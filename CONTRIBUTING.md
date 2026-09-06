# Contributing to Antigravity Usage Intelligence

Thank you for your interest in contributing to **Antigravity Usage Intelligence**! We welcome bug reports, feature requests, documentation enhancements, and code contributions.

---

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

---

## Development Setup

### Prerequisites
- **Node.js**: v18 or higher (v20+ recommended)
- **Python**: v3.9 or higher (standard library only; zero pip dependencies needed!)
- **VS Code** or **Google Antigravity IDE**

### Getting Started

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/Nir-Bhay/antigravity-usage-intelligence.git
   cd antigravity-usage-intelligence
   ```

2. **Install development dependencies:**
   ```bash
   npm install
   ```

3. **Run syntax validation and test suite:**
   ```bash
   npm test
   ```

4. **Test the Python collector directly on your machine:**
   ```bash
   python collector.py --json
   ```

5. **Launch extension in debug mode:**
   - Press `F5` in VS Code or Antigravity IDE to launch an Extension Development Host.
   - Run the command `Antigravity: Open Full Screen Dashboard` from the Command Palette (`Ctrl+Shift+P`).

---

## Pull Request Guidelines

1. **Create a branch:**
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. **Ensure tests and syntax checks pass:**
   ```bash
   npm test
   ```
3. **Commit with clear conventional commit messages:**
   - `feat: add support for custom quota thresholds`
   - `fix: resolve sidebar tile clipping on narrow viewports`
   - `docs: update telemetry architecture diagram`
4. **Push to your fork and submit a PR:**
   - Fill out the PR template completely.
   - Ensure CI checks pass on both Ubuntu and Windows.

---

## Core Philosophy

- **100% Offline & Zero Telemetry**: This extension must never make unauthorized outbound network requests. All telemetry parsing must remain 100% local.
- **Zero Third-Party Python Dependencies**: The collector must work out-of-the-box on any system with a standard Python installation (`sqlite3`, `json`, `os`, `sys`).
- **High-Density, Modern UI**: The dashboard must remain visually stunning, responsive, and space-efficient across both wide editor tabs and narrow sidebars.
