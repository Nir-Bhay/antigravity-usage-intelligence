# Changelog

All notable changes to the **Antigravity Usage Intelligence** extension will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-09-06

### Added

#### Core Telemetry & Parsing Engine
* **Safe Read-Only SQLite WAL Extraction:** Engine reads Antigravity internal session databases (`~/.gemini/antigravity/conversations/*.db`) using `?mode=ro&immutable=1`, `PRAGMA query_only = ON`, and busy timeouts. Prevents file locking conflicts while Antigravity agents execute.
* **Zero-Dependency Protobuf Wire Decoder:** Custom binary parser extracts raw protobuf field tags (`varint`, `fixed64`, `bytes`, `fixed32`) directly from `gen_metadata` blobs without external protobuf or grpc runtime packages.
* **Granular Token Accounting:** Accurately isolates fresh input tokens, prompt cache read tokens, output generation tokens, and Gemini reasoning/thinking tokens.
* **Atomic Disk Caching:** Implements incremental caching (`antigravity_stats_cache.json`) with atomic `.tmp` file swapping. Cold scans index 140+ conversation databases in ~2 seconds; subsequent queries load in under 80 milliseconds.
* **Automatic Python Discovery:** Multi-tiered interpreter locator resolving paths through settings (`antigravity-stats.pythonPath`), Microsoft Python extension API (`ms-python.python`), active virtual environments (`VIRTUAL_ENV`, `.venv`), and system command fallbacks (`python3`, `python`, `py -3`, `uv run python`).

#### Interactive Analytics Dashboard
* **Dual View Architecture:** Operates both as a compact sidebar webview in the Activity Bar (`antigravity-stats-container`) and as a full-screen dashboard in an editor tab (`antigravity-stats.openDashboard`).
* **KPI Metrics Grid:** Real-time counters for Total Tokens, Prompt Cache Read, Fresh Input, Output Generation, Thinking Tokens, Cache Efficiency Rate, Dollar Savings, and Tool Reliability.
* **Circadian Rhythm Chart:** 24-hour peak coding hours widget visualizing agent sessions, turns, and token volumes across the clock.
* **16-Week Activity Heatmap:** GitHub-style density grid displaying daily agent interaction intensity over the preceding 4 months.
* **Daily Consumption Trend:** Proportionally stacked visual bar chart breaking down input, cache read, output, and thinking tokens by day.
* **Workspace & Project Filter Grid:** Detects open workspaces from trajectory metadata and enables 1-click token isolation per repository.
* **Status Bar Integration:** Persistent bottom-right status bar item displaying today's token consumption with live auto-refresh and click-to-open interaction.

#### Forensics & Session Explorer
* **Slide-Out Session Inspector:** Side drawer detailing conversation UUID, workspace root, model name, elapsed duration, turn count, token splits, and executed tools.
* **Quick-Filter Pills:** 1-click pills to filter sessions by size and behavior: `All`, `🔥 Heavy (>5M)`, `⚡ Fast (<1m)`, `⏱️ Deep (>10 turns)`, and `⚠️ Has Retries`.
* **Live Session Search:** Real-time search indexing prompts, conversation IDs, project names, and model strings.

#### Financial & Efficiency Accounting
* **Dollar Cost & Cache ROI Engine:** Translates token consumption into real-world dollars using standard Gemini pricing models ($0.10/1M input, $0.025/1M cache read, $0.40/1M output).
* **Prompt Cache Savings Calculation:** Quantifies gross spend without caching vs net spend, providing exact dollar savings and percentage discount figures.
* **Coding Streaks Tracker:** Tracks consecutive active coding days, all-time best streak, and total active days with Antigravity agents.
* **Tool Reliability Tracker:** Aggregates tool executions from transcript ledgers (`run_command`, `replace_file_content`, `view_file`, etc.) and computes tool success versus retry/error rates.

#### Exporting & Developer Workflows
* **1-Click Markdown Standup Export:** Generates formatted Markdown summaries containing token totals, cache efficiency, dollar savings, and top projects ready for standup notes, PR descriptions, and client reports.
* **CSV Data Export:** Formats all indexed session rows into structured CSV files for spreadsheet and data warehouse ingestion.
* **Raw JSON Export:** Full telemetry export for custom scripting and reporting.
* **Command Palette Integration:** Quick commands for opening the dashboard, manual refresh, cache rebuilding, and report exporting.

#### Security & Privacy
* **100% Local Execution:** Operates with zero outbound network calls, zero external analytics beacons, and no tracking scripts.
* **Strict Content Security Policy:** Webview enforces strict nonce-guarded script execution and `default-src 'none'` policies.
