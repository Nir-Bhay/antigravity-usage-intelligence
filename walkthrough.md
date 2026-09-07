# Walkthrough: Real Frontier Model Detection & Model Intelligence UI Redesign

We resolved the obsolete model names issue and transformed the **Model Intelligence & Reasoning Share** widget into a sleek, compact card with an interactive dropdown selector and quick-switch pills.

---

## 1. Root Cause Analysis & Model Detection Fix

### The Problem
Previously, `collector.py` relied solely on an internal protobuf field ID integer in `gen_metadata` mapped through a static dictionary. This resulted in deprecated model labels from older test sessions (`Gemini 2.5 Pro`, `Gemini 1.5 Pro`, `Gemini (ID:1132)`).

### The Solution
By inspecting the internal SQLite conversation databases in `~/.gemini/*/conversations/*.db`, we discovered that:
1. The `executor_metadata` table contains the true runtime model strings executed by the Antigravity agent per step (`gemini-3.8-flash-high`, `gemini-3.7-flash-high`, `gemini-3.6-flash-high`, `gemini-3.5-flash-low`, `gemini-3.1-pro-low`, `claude-sonnet-4-6`, `claude-opus-4-6-thinking`, `gemini-pro-agent`, `gemini-3-flash-agent`).
2. We implemented `normalize_model_name()` in [collector.py](file:///c:/Users/lenovo/Antigravity%20useres%20stats/collector.py) to map these runtime slugs directly to clean display names:
   - **Gemini 3.8 Flash**
   - **Gemini 3.7 Flash**
   - **Gemini 3.6 Flash**
   - **Gemini 3.5 Flash**
   - **Gemini 3.1 Pro**
   - **Gemini 3 Flash**
   - **Gemini Pro Agent**
   - **Claude Sonnet 4.6**
   - **Claude Opus 4.6**
3. In [collector.py](file:///c:/Users/lenovo/Antigravity%20useres%20stats/collector.py#L196-L245), `parse_session_db` now extracts the exact model used for each step from `executor_metadata`, falls back to `gen_metadata`, and dynamically updates the session model.
4. Incremental cache invalidation was added so any cached session containing deprecated labels (`1.5`, `2.5`, `ID:`) is automatically re-evaluated to its true 2026 model.

### Verified Model Breakdown from User's Local Database
```
Gemini 3.7 Flash   -> 762,919,162 tokens (28.8%, 29 sessions)
Gemini 3 Flash     -> 435,681,613 tokens (16.5%, 15 sessions)
Gemini Pro Agent   -> 435,555,078 tokens (16.5%, 29 sessions)
Gemini 3.8 Flash   -> 396,293,368 tokens (15.0%, 14 sessions)
Gemini 3.6 Flash   -> 333,313,822 tokens (12.6%, 23 sessions)
Gemini 3.5 Flash   -> 209,957,086 tokens (7.9%, 12 sessions)
Claude Sonnet 4.6  -> 46,833,744 tokens (1.8%, 22 sessions)
Gemini 3.1 Pro     -> 22,074,313 tokens (0.8%, 24 sessions)
Claude Opus 4.6    -> 2,950,108 tokens (0.1%, 7 sessions)
```

---

## 2. UI Redesign of "Model Intelligence & Reasoning Share"

### The Problem
The previous widget stacked 6 massive cards on top of each other, taking over 480px of vertical space with repetitive bars and cluttered subtext.

### The New Architecture in [dashboard.html](file:///c:/Users/lenovo/Antigravity%20useres%20stats/src/ui/dashboard.html)
1. **Interactive Model Dropdown (`#model-select`)**:
   - Located directly in the widget's header.
   - Allows switching between:
     - `⚡ All Models (Fleet Overview)`
     - Any individual detected model with its share percentage (e.g., `Gemini 3.8 Flash (15.0%)`, `Claude Sonnet 4.6 (1.8%)`).
2. **Compact Active Intelligence Card**:
   - **Multi-Segment Bar (10px height)**:
     - 🟧 **Thinking / Reasoning Mode** (`#f59e0b`)
     - 🟩 **Text Output Generation** (`#22c55e`)
     - 🟪 **Context Cache Read** (`#a855f7`)
     - 🟦 **Fresh Prompt Input** (`#38bdf8`)
     - Hovering any segment displays non-clipping floating tooltips with token count and percentage share.
   - **4 Stat Tiles**:
     - 🧠 **Thinking / Reasoning**: Token volume and % of output generation.
     - ⚡ **Context Cache Read**: Cache volume and hit ratio.
     - 📝 **Text Generation**: Pure text tokens.
     - 📥 **Fresh Input**: Uncached prompt tokens.
3. **1-Click Quick Switch Pills**:
   - Clean horizontal row of pills (`⚡ All`, `Gemini 3.8 Flash`, `Claude Sonnet 4.6`, etc.).
   - Clicking any pill immediately switches the dropdown, updates the reasoning bar, and displays that model's stats.
4. **Instant Table Filter**:
   - When inspecting an individual model, a `🔍 Filter Sessions` button instantly filters the session history table to only sessions using that model and smoothly scrolls down.

---

## 3. Packaging & Local Deployment

1. **Prepublish Verification**:
   - `node -c extension.js` passed with 0 errors.
   - `python -m py_compile collector.py` passed with 0 errors.
2. **VSIX Built**:
   - Packaged `antigravity-usage-intelligence-1.0.0.vsix` via `@vscode/vsce package`.
3. **Installed Locally**:
   - VS Code: `code --install-extension antigravity-usage-intelligence-1.0.0.vsix --force` -> **Success**
   - Cursor: `cursor --install-extension antigravity-usage-intelligence-1.0.0.vsix --force` -> **Success**

---

## 4. Next-Level Agent Activity Heatmap Redesign

### The Problem
As shown in the user's screenshot, the previous heatmap suffered from a visual defect:
- 16 fixed 11px columns (~224px) were crammed on the far left of the card.
- More than 65% of the right side remained completely blank ("blanket" / empty void).
- Lacked day-of-month indicators and overall consistency metrics.

### The Solution: 100% Full-Width Split Layout

The new heatmap completely fills the card width and defaults to a dedicated **Last 30 Days** overview:

1. **Left Side: 30-Day Calendar Matrix (`55%` width)**
   - **Aligned Weekday Grid**: Displays 7 columns with labels (`Mon`, `Tue`, `Wed`, `Thu`, `Fri`, `Sat`, `Sun`).
   - **Tactile Day Tiles (28px height)**: Each tile displays the actual day number (`1` to `31`), cleanly rounded with modern glassmorphism styling.
   - **Color Intensity Tiers**:
     - `heat-0`: Inactive days (subtle dark gray border).
     - `heat-1`: Low activity (`#065f46`, emerald glow).
     - `heat-2`: Medium activity (`#059669`).
     - `heat-3`: High activity (`#10b981`).
     - `heat-4`: Peak activity (`#34d399`, `#10b981` radial glow).
   - **Today Indicator**: Marked with an amber/cyan glowing border and tag.
   - **Interactive Floating Tooltips**: Hovering any day displays full date, total tokens, cache reads, reasoning tokens, text output, and turn/session counts.
   - **1-Click Day Filter**: Clicking any calendar tile immediately sets the dashboard date filter to that specific day.

2. **Right Side: Consistency & Velocity Status Panel (`45%` width)**
   - **30-Day Consistency Progress Bar**: Displays active day frequency (e.g., `18 / 30 Days (60%)`) with an animated emerald gradient bar.
   - **4 Status KPI Cards**:
     - ⚡ **30-Day Tokens**: Total volume (e.g., `1.28B`) and turn count across the 30-day rolling window.
     - 🔥 **Peak Daily Run**: The date and token count of the single highest agent session day.
     - 🚀 **Active Day Pace**: Average token throughput per active coding day.
     - 📅 **Window Span**: Formatted start and end dates for the 30-day window.
   - **1-Click Filter Action**: "📅 Filter Dashboard to Last 30 Days" button that immediately updates all charts and session tables to the 30-day period.

3. **View Switcher Pill Buttons**:
   - Easily toggle between **"Last 30 Days"** (calendar matrix + status panel) and **"90 Days View"** (full-width continuous multi-month matrix) right from the card header.

---

## 5. Daily Token Consumption Trend: Today's Date & Auto-Scroll Fix

### The Problem
- The daily bar chart started on June 14, 2026 (the oldest date in the database).
- Because `scrollLeft` defaults to `0`, whenever the dashboard opened, the chart showed the oldest date (**June 14**) on the far left. The user had to scroll all the way through June, July, and August to see **September 6 (Today)** on the right.
- Due to lack of `overflow-y: hidden`, the horizontal scrollbar pushed the container content height, causing an ugly vertical scrollbar with up/down arrows to appear on the card.

### The Solution in [dashboard.html](file:///c:/Users/lenovo/Antigravity%20useres%20stats/src/ui/dashboard.html)
1. **Default 30-Day Rolling View (`trendViewMode = '30d'`)**:
   - By default, the chart displays the last 30 calendar days ending today (August 8 – September 6).
   - Past dates from June are neatly tucked away unless the user explicitly switches to `All Time`.
2. **Auto-Scroll to Rightmost Edge (Today / Latest Date)**:
   - On render, layout calculation, and view switches, `barsContainer.scrollLeft = barsContainer.scrollWidth` is called.
   - Today's date (September 6) is immediately visible on the right of the chart window upon opening.
3. **Dedicated "Today" Indicator & Highlight**:
   - The bar for today features a cyan glowing border (`is-today-bar`), box shadow, and a distinct cyan `Today` label with an active indicator dot.
   - If today has no recorded sessions yet, a clean baseline placeholder is rendered so today's date is never absent.
4. **Header Today Badge**:
   - A live pill badge in the card header immediately displays:
     `📅 Today (Sep 6): 131.4M (X turns)`.
5. **View Mode Toggles**:
   - Added pill buttons right in the header:
     - `Last 30 Days` (Default)
     - `Last 14 Days` (Expanded bars)
     - `All Time` (Full history back to June 14, automatically scrolled to today)
6. **"➔ Latest (Today)" Quick-Jump Button**:
   - If the user scrolls back to inspect past days (e.g. June or July), a floating pill button appears at the bottom-right: `Latest (Today) ➔`. Clicking it smoothly glides the view back to today.
7. **Eliminated Vertical Scrollbar**:
   - Added `overflow-y: hidden;` and sleek custom scrollbars (`::-webkit-scrollbar` with 5px height and dark pill thumb).

---

## 6. Rolling 5-Hour Model Quota: Dual Circular Radial Gauges (Gemini & Claude)

### The Problem
As shown in the user's screenshot:
- The previous card was a plain text banner with verbose descriptions (`33.15M tokens across 214 turns in active window (1 sessions)`).
- It lumped all models into a single generic bucket without distinguishing the separate quota ceilings and limitations of **Google Gemini** vs **Anthropic Claude**.
- It lacked visual hierarchy, graphs, and modern progress indicators.

### The Solution in [collector.py](file:///c:/Users/lenovo/Antigravity%20useres%20stats/collector.py) & [dashboard.html](file:///c:/Users/lenovo/Antigravity%20useres%20stats/src/ui/dashboard.html)
1. **Backend Separation by Model Family**:
   - In `collector.py`, sessions in the 5-hour rolling window are classified into:
     - **Gemini Family**: Baseline quota window of **100M tokens** (e.g. Gemini 3.8 Flash, 3.7 Flash, 3.1 Pro).
     - **Claude Family**: Rate-limited quota window of **15M tokens** (e.g. Claude Sonnet 4.6, Claude Opus 4.6).
   - Computes tokens, turns, active sessions, and percentage used for both models in real time.
2. **Dual SVG Circular Radial Gauges**:
   - **Google Gemini Fleet Ring (Cyan `#38bdf8` to Mint `#34d399`)**:
     - Large center percentage display (e.g., `68% USED`).
     - Real-time gauge: `68.28M / 100M quota`.
     - Active model pill: `Gemini 3.8 Flash`.
     - Status badge: `● 31.7M Available` (switches to amber/red if nearing capacity).
   - **Anthropic Claude Fleet Ring (Purple `#a855f7` to Rose `#f43f5e`)**:
     - Center percentage display (e.g., `0% USED`).
     - Real-time gauge: `0.0M / 15M quota`.
     - Active model pill: `Claude Sonnet 4.6`.
     - Status badge: `● 15.0M Available (100%)`.
3. **Card Header**:
   - Ambient glowing bolt icon (`⚡`).
   - Title: `Rolling 5-Hour Model Quota Window` with pulsing `Active Session` / `Healthy` badge.
   - Clean reset timer: `WINDOW RESETS IN 4h 59m` with clock icon.
   - Replaced sentence descriptions with concise metrics.
4. **Interactive Floating Tooltips**:
   - Hovering either circular gauge shows full details on 5-hour consumption, baseline thresholds, and sliding window behavior.

---

## 7. Default Time Range: "Today" Always Active by Default

### The Problem
- Previously, opening the Antigravity dashboard defaulted to `All Time`, loading full historical data from June 14, 2026.
- Users had to manually click the `Today` pill every time they opened the analytics panel or reloaded.

### The Solution
1. **HTML Filter Bar Initial State**:
   - In [dashboard.html](file:///c:/Users/lenovo/Antigravity%20useres%20stats/src/ui/dashboard.html), the `Today` pill now defaults with the `.active` class (`<button class="filter-btn active" data-range="today">Today</button>`).
2. **Immediate "Today" Initialization**:
   - On load, the webview immediately sends `{ command: 'init', start: todayStr, end: todayStr }` to fetch today's stats on opening.
3. **Backend Fallback in [extension.js](file:///c:/Users/lenovo/Antigravity%20useres%20stats/extension.js)**:
   - `config.get('defaultRange', 'today')` automatically slices the date window to today's local date if no dates are passed.
4. **Configuration Schema in [package.json](file:///c:/Users/lenovo/Antigravity%20useres%20stats/package.json)**:
   - `antigravity-stats.defaultRange` default updated from `"all"` to `"today"`, supporting all options: `"today"`, `"yesterday"`, `"7d"`, `"30d"`, `"90d"`, `"180d"`, and `"all"`.
5. **Documentation Updated**:
   - [README.md](file:///c:/Users/lenovo/Antigravity%20useres%20stats/README.md) and [llms.txt](file:///c:/Users/lenovo/Antigravity%20useres%20stats/llms.txt) updated to reflect `"today"` as the default setting.

---

## 8. Refined Glassmorphic KPI Cards & Tool Requests

### The Problem
- Every KPI card had a flat 2px solid colored border strip along the top edge (`.kpi-card::before`) which looked harsh and unpolished.
- The **Cache Dollar Savings** card showed synthetic dollar amounts ($7.04) that were irrelevant for users operating on standard Antigravity quotas.
- The **Tool Reliability** card showed a static 100% metric that provided no actionable insight into agent operations.
- The 8-card grid wrapped into 3 columns, leaving an awkward empty gap in the 3rd row.

### The Solution in [dashboard.html](file:///c:/Users/lenovo/Antigravity%20useres%20stats/src/ui/dashboard.html)
1. **Removed Flat Top Borders**:
   - Removed `.kpi-card::before` 2px top border stripe entirely across all cards.
2. **Modern Glassmorphic Surface**:
   - Upgraded cards with subtle dark gradients (`linear-gradient(145deg, rgba(30, 41, 59, 0.45), rgba(15, 23, 42, 0.6))`), soft border (`1px solid rgba(255, 255, 255, 0.08)`), rounded corners (`10px`), and smooth hover lift with ambient glow (`transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4), 0 0 12px rgba(56, 189, 248, 0.1)`).
3. **Removed Irrelevant Cards**:
   - Dropped **Cache Dollar Savings** and **Tool Reliability (100%)**.
4. **Added "Tool Requests" Card**:
   - Displays real agent execution activity: `total_tool_calls` (e.g. `809 calls`) with a tool icon, rose chip, and descriptive subtext (`Agent tool executions`).
5. **Retained Essential Metrics**:
   - **Reasoning Tokens**: Amber thinking mode counter with dedicated chip.
   - **Cache Efficiency**: Mint hit-rate percentage with dedicated chip.
   - **Prompt Cache Hits**: Purple context cache volume.
   - **Input (Prompt)** & **Output Tokens**: Blue and emerald counters.
6. **Hero Card Layout & Zero-Gap Balance**:
   - **Total Tokens** spans 2 columns (`.kpi-card-hero`) with larger typography (`23px`).
   - Row 1: `Total Tokens (2 cols)` + `Input (1 col)` + `Output (1 col)` = **4 columns**.
   - Row 2: `Prompt Cache (1 col)` + `Cache Efficiency (1 col)` + `Reasoning Tokens (1 col)` + `Tool Requests (1 col)` = **4 columns**.
   - Completely fills both rows with zero empty slots.

---

## Walkthrough: Activity Heatmap Redesign & Release v1.0.5

Completed GitHub-style activity matrix redesign, space optimization, and backend aggregation:

1. **Continuous GitHub-Style Activity Matrix**:
   - Replaced fixed 30d/90d views with a continuous 26-week (~6 months) rolling contribution matrix ending on the current week.
   - Fixed month label alignments directly over starting week columns.
   - Added automatic right-scroll on open (`scrollLeft = scrollWidth`) so Today's active week is always immediately visible.
   - All past dates are rendered as valid contribution cells (`heat-0` through `heat-4`), eliminating awkward blank gaps on the left.
2. **Removed Cluttery Tab Controls**:
   - Stripped `Last 30 Days`, `90 Days View`, and `All History` buttons from the header.
   - Kept a clean header with title on the left and standard GitHub contribution legend on the right.
3. **Streamlined Summary Bar (Removed 4 Bulky Cards)**:
   - Eliminated the bulky 4-card grid (`90D TOKENS`, `ACTIVE PACE`, `WINDOW`) and heavy consistency progress bar.
   - Implemented a sleek single-line summary bar displaying:
     - **Active Days & Consistency %**: `Active: 42 days (23%)`
     - **Peak Activity Day**: `🔥 Peak: Sep 6 (664.17M)`
     - **Daily Coding Streak**: `⚡ Streak: 3d`
4. **Enhanced "Filter Dashboard to All History" Action**:
   - Modernized action button with icon to quickly switch the entire dashboard to all historical sessions.
5. **Backend Data Persistence (`collector.py`)**:
   - Added `all_daily` historical aggregation so the heatmap matrix always shows the full 6-month graph even if the top navigation filter is set to "Today" or "Yesterday".
6. **Packaging & Release**:
   - Built `antigravity-usage-intelligence-1.0.5.vsix` and installed locally into Antigravity IDE (`--force`).
   - Tagged `v1.0.5` and published GitHub release at `https://github.com/Nir-Bhay/antigravity-usage-intelligence/releases/tag/v1.0.4`.

### The Solution in [dashboard.html](file:///c:/Users/lenovo/Antigravity%20useres%20stats/src/ui/dashboard.html)
1. **Glassmorphic Surface & Smooth Animation**:
   - Upgraded drawer frame to `440px` width with deep glass gradient (`linear-gradient(180deg, #0d1526, #080c18)`), cyan border glow (`rgba(56, 189, 248, 0.25)`), smooth cubic-bezier sliding transition, and sleek 5px custom scrollbars.
   - Backdrop filter with `rgba(0, 0, 0, 0.7)` and `blur(6px)`.
2. **Executive Header**:
   - Workspace project badge with folder icon and live session status badge (`Recorded Session`).
   - Crisp session title with `15px` typography and high contrast readability.
   - Circular glass close button (`✕`) with red hover state.
3. **4-Tile Key Specs Grid**:
   - 🤖 **Active Model**: Dedicated model pill (Cyan for Gemini, Purple for Claude).
   - ⏱️ **Session Duration**: Formatted duration with timer icon.
   - 📅 **Timestamp**: Formatted start timestamp with calendar icon.
   - 💬 **Agent Turns**: Turns counter with conversation icon.
4. **Token Consumption Card & Visual Distribution Bar**:
   - **Horizontal Proportion Bar**: Animated 8px multi-color bar displaying the exact ratio of Cache (purple), Input (blue), Output (green), and Thinking (amber).
   - **Token Metric Rows**: Displays label, percentage share of total (e.g. `92.4%`), and monospace token amount for each slice.
   - **Total Processed Banner**: Bold cyan counter with an active `Cache Efficiency` pill in the card header.
5. **Categorized Tools Executed**:
   - Section header showing total call count (e.g. `809 calls`).
   - Sleek dark tool pills with cyan monospace tool names (`view_file`, `replace_file_content`, etc.) and high-contrast count badges (`204`).
6. **Developer Metadata Card & Inline Copy**:
   - Conversation ID with an inline 1-click `📋 Copy` button.
   - Workspace Path with folder icon and monospace formatting.
7. **Action Buttons**:
   - Secondary button: `[ 📋 Copy Session ID ]`
   - Primary glow button: `[ 📄 Copy Markdown Report ]`

---

## 10. Compact Sizing & Vertical Space Optimization (Quota & KPI Cards)

### The Problem
- As identified in the user's feedback and screenshot:
  1. **Excessive Vertical Footprint**: The Rolling 5-Hour Quota card was ~180px tall and the KPI grid collapsed into 4 rows (`Total Tokens` on row 1, followed by 3 rows of 2 cards each), consuming almost 600px of vertical space before any charts or sessions could be seen.
  2. **Premature Media Query Collapse**: A `@media (max-width: 820px)` breakpoint was forcing the KPI cards into 2 columns on standard extension webview panels (which are usually 600px–750px wide).
  3. **Text Clipping**: The model name chips had `max-width: 130px; text-overflow: ellipsis;`, cutting off `Gemini 3.8 Flash` to `Gemini 3.8 Fl_` and `Claude Sonnet 4.6` to `Claude Sonnet_`.

### The Solution in [dashboard.html](file:///c:/Users/lenovo/Antigravity%20useres%20stats/src/ui/dashboard.html)
1. **Compact Rolling 5-Hour Quota Window**:
   - Resized SVG gauge circles from 76px (`cx=38, cy=38, r=30`) down to 54px (`cx=27, cy=27, r=22`) with `stroke-width: 4.5`.
   - Updated circumference formula to `138.2` (`2 * PI * 22`) in both CSS and JavaScript `updateQuotaCard()`.
   - Removed `max-width: 130px;` on `.quota-active-chip` and reduced font size to `9.5px` so model labels are fully visible with zero clipping.
   - Reduced padding from `14px 16px` to `8px 12px`, top bar margin to `6px`, and typography sizes (`12px` heading, `14px` usage value).
   - Total Quota card height reduced from ~180px down to ~100px.
2. **Dense 2-Row KPI Grid & Breakpoint Fix**:
   - Adjusted media query breakpoint from `820px` down to `580px` so that extension panels maintain the sleek 4-column, 2-row layout.
   - Row 1: `Total Tokens (2 cols)` + `Input (1 col)` + `Output (1 col)`.
   - Row 2: `Prompt Cache (1 col)` + `Cache Efficiency (1 col)` + `Reasoning (1 col)` + `Tool Requests (1 col)`.
   - Reduced card padding from `12px 14px` to `6px 9px` and `min-height` from `82px` to `52px`.
   - Tightened typography: values to `15px` (`17px` on Hero), titles to `10px` with 11px SVG icons, chips to `7.5px`.
   - Total KPI section height reduced from ~390px across 4 rows down to ~115px across 2 rows (> 70% height reduction).
3. **Streamlined Top Controls & Chart Margins**:
   - Filter bar padding reduced to `5px 8px` with `margin-bottom: 8px`.
   - Chart containers updated to `11px 13px` padding with `margin-bottom: 10px`.
4. **VSIX Built and Installed**:
   - Built clean VSIX: `antigravity-usage-intelligence-1.0.0.vsix`.

---

## 11. GitHub-Grade Activity Heatmap & Live Language Server Quota Sync

### The Problem
1. **Clumsy Calendar Heatmap Layout**:
   - The previous iteration attempted a 7-column wall-calendar table with giant 28px square tiles, which looked empty and consumed excessive vertical space.
   - In a wide dashboard, it left massive unused space. In a narrow right sidebar (280px–400px), it broke or caused horizontal layout distortion.
2. **Artificial "100M / 15M" Quota Assumption**:
   - The previous quota display assumed hardcoded static ceilings (`/ 100M quota` and `/ 15M quota`), which did not reflect the true Antigravity server-side subscription pool.

### The Solution

1. **Authentic GitHub Contribution Matrix**:
   - **7 Weekday Rows**: Aligned from Monday (row 0) to Sunday (row 6) with GitHub standard labels on the left (`Mon`, `Wed`, `Fri`).
   - **Month Headers**: Positioned dynamically across the top aligned with the week columns.
   - **Compact Emerald Tiles**: 12px × 12px rounded cells with 4 distinct GitHub emerald heat intensity levels:
     - `heat-0`: Inactive (`rgba(255, 255, 255, 0.035)`)
     - `heat-1`: Low activity (`#0e4429`)
     - `heat-2`: Medium activity (`#006d32`)
     - `heat-3`: High activity (`#26a641`)
     - `heat-4`: Peak activity (`#39d353` with emerald glow)
     - `is-today`: Glowing cyan ring (`#38bdf8`) with box shadow.
   - **Interactive Tooltips & Date Filtering**: Hovering displays comprehensive breakdown (tokens, cached, thinking, output, turns, sessions); clicking any day filters the dashboard to that day.
   - **3 Time Span Views**:
     - `Last 30 Days` (5 weeks)
     - `90 Days View` (13 weeks)
     - `All History` (Full recorded historical span from June 2026 to present)

2. **Perfect Dual Responsiveness (Full Dashboard vs Right Sidebar)**:
   - **Full Dashboard (width ≥ 680px)**:
     - Side-by-side flex layout with `flex: 1.35` for the heatmap grid and `flex: 1` for the compact 4-tile status panel.
     - Height is ~125px, reducing vertical footprint by > 60% compared to the old calendar.
   - **Right Sidebar (width < 680px down to 280px)**:
     - Switches to a vertical column stack (`flex-direction: column; gap: 8px;`).
     - Smooth horizontal touch-scrolling with a subtle 4px custom scrollbar (`::-webkit-scrollbar`).
     - The 4-tile status grid renders as a 2×2 grid (or 1-column on ultra-narrow sidebar ≤ 360px), fitting 100% of viewport width without clipping or overflowing.

3. **Reverse-Engineered Live Antigravity Language Server Quota Sync**:
   - Discovered and connected to local `language_server_windows_x64.exe` Connect-RPC service at `127.0.0.1:<port>/exa.language_server_pb.LanguageServerService/GetUserStatus`.
   - Built [src/quota_detector.js](file:///c:/Users/lenovo/Antigravity%20useres%20stats/src/quota_detector.js) to auto-detect running process PID, CSRF token, and HTTPS listening port.
   - Retrieves official live metrics:
     - **User Tier**: `Google AI Pro` badge with live status.
     - **Credit Balances**: Available Prompt Credits (`500`) and Flow Credits (`100`).
     - **Official Quota Pools**: Real-time `remainingFraction` (e.g. Gemini 27% available / 73% used, Claude 100% available).
     - **Server Reset Countdown**: Live countdown timer calculated from the server's ISO `resetTime`.
   - Graceful fallback to local sliding window metrics if the language server is offline.

4. **VSIX Built and Synced**:
   - Re-packaged clean VSIX: `antigravity-usage-intelligence-1.0.0.vsix`.
   - Installed and synced to **Antigravity IDE**, **VS Code**, and **Cursor** extension paths.

---

## 12. Open-Source GitHub Launch & CI/CD Release Pipeline

### Public Repository Setup
- **Repository**: [https://github.com/Nir-Bhay/antigravity-usage-intelligence](https://github.com/Nir-Bhay/antigravity-usage-intelligence)
- **Primary Branch**: `main`
- **License**: MIT
- **Discoverability Topics**: `antigravity`, `antigravity-ide`, `token-tracker`, `gemini`, `prompt-caching`, `ai-agents`, `vscode-extension`, `telemetry`, `observability`, `developer-tools`

### Engineering Standards & Governance Added
1. **Multi-OS GitHub Actions CI** ([.github/workflows/ci.yml](file:///c:/Users/lenovo/Antigravity%20useres%20stats/.github/workflows/ci.yml)):
   - Matrix testing across `ubuntu-latest` and `windows-latest`.
   - Automated Node 20 & Python 3.11 validation, syntax checks, and automated VSIX packaging via `@vscode/vsce`.
   - Verified Run: `34050209447` finished with status `completed: success`.
2. **Issue & PR Templates**:
   - Structured bug report template with system environment fields ([.github/ISSUE_TEMPLATE/bug_report.md](file:///c:/Users/lenovo/Antigravity%20useres%20stats/.github/ISSUE_TEMPLATE/bug_report.md)).
   - Feature request template ([.github/ISSUE_TEMPLATE/feature_request.md](file:///c:/Users/lenovo/Antigravity%20useres%20stats/.github/ISSUE_TEMPLATE/feature_request.md)).
   - Pull request checklist template ([.github/PULL_REQUEST_TEMPLATE.md](file:///c:/Users/lenovo/Antigravity%20useres%20stats/.github/PULL_REQUEST_TEMPLATE.md)).
3. **Open-Source Community Guidelines**:
   - Detailed contribution guide ([CONTRIBUTING.md](file:///c:/Users/lenovo/Antigravity%20useres%20stats/CONTRIBUTING.md)).
   - Contributor Covenant Code of Conduct ([CODE_OF_CONDUCT.md](file:///c:/Users/lenovo/Antigravity%20useres%20stats/CODE_OF_CONDUCT.md)).
   - Responsible security disclosure policy ([SECURITY.md](file:///c:/Users/lenovo/Antigravity%20useres%20stats/SECURITY.md)).
4. **README Showcase** ([README.md](file:///c:/Users/lenovo/Antigravity%20useres%20stats/README.md)):
   - Live build status & version badges.
   - Mermaid dual-engine architecture diagram (Language Server Connect-RPC vs SQLite Telemetry Pipeline).
   - Core metrics table, CLI & VS Code installation steps, keyboard shortcuts (`Ctrl+Alt+A`), and local privacy guarantees.

### Release v1.0.0
- **Tag**: `v1.0.0`
- **Release URL**: [https://github.com/Nir-Bhay/antigravity-usage-intelligence/releases/tag/v1.0.0](https://github.com/Nir-Bhay/antigravity-usage-intelligence/releases/tag/v1.0.0)
- **Asset Attached**: `antigravity-usage-intelligence-1.0.0.vsix`

---

## 13. Production Release v1.0.1 & Multi-IDE Local Installation

### Core Enhancements in v1.0.1
1. **Live Quota Threshold Alerts**:
   - Added user configurable alerts (`antigravity-stats.quotaAlerts`: `true`, `antigravity-stats.quotaAlertThresholds`: `[75, 90, 100]`).
   - Warning notifications trigger only on authenticated live language server Connect-RPC data, never on speculative estimates.
2. **Deterministic Demo Mode**:
   - Added `antigravity-stats.demoMode` configuration and `--demo` CLI flag to generate mock token trajectories for testing and showcase screenshots without accessing local user databases.
3. **Seamless Auto-Refresh & Ticker**:
   - Silent 30-second background polling without disruptive loading spinners.
   - Immediate refresh on tab focus / visibility change.
   - Real-time 1-second interval countdown timer to quota reset time.
4. **Marketplace Compliance & Governance**:
   - Added comprehensive [PRIVACY.md](file:///c:/Users/lenovo/Antigravity%20useres%20stats/PRIVACY.md) policy.
   - Added Marketplace Review & Compliance Notes to [README.md](file:///c:/Users/lenovo/Antigravity%20useres%20stats/README.md).
   - Documented full changelog entry in [CHANGELOG.md](file:///c:/Users/lenovo/Antigravity%20useres%20stats/CHANGELOG.md).

### Local Installation & Sync Status
- **Antigravity IDE**: Extracted and registered in `C:\Users\lenovo\.antigravity-ide\extensions\nirbhay-hiwse.antigravity-usage-intelligence-1.0.1` and active in `extensions.json`.
- **VS Code**: Installed via `code --install-extension antigravity-usage-intelligence-1.0.1.vsix --force`.
- **Cursor**: Installed via `cursor --install-extension antigravity-usage-intelligence-1.0.1.vsix --force`.

### GitHub Release v1.0.1
- **Commit**: `23ec539` (`feat: release v1.0.1 - quota alerts, demo mode, auto-refresh and privacy docs`)
- **Tag**: `v1.0.1`
- **Release URL**: [https://github.com/Nir-Bhay/antigravity-usage-intelligence/releases/tag/v1.0.1](https://github.com/Nir-Bhay/antigravity-usage-intelligence/releases/tag/v1.0.1)
- **Asset Attached**: `antigravity-usage-intelligence-1.0.1.vsix`

---

## 14. Release v1.0.5 — Continuous Rolling GitHub-Style Activity Matrix
- **Continuous 26-Week Matrix**: Replaced fixed 30d/90d views with a continuous 26-week (~6 month) rolling contribution matrix ending on Today's week.
- **Removed Cluttered Tabs**: Eliminated the "Last 30 Days", "90 Days View", and "All History" tab buttons from the heatmap header.
- **Streamlined Summary Bar**: Replaced bulky 4-card statistics with a sleek, single-line meta bar displaying Active Days, Consistency %, Peak Day, and Current Streak.
- **Persistent Backend Aggregation**: Added `all_daily` to backend analytics collector so the contribution matrix stays fully populated regardless of top-level range filters.

---

## 15. Release v1.0.6 — First-Class Light Theme Support & Dynamic Sync

### The Challenge
In light themes, the dashboard had several visual flaws:
1. Hardcoded dark gradients (`rgba(15, 23, 42, 0.95)`, `rgba(30, 41, 59, 0.8)`) made `.quota-card`, `.kpi-card`, and `.kpi-card-hero` render as pitch-black blocks on a white sidebar/dashboard.
2. The Agent Activity Heatmap rendered empty days with transparent `rgba(255, 255, 255, 0.04)` on a white card, causing empty cells to become completely invisible so only green squares floated in blank space.
3. Summary metrics (`Active: 42 days (24%)`, `Peak: Sep 6`, `Streak: 4d`) used faint text colors (`#f1f5f9`, `#94a3b8`) that washed out against light backgrounds.
4. Model dropdowns and active model cards used hardcoded `#0f172a` black styling.

### The Implementation in [dashboard.html](file:///c:/Users/lenovo/Antigravity%20useres%20stats/src/ui/dashboard.html)
1. **Adaptive CSS Color System**:
   - Injected scoped `body.vscode-light`, `body.theme-light`, and `html[data-vscode-theme-kind="vscode-light"] body` overrides.
   - Cards adapt to clean white surfaces (`#ffffff`, border `#e2e8f0`, soft box-shadow `0 1px 3px rgba(0,0,0,0.04)`).
   - Text colors switch to high-contrast slate (`#0f172a` primary, `#64748b` muted).
2. **GitHub Canonical Light Heatmap**:
   - Empty day cells (`.github-cell.heat-0`) now render with GitHub's light theme standard `#ebedf0` background and subtle border `1px solid rgba(27, 31, 35, 0.06)`. Hover state is `#d0d7de`.
   - Contribution greens map to GitHub's light palette: `#9be9a8` (heat-1), `#40c463` (heat-2), `#30a14e` (heat-3), `#216e39` (heat-4).
   - Today cell highlighted with vivid blue `2px solid #0284c7` and subtle glow.
   - Summary bar styled with `#f8fafc` background, `#e2e8f0` border, `#0f172a` bold text, and colored badges.
3. **High-Contrast KPI Numbers**:
   - Hero card: `linear-gradient(135deg, #f0f9ff 0%, #ffffff 100%)` with deep blue `#0284c7` text.
   - Distinct, vivid high-contrast metrics: Input (`#2563eb`), Output (`#16a34a`), Cache Hits (`#9333ea`), Efficiency (`#059669`), Thinking (`#d97706`), Tool Requests (`#e11d48`).
4. **Light Theme Model Breakdown & Dropdowns**:
   - `.model-select` dropdown styled with crisp white surface `#ffffff`, `#cbd5e1` border, `#0f172a` text, and blue focus ring.
   - `.model-active-card` and metric tiles styled with `#f8fafc` and `#ffffff` surfaces.
5. **Real-Time Dynamic Theme Sync**:
   - Created `syncThemeClass()` helper with automatic detection via class names, `data-vscode-theme-kind`, and computed background luminance fallback.
   - Connected `MutationObserver` on `document.body` and `document.documentElement` to transition between Light, Dark, and High-Contrast themes instantaneously without webview reload.
6. **100% Dark Theme Preservation**:
   - All dark mode glassmorphic styling, neon glows, and gradient cards remain completely untouched when dark themes are active.

### GitHub Release v1.0.6
- **Commit**: `caa9260` (`feat: complete first-class adaptive light theme support with dynamic real-time sync (v1.0.6)`)
- **Tag**: `v1.0.6`
- **Release URL**: [https://github.com/Nir-Bhay/antigravity-usage-intelligence/releases/tag/v1.0.6](https://github.com/Nir-Bhay/antigravity-usage-intelligence/releases/tag/v1.0.6)
- **Asset Attached**: `antigravity-usage-intelligence-1.0.6.vsix`
- **Installed Locally in Antigravity IDE**: Active and verified.



