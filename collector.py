"""
Antigravity Usage Intelligence - Core Telemetry Collector & Engine
Extracts exact token metrics from Antigravity's internal SQLite conversation databases.
"""

import sys
import os
import re
import glob
import json
import sqlite3
import struct
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from contextlib import closing

CACHE_FILE = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity", "antigravity_stats_cache.json")

GEMINI_HOME = os.path.join(os.path.expanduser("~"), ".gemini")

DATA_SOURCES = [
    {"name": "IDE", "root": os.path.join(GEMINI_HOME, "antigravity-ide")},
    {"name": "Core", "root": os.path.join(GEMINI_HOME, "antigravity")},
    {"name": "CLI", "root": os.path.join(GEMINI_HOME, "antigravity-cli")},
]

def normalize_model_name(raw):
    """Maps raw model identifier strings to clean frontier display names (Gemini 3.x, Claude 4.x)"""
    if not raw:
        return None
    r = raw.lower().strip().rstrip('-')
    
    # Claude models
    if 'claude-sonnet-4-6' in r or 'sonnet-4.6' in r or 'sonnet-4-6' in r:
        return 'Claude Sonnet 4.6'
    if 'claude-opus-4-6' in r or 'opus-4.6' in r or 'opus-4-6' in r:
        return 'Claude Opus 4.6'
    if 'claude-haiku-4-5' in r or 'haiku-4.5' in r or 'haiku-4-5' in r:
        return 'Claude Haiku 4.5'
    if 'claude' in r and 'sonnet' in r:
        return 'Claude Sonnet 4.6'
    if 'claude' in r and 'opus' in r:
        return 'Claude Opus 4.6'
    if 'claude' in r and 'haiku' in r:
        return 'Claude Haiku 4.5'

    # Gemini 3.x models
    if '3.8-flash' in r or '3.8' in r:
        return 'Gemini 3.8 Flash'
    if '3.7-flash' in r or '3.7' in r:
        return 'Gemini 3.7 Flash'
    if '3.6-flash' in r or '3.6' in r:
        return 'Gemini 3.6 Flash'
    if '3.5-flash' in r or '3.5' in r:
        return 'Gemini 3.5 Flash'
    if '3.1-pro' in r or '3.1' in r:
        return 'Gemini 3.1 Pro'
    if '3-flash' in r:
        return 'Gemini 3 Flash'
    if 'gemini-pro' in r:
        return 'Gemini Pro Agent'
    if 'gemini-flash' in r:
        return 'Gemini 3 Flash'

    return None

MODEL_MAP = {
    1318: "Gemini 3.8 Flash",
    1301: "Gemini 3.7 Flash",
    1298: "Gemini 3.1 Pro",
    1196: "Gemini 3.6 Flash",
    1187: "Gemini 3.5 Flash",
    1132: "Gemini 3 Flash",
    1071: "Gemini 3.8 Flash",
    1072: "Gemini 3.7 Flash",
    1036: "Gemini 3.5 Flash",
    1035: "Gemini 3.6 Flash",
    1026: "Gemini 3 Flash",
    1020: "Gemini 3 Flash",
    1016: "Gemini Pro Agent",
}

# Pricing per 1M tokens (Standard Gemini Flash reference model)
RATE_INPUT = 0.10
RATE_CACHE = 0.025
RATE_OUTPUT = 0.40

def parse_proto(data):
    """Fast protobuf wire format parser with boundary guards"""
    pos = 0
    fields = {}
    length_data = len(data)
    while pos < length_data:
        try:
            key = 0
            shift = 0
            while True:
                if pos >= length_data or shift > 64:
                    return fields
                b = data[pos]
                pos += 1
                key |= (b & 0x7F) << shift
                shift += 7
                if not (b & 0x80):
                    break
            field_num = key >> 3
            wire_type = key & 0x7
            if wire_type == 0:  # Varint
                val = 0
                shift = 0
                while True:
                    if pos >= length_data or shift > 64:
                        return fields
                    b = data[pos]
                    pos += 1
                    val |= (b & 0x7F) << shift
                    shift += 7
                    if not (b & 0x80):
                        break
                fields.setdefault(field_num, []).append(('varint', val))
            elif wire_type == 1:  # fixed64
                if pos + 8 > length_data:
                    break
                val = struct.unpack('<Q', data[pos:pos+8])[0]
                pos += 8
                fields.setdefault(field_num, []).append(('fixed64', val))
            elif wire_type == 2:  # bytes / sub-message
                length = 0
                shift = 0
                while True:
                    if pos >= length_data or shift > 64:
                        return fields
                    b = data[pos]
                    pos += 1
                    length |= (b & 0x7F) << shift
                    shift += 7
                    if not (b & 0x80):
                        break
                if length < 0 or pos + length > length_data:
                    break
                payload = data[pos:pos+length]
                pos += length
                fields.setdefault(field_num, []).append(('bytes', payload))
            elif wire_type == 5:  # fixed32
                if pos + 4 > length_data:
                    break
                val = struct.unpack('<I', data[pos:pos+4])[0]
                pos += 4
                fields.setdefault(field_num, []).append(('fixed32', val))
            else:
                break
        except Exception:
            break
    return fields

def open_readonly_db(db_path):
    """Opens an SQLite database in safe read-only WAL mode"""
    db_uri = Path(os.path.abspath(db_path)).as_uri()
    uri = f"{db_uri}?mode=ro"
    try:
        con = sqlite3.connect(uri, uri=True, timeout=5.0)
        con.execute("PRAGMA busy_timeout = 3000;")
        con.execute("PRAGMA query_only = ON;")
        return con
    except sqlite3.OperationalError:
        # Fallback to immutable snapshot if exclusive write lock is active
        imm_uri = f"{db_uri}?mode=ro&immutable=1"
        return sqlite3.connect(imm_uri, uri=True, timeout=2.0)

def parse_session_db(db_path, surface="IDE", brain_dir=None):
    """Parses a single conversation SQLite database safely"""
    if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
        return None

    convo_id = os.path.splitext(os.path.basename(db_path))[0]
    
    try:
        with closing(open_readonly_db(db_path)) as con:
            cur = con.cursor()
            
            # 1. Map step idx to timestamp
            step_times = {}
            try:
                for r in cur.execute('SELECT idx, metadata FROM steps WHERE metadata IS NOT NULL').fetchall():
                    try:
                        s_proto = parse_proto(r[1])
                        if 1 in s_proto:
                            for _, p in s_proto[1]:
                                sub_time = parse_proto(p)
                                if 1 in sub_time and sub_time[1]:
                                    step_times[r[0]] = sub_time[1][0][1]
                    except Exception:
                        pass
            except Exception:
                pass

            # 1.5 Extract real model names per step from executor_metadata
            step_models = {}
            all_detected_models = []
            try:
                rows = cur.execute('SELECT idx, data FROM executor_metadata ORDER BY idx ASC').fetchall()
                for s_idx, data in rows:
                    if data:
                        txt = data.decode('latin-1', errors='ignore')
                        for m in re.findall(r'(?:gemini-[a-zA-Z0-9\.\-]+|claude-[a-zA-Z0-9\.\-]+)', txt):
                            norm = normalize_model_name(m)
                            if norm:
                                step_models[s_idx] = norm
                                all_detected_models.append(norm)
                                break
            except Exception:
                pass

            # Fallback search in gen_metadata if executor_metadata had no model slugs
            if not all_detected_models:
                try:
                    for r in cur.execute('SELECT idx, data FROM gen_metadata ORDER BY idx DESC LIMIT 20').fetchall():
                        if r[1]:
                            txt = r[1].decode('latin-1', errors='ignore')
                            for m in re.findall(r'(?:gemini-[a-zA-Z0-9\.\-]+|claude-[a-zA-Z0-9\.\-]+)', txt):
                                norm = normalize_model_name(m)
                                if norm:
                                    all_detected_models.append(norm)
                                    break
                            if all_detected_models:
                                break
                except Exception:
                    pass

            default_session_model = Counter(all_detected_models).most_common(1)[0][0] if all_detected_models else "Gemini 3.8 Flash"

            # 2. Extract model name & token usage from gen_metadata
            steps_data = []
            session_models_used = []
            
            try:
                rows = cur.execute('SELECT idx, data FROM gen_metadata ORDER BY idx ASC').fetchall()
                for idx, data in rows:
                    try:
                        top = parse_proto(data)
                        if 1 in top:
                            for _, p1 in top[1]:
                                sub1 = parse_proto(p1)
                                if 4 in sub1:
                                    for _, p4 in sub1[4]:
                                        usage = parse_proto(p4)
                                        model_id = usage.get(1, [(0, 0)])[0][1]
                                        inp = usage.get(2, [(0, 0)])[0][1]
                                        out = usage.get(3, [(0, 0)])[0][1]
                                        cached = usage.get(5, [(0, 0)])[0][1]
                                        text_out = usage.get(9, [(0, 0)])[0][1]
                                        thinking = usage.get(10, [(0, 0)])[0][1]
                                        
                                        step_model = step_models.get(idx)
                                        if not step_model:
                                            step_model = default_session_model if default_session_model else MODEL_MAP.get(model_id, "Gemini 3.8 Flash")
                                        
                                        session_models_used.append(step_model)
                                            
                                        ts = step_times.get(idx)
                                        if not ts:
                                            ts = int(os.path.getmtime(db_path))
                                            
                                        steps_data.append({
                                            "idx": idx,
                                            "timestamp": ts,
                                            "date": datetime.fromtimestamp(ts).strftime('%Y-%m-%d'),
                                            "model": step_model,
                                            "input_tokens": inp,
                                            "cached_tokens": cached,
                                            "output_tokens": out,
                                            "text_tokens": text_out,
                                            "thinking_tokens": thinking,
                                            "total_tokens": inp + cached + out
                                        })
                    except Exception:
                        pass
            except Exception:
                pass

            model_name = Counter(session_models_used).most_common(1)[0][0] if session_models_used else default_session_model

            # 2.5 Extract project / workspace name
            project_name = "General"
            workspace_path = ""
            try:
                row = cur.execute('SELECT data FROM trajectory_metadata_blob').fetchone()
                if row and row[0]:
                    text = row[0].decode('latin-1', errors='ignore')
                    m = re.search(r'file:///([^\x00-\x20\x7f-\xff]+)', text)
                    if m:
                        raw_path = urllib.parse.unquote(m.group(1))
                        workspace_path = raw_path
                        folder = os.path.basename(raw_path.rstrip('/\\'))
                        if folder:
                            project_name = folder
            except Exception:
                pass
    except Exception as err:
        sys.stderr.write(f"Warning: could not read {db_path}: {err}\n")
        return None
    
    if not steps_data:
        return None

    # 3. Read transcript tool calls and errors across candidate brain directories
    candidate_brains = [
        os.path.join(GEMINI_HOME, "antigravity-ide", "brain"),
        os.path.join(GEMINI_HOME, "antigravity", "brain"),
        os.path.join(GEMINI_HOME, "antigravity-cli", "brain"),
    ]
    if brain_dir and brain_dir not in candidate_brains:
        candidate_brains.insert(0, brain_dir)

    transcript_path = None
    for b_dir in candidate_brains:
        tp = os.path.join(b_dir, convo_id, ".system_generated", "logs", "transcript.jsonl")
        if os.path.exists(tp):
            transcript_path = tp
            break

    tool_counts = defaultdict(int)
    tool_errors = 0
    first_prompt = ""
    
    if transcript_path and os.path.exists(transcript_path):
        try:
            with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    try:
                        step = json.loads(line)
                        stype = step.get("type", "")
                        status = step.get("status", "")
                        if stype == "USER_INPUT" and not first_prompt:
                            raw_p = step.get("content", "")
                            clean_p = re.sub(r'<[^>]+>', ' ', raw_p).strip()
                            clean_p = ' '.join(clean_p.split())
                            if clean_p:
                                first_prompt = clean_p[:90]
                        if "tool_calls" in step:
                            for tc in step["tool_calls"]:
                                name = tc.get("name", tc.get("toolAction", "unknown"))
                                tool_counts[name] += 1
                        # Capture tool execution errors and error messages
                        if status == "ERROR" or stype == "ERROR_MESSAGE":
                            tool_errors += 1
                    except Exception:
                        pass
        except Exception:
            pass

    total_input = sum(s["input_tokens"] for s in steps_data)
    total_cached = sum(s["cached_tokens"] for s in steps_data)
    total_output = sum(s["output_tokens"] for s in steps_data)
    total_thinking = sum(s["thinking_tokens"] for s in steps_data)
    
    start_ts = steps_data[0]["timestamp"] if steps_data else int(os.path.getmtime(db_path))
    end_ts = steps_data[-1]["timestamp"] if steps_data else start_ts
    db_mtime = os.path.getmtime(db_path)
    # Use the LATEST of (last step timestamp, db mtime) as the session's active date.
    # This ensures sessions that span midnight always appear in the correct day's view.
    last_active_ts = max(end_ts, int(db_mtime))
    
    return {
        "convo_id": convo_id,
        "mtime": db_mtime,
        "surface": surface,
        "created_at": datetime.fromtimestamp(start_ts).strftime('%Y-%m-%d %H:%M:%S'),
        "date": datetime.fromtimestamp(last_active_ts).strftime('%Y-%m-%d'),
        "duration_sec": max(0, end_ts - start_ts),
        "model": model_name,
        "project": project_name,
        "workspace_path": workspace_path,
        "title": first_prompt if first_prompt else f"Session {convo_id[:8]}",
        "turn_count": len(steps_data),
        "input_tokens": total_input,
        "cached_tokens": total_cached,
        "output_tokens": total_output,
        "thinking_tokens": total_thinking,
        "total_tokens": total_input + total_cached + total_output,
        "tool_counts": dict(tool_counts),
        "tool_errors": tool_errors
    }

def sync_all_sessions(force=False):
    """Incremental sync across all Antigravity surfaces with cache and atomic save"""
    cache = {"sessions": {}, "last_sync": 0}
    if not force and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except Exception:
            cache = {"sessions": {}, "last_sync": 0}
            
    cached_sessions = cache.get("sessions", {})
    updated = False
    found_any_source = False
    
    for src in DATA_SOURCES:
        root = src["root"]
        surface = src["name"]
        convos_dir = os.path.join(root, "conversations")
        brain_dir = os.path.join(root, "brain")
        if not os.path.exists(convos_dir):
            continue
        found_any_source = True

        db_files = glob.glob(os.path.join(convos_dir, "*.db"))
        for db_path in db_files:
            try:
                if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
                    continue
                convo_id = os.path.splitext(os.path.basename(db_path))[0]
                mtime = os.path.getmtime(db_path)
                
                # Check cache validity
                # Re-parse if: mtime changed, model name is legacy/deprecated, OR
                # the cached date doesn't match what the current mtime implies
                # (catches sessions that were created on one day and are still active today)
                cached_entry = cached_sessions.get(convo_id)
                if cached_entry and cached_entry.get("mtime") == mtime and cached_entry.get("surface"):
                    old_m = cached_entry.get("model", "")
                    if any(dep in old_m for dep in ["1.5", "2.5", "ID:", "Thinking Exp", "Flash 8B"]):
                        pass  # re-parse for model name fix
                    elif cached_entry.get("date") != datetime.fromtimestamp(mtime).strftime('%Y-%m-%d'):
                        pass  # re-parse: session crossed midnight since last cache write
                    else:
                        continue
                    
                # Parse database
                session_info = parse_session_db(db_path, surface=surface, brain_dir=brain_dir)
                if session_info and session_info.get("turn_count", 0) > 0:
                    cached_sessions[convo_id] = session_info
                    updated = True
            except Exception as e:
                sys.stderr.write(f"Warning: skipped {db_path}: {e}\n")
            
    if updated or (not os.path.exists(CACHE_FILE) and found_any_source):
        cache["sessions"] = cached_sessions
        cache["last_sync"] = int(datetime.now().timestamp())
        tmp_file = CACHE_FILE + ".tmp"
        try:
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f)
            os.replace(tmp_file, CACHE_FILE)
        except Exception as e:
            sys.stderr.write(f"Warning: Cache write failed: {e}\n")
            
    return cached_sessions

def generate_analytics(sessions, start_date=None, end_date=None):
    """Calculates comprehensive time-range statistics with cost, streaks, and hourly flow"""
    filtered_sessions = []
    
    for s in sessions.values():
        s_date = s.get("date")
        if not s_date:
            continue
        if start_date and s_date < start_date:
            continue
        if end_date and s_date > end_date:
            continue
        filtered_sessions.append(s)
        
    total_input = sum(s.get("input_tokens", 0) for s in filtered_sessions)
    total_cached = sum(s.get("cached_tokens", 0) for s in filtered_sessions)
    total_output = sum(s.get("output_tokens", 0) for s in filtered_sessions)
    total_thinking = sum(s.get("thinking_tokens", 0) for s in filtered_sessions)
    total_tokens = total_input + total_cached + total_output
    total_turns = sum(s.get("turn_count", 0) for s in filtered_sessions)
    
    # Cost & Savings Calculation
    est_spend = (total_input * RATE_INPUT + total_cached * RATE_CACHE + total_output * RATE_OUTPUT) / 1_000_000
    cost_without_cache = ((total_input + total_cached) * RATE_INPUT + total_output * RATE_OUTPUT) / 1_000_000
    dollars_saved = max(0.0, cost_without_cache - est_spend)
    savings_pct = (dollars_saved / cost_without_cache * 100) if cost_without_cache > 0 else 0.0

    # Daily aggregation
    daily = defaultdict(lambda: {"input": 0, "cached": 0, "output": 0, "thinking": 0, "total": 0, "sessions": 0, "turns": 0})
    for s in filtered_sessions:
        d = s["date"]
        daily[d]["input"] += s.get("input_tokens", 0)
        daily[d]["cached"] += s.get("cached_tokens", 0)
        daily[d]["output"] += s.get("output_tokens", 0)
        daily[d]["thinking"] += s.get("thinking_tokens", 0)
        daily[d]["total"] += s.get("total_tokens", 0)
        daily[d]["sessions"] += 1
        daily[d]["turns"] += s.get("turn_count", 0)
        
    # Hourly Flow Distribution (24 hours)
    hourly = [{"hour": h, "sessions": 0, "turns": 0, "tokens": 0} for h in range(24)]
    for s in filtered_sessions:
        created_at = s.get("created_at", "")
        if created_at and len(created_at) >= 13:
            try:
                hr = int(created_at[11:13])
                if 0 <= hr < 24:
                    hourly[hr]["sessions"] += 1
                    hourly[hr]["turns"] += s.get("turn_count", 0)
                    hourly[hr]["tokens"] += s.get("total_tokens", 0)
            except Exception:
                pass

    # Streaks and consistency
    dates_list = sorted(list(set(s.get("date") for s in filtered_sessions if s.get("date"))))
    current_streak = 0
    longest_streak = 0
    if dates_list:
        date_objs = [datetime.strptime(d, '%Y-%m-%d').date() for d in dates_list]
        temp_streak = 1
        longest_streak = 1
        for i in range(1, len(date_objs)):
            if (date_objs[i] - date_objs[i-1]).days == 1:
                temp_streak += 1
                if temp_streak > longest_streak:
                    longest_streak = temp_streak
            else:
                temp_streak = 1
        today = datetime.now().date()
        date_set = set(date_objs)
        check = today if today in date_set else (today - timedelta(days=1) if (today - timedelta(days=1)) in date_set else None)
        if check:
            while check in date_set:
                current_streak += 1
                check -= timedelta(days=1)

    # Tool aggregation
    all_tools = defaultdict(int)
    total_tool_errors = 0
    for s in filtered_sessions:
        for t, c in s.get("tool_counts", {}).items():
            all_tools[t] += c
        total_tool_errors += s.get("tool_errors", 0)

    total_calls = sum(all_tools.values())
    tool_success_rate = ((total_calls - total_tool_errors) / total_calls * 100) if total_calls > 0 else 100.0

    # Model breakdown
    models = defaultdict(lambda: {"input": 0, "cached": 0, "output": 0, "thinking": 0, "total": 0, "sessions": 0})
    for s in filtered_sessions:
        m = s.get("model", "Gemini 3.8 Flash")
        models[m]["input"] += s.get("input_tokens", 0)
        models[m]["cached"] += s.get("cached_tokens", 0)
        models[m]["output"] += s.get("output_tokens", 0)
        models[m]["thinking"] += s.get("thinking_tokens", 0)
        models[m]["total"] += s.get("total_tokens", 0)
        models[m]["sessions"] += 1

    models_list = sorted([
        {
            "name": k,
            "total": v["total"],
            "input": v["input"],
            "cached": v["cached"],
            "output": v["output"],
            "thinking": v["thinking"],
            "sessions": v["sessions"],
            "share_pct": round((v["total"] / total_tokens * 100) if total_tokens > 0 else 0, 1)
        }
        for k, v in models.items()
    ], key=lambda x: x["total"], reverse=True)

    # Surface breakdown
    surfaces = defaultdict(lambda: {"total": 0, "sessions": 0, "input": 0, "cached": 0, "output": 0})
    for s in filtered_sessions:
        surf = s.get("surface", "IDE")
        surfaces[surf]["total"] += s.get("total_tokens", 0)
        surfaces[surf]["sessions"] += 1
        surfaces[surf]["input"] += s.get("input_tokens", 0)
        surfaces[surf]["cached"] += s.get("cached_tokens", 0)
        surfaces[surf]["output"] += s.get("output_tokens", 0)

    # Rolling 5-Hour Quota & Activity Window
    now_ts = int(datetime.now().timestamp())
    window_secs = 5 * 3600
    cutoff_5h = now_ts - window_secs
    recent_5h = [s for s in sessions.values() if s.get("mtime", 0) >= cutoff_5h]
    window_tokens = sum(s.get("total_tokens", 0) for s in recent_5h)
    window_turns = sum(s.get("turn_count", 0) for s in recent_5h)
    ACTIVE_WINDOW_SEC = 120
    RECENT_WINDOW_SEC = 900
    is_active = any((now_ts - s.get("mtime", 0)) < ACTIVE_WINDOW_SEC for s in sessions.values())
    is_recent = any((now_ts - s.get("mtime", 0)) < RECENT_WINDOW_SEC for s in sessions.values())

    if recent_5h:
        oldest_ts = min(s.get("mtime", 0) for s in recent_5h)
        next_reset_ts = oldest_ts + window_secs
        secs_left = max(0, int(next_reset_ts - now_ts))
    else:
        secs_left = window_secs

    h_left = secs_left // 3600
    m_left = (secs_left % 3600) // 60
    reset_str = f"{h_left}h {m_left}m" if h_left > 0 else f"{m_left}m"
    
    sorted_recent = sorted(recent_5h, key=lambda x: x.get("mtime", 0), reverse=True)
    active_model_name = sorted_recent[0].get("model", "Gemini 3.8 Flash") if sorted_recent else "Gemini 3.8 Flash"

    # Family breakdowns: Gemini vs Claude
    gemini_tokens = 0
    gemini_turns = 0
    gemini_sessions = 0
    gemini_active = None

    claude_tokens = 0
    claude_turns = 0
    claude_sessions = 0
    claude_active = None

    for s in sorted_recent:
        m = s.get("model", "")
        toks = s.get("total_tokens", 0)
        turns = s.get("turn_count", 0)
        if "claude" in m.lower():
            claude_tokens += toks
            claude_turns += turns
            claude_sessions += 1
            if not claude_active:
                claude_active = m
        else:
            gemini_tokens += toks
            gemini_turns += turns
            gemini_sessions += 1
            if not gemini_active:
                gemini_active = m

    # Standard 5-hour baseline limits in Google Antigravity ecosystem
    GEMINI_LIMIT = 100_000_000  # 100M tokens
    CLAUDE_LIMIT = 15_000_000   # 15M tokens

    gemini_pct = min(100.0, round((gemini_tokens / GEMINI_LIMIT) * 100, 1))
    claude_pct = min(100.0, round((claude_tokens / CLAUDE_LIMIT) * 100, 1))

    quota_info = {
        "rolling_window_hours": 5,
        "window_tokens": window_tokens,
        "window_turns": window_turns,
        "window_sessions": len(recent_5h),
        "seconds_to_reset": secs_left,
        "reset_countdown": reset_str,
        "is_active": is_active,
        "is_recent": is_recent,
        "active_model": active_model_name,
        "status": "High Usage" if window_tokens > 60_000_000 else ("Active Session" if is_active else ("Recent Activity" if is_recent else "Healthy")),
        "gemini": {
            "tokens": gemini_tokens,
            "turns": gemini_turns,
            "sessions": gemini_sessions,
            "limit_tokens": GEMINI_LIMIT,
            "pct": gemini_pct,
            "active_model": gemini_active or "Gemini 3.8 Flash"
        },
        "claude": {
            "tokens": claude_tokens,
            "turns": claude_turns,
            "sessions": claude_sessions,
            "limit_tokens": CLAUDE_LIMIT,
            "pct": claude_pct,
            "active_model": claude_active or "Claude Sonnet 4.6"
        }
    }

    # Sorted daily list
    daily_list = [{"date": k, **v} for k, v in sorted(daily.items())]

    # Full historical daily activity for the annual/multi-month contribution heatmap
    all_daily = defaultdict(lambda: {"input": 0, "cached": 0, "output": 0, "thinking": 0, "total": 0, "sessions": 0, "turns": 0})
    for s in sessions.values():
        d = s.get("date")
        if d:
            all_daily[d]["input"] += s.get("input_tokens", 0)
            all_daily[d]["cached"] += s.get("cached_tokens", 0)
            all_daily[d]["output"] += s.get("output_tokens", 0)
            all_daily[d]["thinking"] += s.get("thinking_tokens", 0)
            all_daily[d]["total"] += s.get("total_tokens", 0)
            all_daily[d]["sessions"] += 1
            all_daily[d]["turns"] += s.get("turn_count", 0)
    all_daily_list = [{"date": k, **v} for k, v in sorted(all_daily.items())]

    # Project breakdown
    projects = defaultdict(lambda: {"input": 0, "cached": 0, "output": 0, "thinking": 0, "total": 0, "sessions": 0, "turns": 0})
    for s in filtered_sessions:
        p = s.get("project", "General")
        projects[p]["input"] += s.get("input_tokens", 0)
        projects[p]["cached"] += s.get("cached_tokens", 0)
        projects[p]["output"] += s.get("output_tokens", 0)
        projects[p]["thinking"] += s.get("thinking_tokens", 0)
        projects[p]["total"] += s.get("total_tokens", 0)
        projects[p]["sessions"] += 1
        projects[p]["turns"] += s.get("turn_count", 0)

    projects_list = sorted([{"name": k, **v} for k, v in projects.items()], key=lambda x: x["total"], reverse=True)

    total_prompt_requests = total_input + total_cached
    cache_hit_rate = (total_cached / total_prompt_requests * 100) if total_prompt_requests > 0 else 0

    return {
        "time_range": {
            "start": start_date or (daily_list[0]["date"] if daily_list else ""),
            "end": end_date or (daily_list[-1]["date"] if daily_list else "")
        },
        "summary": {
            "total_tokens": total_tokens,
            "total_input_tokens": total_input,
            "total_cached_tokens": total_cached,
            "total_output_tokens": total_output,
            "total_thinking_tokens": total_thinking,
            "total_sessions": len(filtered_sessions),
            "total_turns": total_turns,
            "cache_hit_rate_pct": round(cache_hit_rate, 1),
            "total_tool_calls": total_calls,
            "total_tool_errors": total_tool_errors,
            "tool_success_rate_pct": round(tool_success_rate, 1)
        },
        "costs": {
            "est_spend": round(est_spend, 2),
            "cost_without_cache": round(cost_without_cache, 2),
            "dollars_saved": round(dollars_saved, 2),
            "savings_pct": round(savings_pct, 1)
        },
        "streaks": {
            "active_days": len(dates_list),
            "current_streak": current_streak,
            "longest_streak": longest_streak
        },
        "quota": quota_info,
        "hourly": hourly,
        "daily": daily_list,
        "all_daily": all_daily_list,
        "models": dict(models),
        "models_list": models_list,
        "surfaces": dict(surfaces),
        "projects": projects_list,
        "top_tools": sorted([{"name": k, "count": v} for k, v in all_tools.items()], key=lambda x: x["count"], reverse=True)[:15],
        "recent_sessions": sorted(
            [
                {
                    "convo_id": s["convo_id"],
                    "title": s["title"],
                    "project": s.get("project", "General"),
                    "workspace_path": s.get("workspace_path", ""),
                    "surface": s.get("surface", "IDE"),
                    "is_active": (now_ts - s.get("mtime", 0)) < ACTIVE_WINDOW_SEC,
                    "is_recent": (now_ts - s.get("mtime", 0)) < RECENT_WINDOW_SEC,
                    "date": s["date"],
                    "created_at": s["created_at"],
                    "duration_sec": s["duration_sec"],
                    "turn_count": s["turn_count"],
                    "total_tokens": s["total_tokens"],
                    "input_tokens": s["input_tokens"],
                    "cached_tokens": s["cached_tokens"],
                    "output_tokens": s["output_tokens"],
                    "thinking_tokens": s.get("thinking_tokens", 0),
                    "tool_counts": s.get("tool_counts", {}),
                    "tool_errors": s.get("tool_errors", 0),
                    "model": s["model"]
                }
                for s in filtered_sessions
            ],
            key=lambda x: x["created_at"],
            reverse=True
        )[:50]
    }

def build_demo_sessions():
    """Deterministic sample ledger for screenshots, UI testing, and first-run preview.
    Same schema as parse_session_db output; no real databases are touched.
    Token splits honor the calibrated semantics: out includes thinking, inp excludes cache."""
    base = datetime.now().replace(hour=10, minute=30, second=0, microsecond=0)
    specs = [
        # days_ago, project, model, surface, turns, fresh_in, cached, out, think, duration_min, tools
        (0, "Demo Shop", "Gemini 3.8 Flash", "IDE", 34, 41200, 812000, 18900, 5600, 95, {"run_command": 22, "view_file": 14, "replace_file_content": 9}),
        (0, "Demo API", "Claude Sonnet 4.6", "CLI", 12, 18500, 204000, 7600, 2300, 41, {"run_command": 9, "grep_search": 6}),
        (1, "Demo Shop", "Gemini 3.8 Flash", "IDE", 47, 52300, 1150000, 24100, 7100, 132, {"run_command": 31, "view_file": 19, "write_to_file": 7}),
        (1, "Demo API", "Gemini 3.7 Flash", "IDE", 8, 9400, 88000, 3200, 900, 22, {"view_file": 5, "run_command": 4}),
        (2, "Demo Shop", "Claude Sonnet 4.6", "CLI", 21, 27600, 402000, 11800, 3400, 64, {"run_command": 15, "grep_search": 8}),
        (3, "Demo API", "Gemini 3.8 Flash", "Core", 15, 15800, 231000, 6900, 2100, 48, {"view_file": 11, "run_command": 6}),
        (4, "Demo Shop", "Gemini 3.1 Pro", "IDE", 29, 38400, 689000, 16200, 4900, 88, {"replace_file_content": 13, "run_command": 17, "view_file": 10}),
        (5, "Demo API", "Claude Sonnet 4.6", "CLI", 6, 7200, 64000, 2400, 700, 18, {"run_command": 5}),
        (6, "Demo Shop", "Gemini 3.8 Flash", "IDE", 38, 44900, 934000, 20500, 6200, 110, {"run_command": 26, "view_file": 16, "write_to_file": 6}),
        (6, "Demo API", "Gemini 3.7 Flash", "Core", 11, 12400, 142000, 5100, 1500, 35, {"grep_search": 7, "view_file": 5}),
    ]
    sessions = {}
    for i, (ago, project, model, surface, turns, inp, cached, out, think, dur_min, tools) in enumerate(specs):
        start = base - timedelta(days=ago)
        end = start + timedelta(minutes=dur_min)
        mtime = int(end.timestamp())
        sessions[f"demo-session-{i:02d}"] = {
            "convo_id": f"demo-session-{i:02d}",
            "mtime": mtime,
            "surface": surface,
            "created_at": start.strftime('%Y-%m-%d %H:%M:%S'),
            "date": start.strftime('%Y-%m-%d'),
            "duration_sec": dur_min * 60,
            "model": model,
            "project": project,
            "workspace_path": "",
            "title": f"Demo: {project} task #{i + 1}",
            "turn_count": turns,
            "input_tokens": inp,
            "cached_tokens": cached,
            "output_tokens": out,
            "thinking_tokens": think,
            "total_tokens": inp + cached + out,
            "tool_counts": tools,
            "tool_errors": 1 if i % 4 == 0 else 0,
        }
    return sessions

if __name__ == "__main__":
    force_sync = "--force" in sys.argv or "--rebuild" in sys.argv
    if "--demo" in sys.argv:
        sessions = build_demo_sessions()
    else:
        sessions = sync_all_sessions(force=force_sync)
    
    # Check arguments
    if "--json" in sys.argv:
        start_date = None
        end_date = None
        for i, arg in enumerate(sys.argv):
            if arg == "--start" and i + 1 < len(sys.argv):
                start_date = sys.argv[i + 1]
            if arg == "--end" and i + 1 < len(sys.argv):
                end_date = sys.argv[i + 1]
        data = generate_analytics(sessions, start_date, end_date)
        print(json.dumps(data))
    else:
        data = generate_analytics(sessions)
        s = data["summary"]
        c = data["costs"]
        st = data["streaks"]
        print("==================================================")
        print("      ANTIGRAVITY USAGE INTELLIGENCE REPORT      ")
        print("==================================================")
        print(f"Total Sessions:         {s['total_sessions']}")
        print(f"Total Agent Turns:      {s['total_turns']:,}")
        print(f"Non-Cached Input:       {s['total_input_tokens']:,}")
        print(f"Cached Input (Read):    {s['total_cached_tokens']:,}")
        print(f"Output Tokens:          {s['total_output_tokens']:,} (incl. Thinking: {s['total_thinking_tokens']:,})")
        print(f"Total Processed Tokens: {s['total_tokens']:,}")
        print(f"Cache Savings Ratio:    {s['cache_hit_rate_pct']}%")
        print(f"Estimated Spend:        ${c['est_spend']:.2f} (Without Cache: ${c['cost_without_cache']:.2f})")
        print(f"Dollars Saved by Cache: ${c['dollars_saved']:.2f} ({c['savings_pct']}% saved)")
        print(f"Coding Streak:          {st['current_streak']} days active (Best: {st['longest_streak']} days)")
        print(f"Tool Reliability:       {s['tool_success_rate_pct']}% ({s['total_tool_calls']:,} calls / {s['total_tool_errors']} retries)")
        print("==================================================")
