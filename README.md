# Antigravity Usage Intelligence

<p align="center">
  <img src="assets/icon.png" alt="Antigravity Usage Intelligence Logo" width="128" height="128" />
</p>

<p align="center">
  <strong>The definitive token telemetry, context cache efficiency, and agent forensics engine for Google Antigravity & AI Coding Assistants.</strong>
</p>

<p align="center">
  <a href="https://github.com/Nir-Bhay/antigravity-usage-intelligence/actions"><img src="https://img.shields.io/github/actions/workflow/status/Nir-Bhay/antigravity-usage-intelligence/ci.yml?branch=main&style=flat-square&logo=github&label=CI%20Build" alt="CI Status" /></a>
  <a href="https://marketplace.visualstudio.com/items?itemName=nirbhay-hiwse.antigravity-usage-intelligence"><img src="https://img.shields.io/badge/VS%20Code%20Marketplace-v1.0.0-007ACC?style=flat-square&logo=visual-studio-code&logoColor=white" alt="VS Code Marketplace" /></a>
  <a href="https://open-vsx.org/extension/nirbhay-hiwse/antigravity-usage-intelligence"><img src="https://img.shields.io/badge/Open%20VSX-v1.0.0-9C27B0?style=flat-square&logo=eclipse-ide&logoColor=white" alt="Open VSX" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg?style=flat-square" alt="License: MIT" /></a>
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-blue?style=flat-square" alt="Platform" />
  <img src="https://img.shields.io/badge/Privacy-100%25%20Offline%20%7C%20Zero%20Telemetry-10b981?style=flat-square" alt="100% Offline" />
  <img src="https://img.shields.io/badge/Prompt%20Cache%20Efficiency-90.2%25-success?style=flat-square" alt="Cache Hit Rate" />
</p>

---

## ⚡ Overview

Google Antigravity builds deep contextual abstractions, indexes multi-repo codebases, and executes autonomous tool loops. In active projects, pairing with frontier models pushes tens of millions of tokens daily across **Gemini 3.8 Flash**, **Gemini 3.7 Flash**, **Claude Sonnet 4.6**, and **Claude Opus 4.6**.

Until now, developers were flying blind:
- **Hidden Context Burn**: No visibility into whether an agent turn re-read 200K cached tokens or triggered a costly raw prompt rebuild.
- **Buried Reasoning Overhead**: Frontier thinking tokens were locked inside internal SQLite protobuf blobs without dedicated tracking.
- **Unverified Quotas**: Artificial fixed limits gave misleading alarms instead of tracking official server-side pools.
- **Zero Session Forensics**: No fast way to audit modified files, tool execution counts, or long-term developer consistency.

**Antigravity Usage Intelligence** solves this completely. Operating **100% locally and privately**, it extracts session ledgers directly from your machine and connects to the Antigravity Language Server via Connect-RPC to provide a real-time, responsive command center inside your IDE.

---

## 🚀 Key Features

### 📅 1. GitHub-Grade Activity Heatmap & Consistency Grid
- **Authentic 7-Day Weekday Matrix**: Aligned from Monday to Sunday with GitHub standard labels (`Mon`, `Wed`, `Fri`) and month headers.
- **4-Level Emerald Intensity Scale**: Visualizes coding density with sleek rounded tiles and an amber/cyan glowing ring for **Today**.
- **Interactive Tooltips & 1-Click Filtering**: Hover any day to inspect input, cache, output, thinking tokens, turns, and sessions. Click any day to immediately filter the entire dashboard to that date.
- **3 Time Span Views**: Toggle effortlessly between **Last 30 Days** (5 weeks), **90 Days View** (13 weeks), and **All History** (full historical timeline).

### ⚡ 2. Live Antigravity Language Server Quota Sync
- **Official Connect-RPC Client**: Queries the local `language_server_windows_x64.exe` (`/exa.language_server_pb.LanguageServerService/GetUserStatus`) with CSRF authentication over HTTPS localhost.
- **True Subscription Pools**: Surfaces your verified tier (`Google AI Pro`), remaining capacity fractions (e.g., 27% available / 73% used), and prompt/flow credits (`500 Prompt Credits`, `100 Flow Credits`).
- **Live Reset Countdown**: Dynamic timer calculated directly from the server's ISO `resetTime`.
- **Graceful Fallback**: Automatically falls back to rolling 5-hour local sliding window calculations if the language server is offline.

### 🧠 3. Frontier 2026 Model Intelligence & Reasoning Share
- **Granular Model Analytics**: Detects runtime model executions from `executor_metadata` and `gen_metadata`:
  - **Gemini 3.8 Flash** & **Gemini 3.7 Flash**
  - **Claude Sonnet 4.6** & **Claude Opus 4.6 (Thinking)**
  - **Gemini 3.6 Flash**, **Gemini 3.5 Flash**, **Gemini 3.1 Pro**, and **Gemini Pro Agent**
- **Token Type Breakdown**:
  - 🟧 **Thinking / Reasoning Tokens**: Internal reasoning steps from hybrid thinking models.
  - 🟪 **Prompt Cache Hits**: Context tokens served at high speed from cache.
  - 🟩 **Generation Output Tokens**: Model completions and code diffs.
  - 🟦 **Fresh Input Tokens**: Non-cached prompt tokens.

### 🕒 4. Circadian Rhythm: 24-Hour Peak Coding Flow
- Maps your agent sessions, turns, and token throughput across all 24 hours of the day.
- Identifies your peak deep-work hours, late-night debugging marathons, and team collaboration patterns.

### 🔍 5. Deep Session Inspector & Tool Execution Tracker
- Slide-out glassmorphic drawer inspecting individual sessions:
  - Exact session UUID and workspace project path.
  - Duration, turn count, and token distribution progress bar.
  - Categorized tool execution pills (`run_command`, `replace_file_content`, `view_file`, `grep_search`, `write_to_file`).
  - 1-click **Copy Session ID** and **Copy Markdown Report** buttons.

### 📱 6. Dual Responsiveness: Full Dashboard vs Right Sidebar
- **Full Dashboard (Width ≥ 680px)**: Side-by-side flex layout with ~125px vertical footprint, saving > 60% vertical space compared to standard panels.
- **Right Sidebar (Width < 680px down to 280px)**: Seamless vertical column stack with touch-friendly horizontal scrolling and responsive 2×2 / 1-column status grids.

---

## 🏗️ Architecture & Data Flow

```mermaid
flowchart TD
    subgraph Local Storage [Local Disk / Ledgers]
        A["Antigravity SQLite Ledgers<br/>(~/.gemini/antigravity/conversations/*.db)"]
        B["Local Language Server<br/>(language_server_windows_x64.exe)"]
    end

    subgraph Telemetry Engine [Usage Intelligence Core]
        C["Python Telemetry Engine (collector.py)<br/>• Read-Only WAL Mode (?mode=ro&immutable=1)<br/>• Non-blocking Protobuf Parser<br/>• Atomic Incremental Cache (<80ms)"]
        D["Live Quota Detector (src/quota_detector.js)<br/>• Connect-RPC over HTTPS Loopback<br/>• CSRF Protected Local IPC"]
    end

    subgraph Extension Host [VS Code / Antigravity IDE]
        E["Extension Backend (extension.js)<br/>• Status Bar Item<br/>• Multi-View Controller"]
        F["Interactive Webview (src/ui/dashboard.html)<br/>• GitHub-Grade Heatmap<br/>• Dual Model Radial Gauges<br/>• Session Drawer & Search"]
    end

    A -->|Safe Read-Only WAL| C
    B -->|Connect-RPC HTTPS| D
    C -->|JSON Payload| E
    D -->|Live Quota Sync| E
    E -->|CSP & Nonce IPC| F
```

---

## 🔒 Privacy & Security First

- **100% Offline & Private**: Zero outbound internet calls. No telemetry beacons, no external analytics, no cloud data harvesting.
- **Non-Contention Database Access**: Opened using `?mode=ro&immutable=1` and `PRAGMA query_only = ON`. Will never lock or corrupt active pair-programming sessions.
- **Safe Local RPC**: Connects exclusively to `127.0.0.1` using the session's internal CSRF token.
- **Zero Third-Party Python Dependencies**: Runs out-of-the-box using the standard Python library (`sqlite3`, `json`, `os`, `sys`).

---

## 📦 Quick Start & Installation

### Option 1: VS Code / Cursor / Antigravity IDE Marketplace
1. Open the Extensions view (`Ctrl+Shift+X` or `Cmd+Shift+X`).
2. Search for `Antigravity Usage Intelligence`.
3. Click **Install**.

Or install directly via CLI:
```bash
code --install-extension nirbhay-hiwse.antigravity-usage-intelligence
```

### Option 2: Open VSX Registry (VSCodium, Gitpod, Cursor)
```bash
ovsx get nirbhay-hiwse.antigravity-usage-intelligence
```

### Option 3: Manual VSIX Installation
1. Download `antigravity-usage-intelligence-1.0.0.vsix` from [GitHub Releases](https://github.com/Nir-Bhay/antigravity-usage-intelligence/releases).
2. Install via command line:
   ```bash
   code --install-extension antigravity-usage-intelligence-1.0.0.vsix
   ```
   Or use the Command Palette (`Ctrl+Shift+P` → **Extensions: Install from VSIX...**).

---

## ⌨️ Command Palette & Shortcuts

Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (macOS):

| Command | Title | Description |
| :--- | :--- | :--- |
| `antigravity-stats.openDashboard` | `Antigravity Stats: Open Full Screen Dashboard` | Opens the interactive analytics dashboard in an editor tab |
| `antigravity-stats.refresh` | `Antigravity Stats: Refresh Stats` | Runs an incremental scan of newly recorded sessions |
| `antigravity-stats.rebuildCache` | `Antigravity Stats: Rebuild Full History Cache` | Wipes the cache and re-indexes all conversation databases |
| `antigravity-stats.exportReport` | `Antigravity Stats: Export Token Usage Report (JSON)` | Exports all current analytics data to a new JSON document |

---

## ⚙️ Configuration Settings

Open Settings (`Ctrl+,` or `Cmd+,`) and search for `antigravity-stats`:

| Setting | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `antigravity-stats.pythonPath` | `string` | `""` (Auto-detect) | Path to Python binary (e.g. `C:\Python311\python.exe` or `/usr/bin/python3`). |
| `antigravity-stats.showStatusBar` | `boolean` | `true` | Show today's token counter in the IDE status bar. |
| `antigravity-stats.autoRefreshMinutes` | `number` | `3` | Background polling interval in minutes to keep status bar fresh. |
| `antigravity-stats.defaultRange` | `string` | `"today"` | Default time range loaded when opening dashboard (`today`, `yesterday`, `7d`, `30d`, `90d`, `180d`, `all`). |

---

## 🛠️ Development & Building

```bash
# Clone the repository
git clone https://github.com/Nir-Bhay/antigravity-usage-intelligence.git
cd antigravity-usage-intelligence

# Install dev dependencies
npm install

# Run syntax tests and linting
npm test

# Test the Python collector directly
python collector.py --json

# Package VSIX for distribution
npx @vscode/vsce package --no-git-tag-version
```

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before submitting pull requests.

---

## 📄 License

MIT License © 2026 [Nirbhay Hiwse](https://github.com/Nir-Bhay). Built with care for the global AI engineering community.
