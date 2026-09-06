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

async function scanForLanguageServer() {
  const psCmd = process.platform === 'win32'
    ? 'powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like \'*language_server*\' -and $_.CommandLine -like \'*--csrf_token*\' } | Select-Object ProcessId, CommandLine | ConvertTo-Json -Compress"'
    : 'pgrep -fl language_server';

  const { stdout } = await execCommand(psCmd);
  if (!stdout) return null;

  let candidates = [];
  try {
    const parsed = JSON.parse(stdout);
    candidates = Array.isArray(parsed) ? parsed : [parsed];
  } catch (e) {
    return null;
  }

  for (const cand of candidates) {
    const cmd = cand.CommandLine || '';
    const pid = cand.ProcessId;
    if (!pid || !cmd) continue;

    const tokenMatch = cmd.match(/--csrf_token\s+([a-zA-Z0-9\-_.]+)/);
    const extPortMatch = cmd.match(/--extension_server_port\s+(\d+)/);
    if (!tokenMatch) continue;

    const csrfToken = tokenMatch[1];
    const extPort = extPortMatch ? parseInt(extPortMatch[1], 10) : 0;

    // Find listening ports for this PID
    const netCmd = `netstat -ano | findstr "LISTENING" | findstr " ${pid}"`;
    const { stdout: netOut } = await execCommand(netCmd);

    const ports = new Set();
    if (extPort > 0) {
      ports.add(extPort + 2);
      ports.add(extPort + 1);
      ports.add(extPort);
    }

    if (netOut) {
      const lines = netOut.split('\n');
      for (const line of lines) {
        const m = line.trim().match(/:(\d+)\s+.*LISTENING/);
        if (m) ports.add(parseInt(m[1], 10));
      }
    }

    for (const port of ports) {
      for (const proto of ['https', 'http']) {
        const status = await queryStatus(port, csrfToken, proto);
        if (status && status.userStatus) {
          return {
            port,
            protocol: proto,
            csrfToken,
            pid,
            rawStatus: status.userStatus,
          };
        }
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

  return cachedQuota;
}

module.exports = {
  getLiveQuota,
};
