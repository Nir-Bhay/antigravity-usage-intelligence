const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const { execFile } = require('child_process');
const { getLiveQuota } = require('./src/quota_detector');

let statusBarItem;
let statsProvider;
let fullPanel;
let autoRefreshTimer;
let activeChildProcess = null;
let lastRange = { start: null, end: null };
let firedQuotaAlerts = {};

/**
 * Warns once per threshold level when LIVE provider quota crosses it.
 * Estimates never trigger alerts; levels re-arm after usage drops 5 points.
 */
function maybeQuotaAlert(liveQuota) {
  const config = vscode.workspace.getConfiguration('antigravity-stats');
  if (!config.get('quotaAlerts', true)) return;
  const thresholds = (config.get('quotaAlertThresholds', [75, 90, 100]) || [])
    .filter((t) => typeof t === 'number' && t > 0 && t <= 100)
    .sort((a, b) => a - b);
  if (!liveQuota || !thresholds.length) return;
  const fleets = [
    { key: 'gemini', label: (liveQuota.gemini && liveQuota.gemini.label) || 'Gemini' },
    { key: 'claude', label: (liveQuota.claude && liveQuota.claude.label) || 'Claude' },
  ];
  for (const f of fleets) {
    const q = liveQuota[f.key];
    if (!q || typeof q.used_pct !== 'number') continue;
    let top = null;
    for (const t of thresholds) {
      const k = f.key + ':' + t;
      if (q.used_pct >= t) {
        if (!firedQuotaAlerts[k]) {
          firedQuotaAlerts[k] = true;
          top = t;
        }
      } else if (q.used_pct < t - 5) {
        delete firedQuotaAlerts[k];
      }
    }
    if (top !== null) {
      vscode.window.showWarningMessage(
        `Antigravity quota: ${f.label} at ${q.used_pct}% used (crossed ${top}%; ${liveQuota.tier_name || 'current plan'}).`,
        'Open Dashboard'
      ).then((sel) => {
        if (sel === 'Open Dashboard') vscode.commands.executeCommand('antigravity-stats.openDashboard');
      });
    }
  }
}

function formatCompact(num) {
  if (num == null) return '0';
  if (num >= 1000000000) return (num / 1000000000).toFixed(1) + 'B';
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toString();
}

function getLocalDateString(d = new Date()) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Intelligent Python executable locator
 */
async function resolvePythonPath() {
  const config = vscode.workspace.getConfiguration('antigravity-stats');
  const configuredPath = config.get('pythonPath');
  if (configuredPath && configuredPath.trim() !== '') {
    return configuredPath.trim().replace(/^"(.*)"$/, '$1').replace(/^'(.*)'$/, '$1');
  }

  // Check VS Code Microsoft Python extension API
  try {
    const pyExt = vscode.extensions.getExtension('ms-python.python');
    if (pyExt) {
      if (!pyExt.isActive) await pyExt.activate();
      const api = pyExt.exports;
      if (api && api.environments) {
        const envPath = api.environments.getActiveEnvironmentPath();
        const resolved = await api.environments.resolveEnvironment(envPath);
        if (resolved && resolved.executable && resolved.executable.uri) {
          return resolved.executable.uri.fsPath;
        }
      }
    }
  } catch (e) {
    // Ignore and fallback
  }

  // Check virtualenvs
  if (process.env.VIRTUAL_ENV) {
    const venvPy = process.platform === 'win32'
      ? path.join(process.env.VIRTUAL_ENV, 'Scripts', 'python.exe')
      : path.join(process.env.VIRTUAL_ENV, 'bin', 'python');
    if (fs.existsSync(venvPy)) return venvPy;
  }

  // Check workspace .venv
  const folders = vscode.workspace.workspaceFolders;
  if (folders) {
    for (const folder of folders) {
      const venvPy = process.platform === 'win32'
        ? path.join(folder.uri.fsPath, '.venv', 'Scripts', 'python.exe')
        : path.join(folder.uri.fsPath, '.venv', 'bin', 'python');
      if (fs.existsSync(venvPy)) return venvPy;
    }
  }

  // Default platform candidates — on Windows, try specific install locations first
  if (process.platform === 'win32') {
    const userProfile = process.env.USERPROFILE || process.env.HOMEDRIVE + process.env.HOMEPATH || 'C:\\Users\\Default';
    const winCandidates = [
      path.join(userProfile, 'AppData', 'Local', 'Programs', 'Python', 'Python312', 'python.exe'),
      path.join(userProfile, 'AppData', 'Local', 'Programs', 'Python', 'Python311', 'python.exe'),
      path.join(userProfile, 'AppData', 'Local', 'Programs', 'Python', 'Python310', 'python.exe'),
      path.join(userProfile, 'AppData', 'Local', 'Programs', 'Python', 'Python39', 'python.exe'),
      'C:\\Python312\\python.exe',
      'C:\\Python311\\python.exe',
      'C:\\Python310\\python.exe',
    ];
    for (const candidate of winCandidates) {
      if (fs.existsSync(candidate)) return candidate;
    }
  }
  return process.platform === 'win32' ? 'python' : 'python3';
}

/**
 * Executes python collector with candidate fallback and timeout
 */
function runCollector(pythonBin, args) {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(__dirname, 'collector.py');
    const cmdArgs = [scriptPath, '--json', ...args];

    const child = execFile(
      pythonBin,
      cmdArgs,
      { maxBuffer: 15 * 1024 * 1024, timeout: 30000 },
      (error, stdout, stderr) => {
        if (activeChildProcess === child) activeChildProcess = null;
        if (error) {
          error.stderr = stderr;
          return reject(error);
        }
        try {
          const parsed = JSON.parse(stdout.trim());
          resolve(parsed);
        } catch (e) {
          reject(new Error(`Failed to parse collector JSON output: ${e.message}`));
        }
      }
    );
    activeChildProcess = child;
  });
}

async function fetchStatsData(args = []) {
  let pythonBin = await resolvePythonPath();
  const demoCfg = vscode.workspace.getConfiguration('antigravity-stats');
  if (demoCfg.get('demoMode', false) && !args.includes('--demo')) {
    args = ['--demo', ...args];
  }

  try {
    const demoData = await runCollector(pythonBin, args);
    if (args.includes('--demo')) demoData.is_demo = true;
    return demoData;
  } catch (err) {
    // Only fallback if the executable itself was not found (ENOENT)
    if (err.code === 'ENOENT') {
      const fallbackBins = process.platform === 'win32'
        ? ['py', 'python', 'python3']
        : ['python3', 'python', '/usr/bin/python3', '/usr/local/bin/python3', '/opt/homebrew/bin/python3'];

      for (const fallback of fallbackBins) {
        if (fallback === pythonBin) continue;
        try {
          const demoFallback = await runCollector(fallback, args);
          if (args.includes('--demo')) demoFallback.is_demo = true;
          return demoFallback;
        } catch (e) {
          if (e.code !== 'ENOENT') {
            throw new Error(`Collector execution failed (${fallback}): ${e.stderr || e.message}`);
          }
        }
      }
      throw new Error(`Python interpreter not found. Please set "antigravity-stats.pythonPath" in settings.`);
    }
    throw new Error(`Collector error: ${err.stderr || err.message}`);
  }
}

async function updateStatusBar() {
  if (!statusBarItem) return;
  try {
    const today = getLocalDateString();
    const data = await fetchStatsData(['--start', today, '--end', today]);
    const tokens = data.summary.total_tokens;
    if (data.summary.total_sessions === 0) {
      statusBarItem.text = `$(graph) AI: no data`;
      statusBarItem.tooltip = `No Antigravity sessions found yet. Use Antigravity for a task, then Refresh. Looking in ~/.gemini/antigravity*/conversations. Click to open dashboard.`;
      statusBarItem.show();
      return;
    }
    statusBarItem.text = `$(graph) AI: ${formatCompact(tokens)} today`;
    statusBarItem.tooltip = `Antigravity Usage Today: ${tokens.toLocaleString()} tokens across ${data.summary.total_sessions} sessions (${data.summary.cache_hit_rate_pct}% cached). Click to open dashboard.`;
    statusBarItem.show();
  } catch (err) {
    statusBarItem.text = `$(graph) AI Stats`;
    statusBarItem.tooltip = `Antigravity Stats error: ${err.message}`;
    statusBarItem.show();
  }
}

function getWebviewContent(webview, extensionUri) {
  const htmlPath = path.join(extensionUri.fsPath, 'src', 'ui', 'dashboard.html');
  let html = fs.readFileSync(htmlPath, 'utf8');

  const nonce = crypto.randomBytes(16).toString('base64');
  const cspMeta = `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${webview.cspSource} https: data:; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">`;

  // Inject CSP and nonce
  html = html.replace('<head>', `<head>\n  ${cspMeta}`);
  html = html.replace(/<script>/g, `<script nonce="${nonce}">`);
  return html;
}

async function handleWebviewMessage(webview, message) {
  try {
    switch (message.command) {
      case 'init': {
        const config = vscode.workspace.getConfiguration('antigravity-stats');
        const defaultRange = config.get('defaultRange', 'today');
        const args = [];
        const start = message.start || (defaultRange === 'today' ? getLocalDateString() : null);
        const end = message.end || (defaultRange === 'today' ? getLocalDateString() : null);
        if (start) args.push('--start', start);
        if (end) args.push('--end', end);
        lastRange = { start: start || null, end: end || null };
        const [data, liveQuota] = await Promise.all([
          fetchStatsData(args),
          getLiveQuota().catch(() => null)
        ]);
        if (liveQuota) data.live_quota = liveQuota;
        maybeQuotaAlert(liveQuota);
        webview.postMessage({ command: 'loadStats', data, defaultRange });
        updateStatusBar();
        break;
      }
      case 'refresh':
      case 'fetchStats': {
        const args = [];
        if (message.start) args.push('--start', message.start);
        if (message.end) args.push('--end', message.end);
        lastRange = { start: message.start || null, end: message.end || null };
        const [data, liveQuota] = await Promise.all([
          fetchStatsData(args),
          getLiveQuota(message.command === 'refresh').catch(() => null)
        ]);
        if (liveQuota) data.live_quota = liveQuota;
        maybeQuotaAlert(liveQuota);
        webview.postMessage({ command: 'loadStats', data });
        updateStatusBar();
        break;
      }
      case 'rebuild': {
        vscode.window.showInformationMessage('Rebuilding Antigravity token cache from disk...');
        const [data, liveQuota] = await Promise.all([
          fetchStatsData(['--force']),
          getLiveQuota(true).catch(() => null)
        ]);
        if (liveQuota) data.live_quota = liveQuota;
        maybeQuotaAlert(liveQuota);
        webview.postMessage({ command: 'loadStats', data });
        updateStatusBar();
        vscode.window.showInformationMessage('Antigravity token cache rebuild complete.');
        break;
      }
      case 'openFullDashboard': {
        vscode.commands.executeCommand('antigravity-stats.openDashboard');
        break;
      }
      case 'exportJSON': {
        const doc = await vscode.workspace.openTextDocument({
          content: JSON.stringify(message.data, null, 2),
          language: 'json'
        });
        await vscode.window.showTextDocument(doc);
        break;
      }
      case 'exportCSV': {
        const sessions = (message.data && message.data.recent_sessions) ? message.data.recent_sessions : [];
        let csv = 'Date,Session ID,Project,Model,Turns,Duration (sec),Input Tokens,Cached Tokens,Output Tokens,Thinking Tokens,Total Tokens,Prompt Title\n';
        sessions.forEach(s => {
          const cleanTitle = (s.title || '').replace(/"/g, '""');
          csv += `"${s.date}","${s.convo_id}","${s.project || 'General'}","${s.model}","${s.turn_count}","${s.duration_sec}","${s.input_tokens}","${s.cached_tokens}","${s.output_tokens}","${s.thinking_tokens || 0}","${s.total_tokens}","${cleanTitle}"\n`;
        });
        const doc = await vscode.workspace.openTextDocument({
          content: csv,
          language: 'csv'
        });
        await vscode.window.showTextDocument(doc);
        break;
      }
      case 'copyToClipboard': {
        if (message.text) {
          await vscode.env.clipboard.writeText(message.text);
          if (message.toast) {
            vscode.window.showInformationMessage(message.toast);
          }
        }
        break;
      }
      case 'openFolder': {
        if (message.path) {
          const uri = vscode.Uri.file(message.path);
          vscode.commands.executeCommand('vscode.openFolder', uri, true);
        }
        break;
      }
    }
  } catch (err) {
    vscode.window.showErrorMessage(`Antigravity Stats: ${err.message}`);
    webview.postMessage({ command: 'error', message: err.message });
  }
}

class AntigravityStatsViewProvider {
  constructor(extensionUri) {
    this._extensionUri = extensionUri;
    this._view = null;
  }

  resolveWebviewView(webviewView) {
    this._view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this._extensionUri]
    };
    webviewView.webview.html = getWebviewContent(webviewView.webview, this._extensionUri);
    webviewView.webview.onDidReceiveMessage(async (message) => {
      await handleWebviewMessage(webviewView.webview, message);
    });
  }

  async refresh(start = lastRange.start, end = lastRange.end) {
    if (this._view) {
      const args = [];
      if (start) args.push('--start', start);
      if (end) args.push('--end', end);
      try {
        const [data, liveQuota] = await Promise.all([
          fetchStatsData(args),
          getLiveQuota(true).catch(() => null)
        ]);
        if (liveQuota) data.live_quota = liveQuota;
        maybeQuotaAlert(liveQuota);
        this._view.webview.postMessage({ command: 'loadStats', data });
        updateStatusBar();
      } catch (err) {
        this._view.webview.postMessage({ command: 'error', message: err.message });
      }
    }
  }

  pushStats(data) {
    if (this._view) {
      this._view.webview.postMessage({ command: 'loadStats', data });
      updateStatusBar();
    }
  }
}

function setupAutoRefresh(context) {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
  const config = vscode.workspace.getConfiguration('antigravity-stats');
  const showBar = config.get('showStatusBar', true);
  const minutes = Math.max(1, config.get('autoRefreshMinutes', 3));

  if (showBar) {
    if (!statusBarItem) {
      statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 95);
      statusBarItem.command = 'antigravity-stats.openDashboard';
      context.subscriptions.push(statusBarItem);
    }
    updateStatusBar();
    autoRefreshTimer = setInterval(() => {
      updateStatusBar();
    }, minutes * 60 * 1000);
  } else if (statusBarItem) {
    statusBarItem.hide();
  }
}

function activate(context) {
  // 1. Register Sidebar Webview
  statsProvider = new AntigravityStatsViewProvider(context.extensionUri);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider('antigravity-stats-view', statsProvider)
  );

  // 2. Register Full Screen Dashboard command
  context.subscriptions.push(
    vscode.commands.registerCommand('antigravity-stats.openDashboard', () => {
      if (fullPanel) {
        fullPanel.reveal(vscode.ViewColumn.One);
        return;
      }

      fullPanel = vscode.window.createWebviewPanel(
        'antigravityStatsFull',
        'Antigravity Usage Intelligence',
        vscode.ViewColumn.One,
        {
          enableScripts: true,
          retainContextWhenHidden: true,
          localResourceRoots: [context.extensionUri]
        }
      );

      fullPanel.webview.html = getWebviewContent(fullPanel.webview, context.extensionUri);

      fullPanel.webview.onDidReceiveMessage(async (message) => {
        await handleWebviewMessage(fullPanel.webview, message);
      });

      fullPanel.onDidDispose(() => {
        fullPanel = null;
      }, null, context.subscriptions);
    })
  );

  // 3. Register Refresh Command
  context.subscriptions.push(
    vscode.commands.registerCommand('antigravity-stats.refresh', () => {
      if (statsProvider) statsProvider.refresh();
      vscode.window.showInformationMessage('Antigravity Stats refreshed.');
    })
  );

  // 4. Register Rebuild Cache Command
  context.subscriptions.push(
    vscode.commands.registerCommand('antigravity-stats.rebuildCache', async () => {
      const progressOptions = { location: vscode.ProgressLocation.Notification, title: 'Rebuilding Antigravity stats...', cancellable: false };
      vscode.window.withProgress(progressOptions, async () => {
        try {
          const rebuildData = await fetchStatsData(['--force']);
          if (statsProvider) statsProvider.pushStats(rebuildData);
          vscode.window.showInformationMessage('Antigravity Stats: cache rebuild complete.');
        } catch (err) {
          // Silently log to status bar tooltip instead of scary red popup
          if (statusBarItem) {
            statusBarItem.tooltip = `Antigravity Stats rebuild failed: ${err.message}. Click to open dashboard.`;
          }
          vscode.window.showWarningMessage(`Antigravity Stats: rebuild issue — ${err.message.slice(0, 120)}`);
        }
      });
    })
  );

  // 5. Register Export Command
  context.subscriptions.push(
    vscode.commands.registerCommand('antigravity-stats.exportReport', async () => {
      const data = await fetchStatsData();
      const doc = await vscode.workspace.openTextDocument({
        content: JSON.stringify(data, null, 2),
        language: 'json'
      });
      await vscode.window.showTextDocument(doc);
    })
  );

  // 6. Config change listener
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration('antigravity-stats')) {
        firedQuotaAlerts = {};
        setupAutoRefresh(context);
      }
    })
  );

  // 7. Initialize status bar & timer
  setupAutoRefresh(context);
}

function deactivate() {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
  if (activeChildProcess) {
    try { activeChildProcess.kill(); } catch (e) {}
    activeChildProcess = null;
  }
  if (statusBarItem) {
    statusBarItem.dispose();
  }
  if (fullPanel) {
    fullPanel.dispose();
    fullPanel = null;
  }
}

module.exports = {
  activate,
  deactivate
};
