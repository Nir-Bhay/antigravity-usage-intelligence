const { exec } = require('child_process');
const https = require('https');
const http = require('http');

let cachedConn = null;
let cachedQuota = null;
let lastQueryTime = 0;

function execCommand(cmd) {
  return new Promise((resolve) => {
    exec(cmd, { timeout: 4000 }, (err, stdout, stderr) => {
      resolve({ err, stdout: stdout ? stdout.trim() : '', stderr });
    });
  });
}

function queryStatus(port, csrfToken, protocol) {
  const lib = protocol === 'https' ? https : http;
  const body = JSON.stringify({ wrapper_data: {} });

  return new Promise((resolve) => {
    const req = lib.request(
      {
        hostname: '127.0.0.1',
        port: port,
        path: '/exa.language_server_pb.LanguageServerService/GetUserStatus',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(body),
          'X-Codeium-Csrf-Token': csrfToken,
          'Connect-Protocol-Version': '1',
        },
        rejectUnauthorized: false,
        timeout: 2500,
      },
      (res) => {
        let data = '';
        res.on('data', (c) => (data += c));
        res.on('end', () => {
          if (res.statusCode === 200 && data) {
            try {
              resolve(JSON.parse(data));
            } catch (e) {
              resolve(null);
            }
          } else {
            resolve(null);
          }
        });
      }
    );

    req.on('error', () => resolve(null));
    req.on('timeout', () => {
      req.destroy();
      resolve(null);
    });
    req.write(body);
    req.end();
  });
}

async function listServerCandidates() {
  if (process.platform === 'win32') {
    const psCmd = 'powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like \'*language_server*\' -and $_.CommandLine -like \'*--csrf_token*\' } | Select-Object ProcessId, CommandLine | ConvertTo-Json -Compress"';
    const { stdout } = await execCommand(psCmd);
    if (!stdout) return [];
    try {
      const parsed = JSON.parse(stdout);
      const arr = Array.isArray(parsed) ? parsed : [parsed];
      return arr
        .filter((c) => c && c.ProcessId && c.CommandLine)
        .map((c) => ({ pid: c.ProcessId, cmd: c.CommandLine }));
    } catch (e) {
      return [];
    }
  }

  // macOS / Linux: pgrep prints "<pid> <full command line>" as plain text,
  // so parse lines instead of expecting JSON.
  const { stdout } = await execCommand('pgrep -fa language_server');
  if (!stdout) return [];
  const out = [];
  for (const line of stdout.split('\n')) {
    const m = line.match(/^\s*(\d+)\s+(.*)$/);
    if (m && m[2].includes('--csrf_token')) {
      out.push({ pid: parseInt(m[1], 10), cmd: m[2] });
    }
  }
  return out;
}

async function listListeningPorts(pid) {
  const ports = new Set();
  try {
    if (process.platform === 'win32') {
      const netCmd = `netstat -ano | findstr "LISTENING" | findstr " ${pid}"`;
      const { stdout: netOut } = await execCommand(netCmd);
      if (netOut) {
        for (const line of netOut.split('\n')) {
          const m = line.trim().match(/:(\d+)\s+.*LISTENING/);
          if (m) ports.add(parseInt(m[1], 10));
        }
      }
    } else if (process.platform === 'linux') {
      const { stdout } = await execCommand(`ss -ltnp 2>/dev/null | grep "pid=${pid},"`);
      if (stdout) {
        for (const line of stdout.split('\n')) {
          const m = line.match(/:(\d+)\s/);
          if (m) ports.add(parseInt(m[1], 10));
        }
      }
    } else {
      // macOS: lsof is best-effort (may not exist -> ignored below).
      const { stdout } = await execCommand(`lsof -aPn -iTCP -sTCP:LISTEN -p ${pid} 2>/dev/null`);
      if (stdout) {
        for (const line of stdout.split('\n')) {
          const m = line.match(/:(\d+)\s+\(LISTEN\)/);
          if (m) ports.add(parseInt(m[1], 10));
        }
      }
    }
  } catch (e) {
    // Best-effort only; extension_port offsets below still apply.
  }
  return ports;
}

async function scanForLanguageServer() {
  const candidates = await listServerCandidates();

  for (const cand of candidates) {
    const cmd = cand.cmd || '';
    const pid = cand.pid;
    if (!pid || !cmd) continue;

    const tokenMatch = cmd.match(/--csrf_token[=\s]+([A-Za-z0-9\-_.=+/]+)/);
    const extPortMatch = cmd.match(/--extension_server_port[=\s]+(\d+)/);
    if (!tokenMatch) continue;

    const csrfToken = tokenMatch[1];
    const extPort = extPortMatch ? parseInt(extPortMatch[1], 10) : 0;

    const ports = new Set();
    if (extPort > 0) {
      ports.add(extPort);
      ports.add(extPort + 1);
      ports.add(extPort + 2);
    }
    for (const p of await listListeningPorts(pid)) ports.add(p);

    // Bound worst-case probe time: cap ports, probe all in parallel,
    // return the first endpoint that answers with a userStatus.
    const portList = [...ports].filter((p) => p > 0 && p < 65536).slice(0, 25);
    const probes = [];
    for (const port of portList) {
      for (const proto of ['https', 'http']) {
        probes.push(
          queryStatus(port, csrfToken, proto)
            .then((status) => ({ port, protocol: proto, status }))
            .catch(() => ({ port, protocol: proto, status: null }))
        );
      }
    }
    const settled = await Promise.allSettled(probes);
    for (const r of settled) {
      if (r.status !== 'fulfilled') continue;
      const { port, protocol, status } = r.value;
      if (status && status.userStatus) {
        return {
          port,
          protocol,
          csrfToken,
          pid,
          rawStatus: status.userStatus,
        };
      }
    }
  }

  return null;
}

function parseQuotaFromStatus(status) {
  if (!status) return null;

  const configs = status.cascadeModelConfigData?.clientModelConfigs || [];

  let geminiModel = null;
  let claudeModel = null;

  for (const m of configs) {
    if (!m.quotaInfo) continue;
    const label = m.label || '';
    if (/gemini/i.test(label) && !geminiModel) {
      geminiModel = m;
    } else if (/claude/i.test(label) && !claudeModel) {
      claudeModel = m;
    }
  }

  const result = {
    is_live: true,
    stale: false,
    fetched_at: Date.now(),
    user_name: status.name || 'User',
    user_email: status.email || '',
    tier_name: status.userTier?.name || 'Google AI Pro',
    prompt_credits: status.planStatus?.availablePromptCredits ?? null,
    flow_credits: status.planStatus?.availableFlowCredits ?? null,
    gemini: geminiModel ? {
      label: geminiModel.label,
      remaining_fraction: geminiModel.quotaInfo.remainingFraction,
      remaining_pct: Math.round((geminiModel.quotaInfo.remainingFraction ?? 1) * 100),
      used_pct: Math.round((1 - (geminiModel.quotaInfo.remainingFraction ?? 1)) * 100),
      reset_time: geminiModel.quotaInfo.resetTime,
    } : null,
    claude: claudeModel ? {
      label: claudeModel.label,
      remaining_fraction: claudeModel.quotaInfo.remainingFraction,
      remaining_pct: Math.round((claudeModel.quotaInfo.remainingFraction ?? 1) * 100),
      used_pct: Math.round((1 - (claudeModel.quotaInfo.remainingFraction ?? 1)) * 100),
      reset_time: claudeModel.quotaInfo.resetTime,
    } : null,
  };

  return result;
}

async function getLiveQuota(forceRefresh = false) {
  const now = Date.now();
  if (!forceRefresh && cachedQuota && (now - lastQueryTime < 15000)) {
    return cachedQuota;
  }

  // 1. Try cached connection first
  if (cachedConn) {
    const raw = await queryStatus(cachedConn.port, cachedConn.csrfToken, cachedConn.protocol);
    if (raw && raw.userStatus) {
      cachedQuota = parseQuotaFromStatus(raw.userStatus);
      lastQueryTime = now;
      return cachedQuota;
    }
    cachedConn = null;
  }

  // 2. Scan for language server
  try {
    const conn = await scanForLanguageServer();
    if (conn) {
      cachedConn = {
        port: conn.port,
        protocol: conn.protocol,
        csrfToken: conn.csrfToken,
        pid: conn.pid,
      };
      cachedQuota = parseQuotaFromStatus(conn.rawStatus);
      lastQueryTime = now;
      return cachedQuota;
    }
  } catch (err) {
    // Graceful fallback
  }

  // Scan failed: serve last-known data explicitly marked stale
  // so the dashboard never mistakes it for a fresh reading.
  if (cachedQuota) {
    cachedQuota.stale = true;
    return cachedQuota;
  }
  return null;
}

module.exports = {
  getLiveQuota,
};
