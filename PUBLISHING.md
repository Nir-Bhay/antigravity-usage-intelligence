# Publishing Guide: Antigravity Usage Intelligence

Complete, production-ready guide for packaging and publishing the **Antigravity Usage Intelligence** extension to both the **Visual Studio Code Marketplace** (Microsoft) and the **Open VSX Registry** (Eclipse Foundation).

---

## 📋 Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Marketplace Configuration Audit](#2-marketplace-configuration-audit)
3. [Visual Studio Marketplace (Microsoft)](#3-visual-studio-marketplace-microsoft)
   - [Step 1: Azure DevOps Organization](#step-1-azure-devops-organization)
   - [Step 2: Generate Personal Access Token (PAT)](#step-2-generate-personal-access-token-pat)
   - [Step 3: Create Publisher in Marketplace Portal](#step-3-create-publisher-in-marketplace-portal)
4. [Open VSX Registry (Eclipse Foundation)](#4-open-vsx-registry-eclipse-foundation)
   - [Step 1: Create Account & Sign In](#step-1-create-account--sign-in)
   - [Step 2: Create & Claim Namespace](#step-2-create--claim-namespace)
   - [Step 3: Generate Access Token](#step-3-generate-access-token)
   - [Step 4: Verify Token Locally](#step-4-verify-token-locally)
5. [Local Validation & Packaging](#5-local-validation--packaging)
6. [Publishing CLI Commands](#6-publishing-cli-commands)
   - [Publish to Visual Studio Marketplace](#publish-to-visual-studio-marketplace)
   - [Publish to Open VSX Registry](#publish-to-open-vsx-registry)
   - [Publishing a Single .vsix to Both Registries](#publishing-a-single-vsix-to-both-registries)
7. [Version Bumping & Release Lifecycle](#7-version-bumping--release-lifecycle)
8. [Troubleshooting & Common Pitfalls](#8-troubleshooting--common-pitfalls)

---

## 1. Prerequisites

Before publishing, ensure you have:

* **Node.js**: v18.0.0 or higher (`node -v`)
* **npm**: v9.0.0 or higher (`npm -v`)
* **Python**: v3.8 or higher (`python --version`) for running prepublish compilation tests
* **Git**: Installed and repository committed to `https://github.com/Nir-Bhay/antigravity-usage-intelligence`
* **Target Publisher ID**: `nirbhay-hiwse` (must match `"publisher"` in `package.json`)

---

## 2. Marketplace Configuration Audit

Ensure `package.json` contains all required metadata fields:

| Field | Configured Value | Marketplace Requirement |
| :--- | :--- | :--- |
| `name` | `antigravity-usage-intelligence` | Lowercase alphanumeric + hyphens |
| `displayName` | `Antigravity Usage — Token Tracker & Quota Intelligence` | Clean human-readable title |
| `publisher` | `nirbhay-hiwse` | Matches publisher account ID |
| `version` | `1.0.7` | Semantic versioning (`MAJOR.MINOR.PATCH`) |
| `engines.vscode` | `^1.80.0` | Target VS Code engine version |
| `icon` | `assets/icon.png` | **128x128px PNG** (strictly required) |
| `categories` | `["AI", "Machine Learning", "Visualization", "Productivity"]` | Valid marketplace categories |
| `repository` | `https://github.com/Nir-Bhay/antigravity-usage-intelligence.git` | Public Git repo |
| `license` | `MIT` | Valid SPDX identifier |

Verify all critical runtime assets exist:
* `extension.js` — Main extension entry point
* `collector.py` — SQLite ledger extraction engine
* `src/ui/dashboard.html` — Webview dashboard
* `assets/icon.png` — 128x128px marketplace icon
* `assets/icon.svg` — Activity bar icon
* `LICENSE` / `LICENSE.txt` — MIT License text
* `README.md` — Detailed documentation & screenshots
* `CHANGELOG.md` — Release history

---

## 3. Visual Studio Marketplace (Microsoft)

Microsoft distributes extensions to VS Code, GitHub Codespaces, and Azure DevOps.

### Step 1: Azure DevOps Organization

1. Navigate to [Azure DevOps](https://dev.azure.com).
2. Sign in with the Microsoft account you want linked to your publisher.
3. If you do not have an organization yet, click **Create new organization** (e.g., `dev.azure.com/nirbhay-hiwse`).

### Step 2: Generate Personal Access Token (PAT)

> [!IMPORTANT]
> A common failure point: When creating the PAT, you **must** select **"All accessible organizations"** under Organization. If you select only a specific organization, the VSCE CLI will fail with `401 Unauthorized`.

1. In Azure DevOps, click the **User Settings** icon (top right corner, next to your profile picture).
2. Select **Personal access tokens**.
3. Click **+ New Token**.
4. Configure the token fields:
   * **Name**: `VSCode-Marketplace-Publisher`
   * **Organization**: Select **All accessible organizations** from the dropdown.
   * **Expiration**: Select 30, 60, or 90 days.
   * **Scopes**: Click **Show all scopes** at the bottom of the dialog.
   * Scroll down to **Marketplace**.
   * Check **Acquire** and **Manage** (or **Manage**).
5. Click **Create**.
6. **Copy and securely store the generated token immediately**. Azure DevOps will not display it again.

### Step 3: Create Publisher in Marketplace Portal

1. Open the [Visual Studio Marketplace Management Portal](https://marketplace.visualstudio.com/manage).
2. Click **Create publisher**.
3. Set the **ID** to: `nirbhay-hiwse` (must exactly match the `publisher` field in `package.json`).
4. Enter your Display Name (`Nirbhay Hiwse`) and contact email.
5. Save changes.

### Step 4: Publish via Web Portal (Easiest & Recommended)

You can upload the pre-packaged `.vsix` file directly through the browser without needing CLI credentials:

1. Open [Marketplace Management Portal](https://marketplace.visualstudio.com/manage).
2. Click on your publisher name (`nirbhay-hiwse`).
3. Click the **+ New extension** button (top right) and select **Visual Studio Code**.
4. Drag and drop `antigravity-usage-intelligence-1.0.7.vsix` (located in this project root) into the upload box.
5. Click **Upload**.
6. The marketplace will verify the extension package (status will show *Verifying*, typically completes within 2–5 minutes). Once verified, your extension is live on the Visual Studio Marketplace!

---

## 4. Open VSX Registry (Eclipse Foundation)

Open VSX supplies extensions to open-source editors including VSCodium, Cursor, Windsurf, Gitpod, Eclipse Theia, and AWS Cloud9.

### Step 1: Create Account & Sign In

1. Open [Open VSX Registry](https://open-vsx.org/).
2. Click **Log In** in the top-right corner.
3. Authenticate using your GitHub account (`Nir-Bhay`).

### Step 2: Create & Claim Namespace

Extensions on Open VSX are namespaced under your publisher handle (`nirbhay-hiwse`).

1. Open your user menu (top-right) -> **Settings**.
2. Navigate to **Namespaces** tab.
3. If `nirbhay-hiwse` does not exist:
   * Click **Create Namespace**.
   * Enter `nirbhay-hiwse` and submit.
   * Note: If the namespace is protected or requires verification, submit a membership request through the [open-vsx.org namespace repository](https://github.com/eclipse/openvsx).

### Step 3: Generate Access Token

1. Under **Settings**, navigate to **Access Tokens** (`https://open-vsx.org/user-settings/tokens`).
2. Click **Generate Token**.
3. Name: `OVSX-Publisher-Token`.
4. Copy the generated token string.

### Step 4: Verify Token Locally

Run the validation command using the `ovsx` CLI:

```bash
npx --yes ovsx verify-pat nirbhay-hiwse -p <YOUR_OPEN_VSX_TOKEN>
```

A success message confirms your token has publishing authority for `nirbhay-hiwse`.

---

## 5. Local Validation & Packaging

Always validate package contents and execute syntax tests before pushing a release.

### Run Prepublish Compilation Test

```bash
npm run vscode:prepublish
```

This verifies:
- `extension.js` passes Node.js syntax checks (`node -c`).
- `collector.py` passes Python bytecode compilation (`python -m py_compile`).

### Inspect Files Targeted for Packaging

```bash
npx --yes @vscode/vsce ls
```

Verify that only production runtime files are listed:
```text
README.md
package.json
LICENSE.txt
LICENSE
extension.js
collector.py
CHANGELOG.md
assets/icon.svg
assets/icon.png
src/ui/dashboard.html
```

Confirm that no test specs, `.planning` files, `plan*.md`, `.vsix`, or `__pycache__` artifacts are listed.

### Build VSIX Package

```bash
npm run package
```
*(or run `npx --yes @vscode/vsce package --no-git-tag-version`)*

This generates `antigravity-usage-intelligence-1.0.7.vsix` (~273 KB).

### Test Install VSIX in VS Code / Antigravity

```bash
# In Antigravity or VS Code:
code --install-extension antigravity-usage-intelligence-1.0.7.vsix
```

Open your editor, verify that:
1. The status bar item shows today's token consumption.
2. The Activity Bar has the `Agent Stats` container with working webview.
3. Command `Antigravity Stats: Open Full Screen Dashboard` opens the full dashboard.

---

## 6. Publishing CLI Commands

### Publish to Visual Studio Marketplace

#### Option A: One-time publish using CLI token argument
```bash
npx --yes @vscode/vsce publish -p <YOUR_AZURE_DEVOPS_PAT>
```

#### Option B: Using the npm script hook
```bash
npm run publish:marketplace -- -p <YOUR_AZURE_DEVOPS_PAT>
```

#### Option C: Storing credentials in OS keychain
```bash
# Saves publisher credentials locally
npx --yes @vscode/vsce login nirbhay-hiwse

# Subsequent publishes do not require entering the token:
npm run publish:marketplace
```

---

### Publish to Open VSX Registry

#### Option A: Publishing the pre-built `.vsix`
```bash
npx --yes ovsx publish antigravity-usage-intelligence-1.0.7.vsix -p <YOUR_OPEN_VSX_TOKEN>
```

#### Option B: Packaging and publishing in one command
```bash
npx --yes ovsx publish -p <YOUR_OPEN_VSX_TOKEN>
```

#### Option C: Using the npm script hook
```bash
npm run publish:openvsx -- -p <YOUR_OPEN_VSX_TOKEN>
```

---

### Publishing a Single .vsix to Both Registries

To guarantee exact binary parity between VS Code Marketplace and Open VSX:

```bash
# 1. Package once
npx --yes @vscode/vsce package --no-git-tag-version

# 2. Publish to Microsoft Marketplace
npx --yes @vscode/vsce publish --packagePath antigravity-usage-intelligence-1.0.7.vsix -p <AZURE_DEVOPS_PAT>

# 3. Publish identical package to Open VSX
npx --yes ovsx publish antigravity-usage-intelligence-1.0.7.vsix -p <OPEN_VSX_TOKEN>
```

---

## 7. Version Bumping & Release Lifecycle

Follow standard Semantic Versioning (`MAJOR.MINOR.PATCH`):

| Release Type | Command | When to Use | Example |
| :--- | :--- | :--- | :--- |
| **Patch** | `npm version patch` | Bug fixes, visual polish, small optimizations | `1.0.0` -> `1.0.1` |
| **Minor** | `npm version minor` | New features, additional filters, new charts | `1.0.0` -> `1.1.0` |
| **Major** | `npm version major` | Breaking config changes, architecture rewrites | `1.0.0` -> `2.0.0` |

### Recommended Release Workflow

1. **Update `CHANGELOG.md`**:
   Document changes under the new version header with today's date.

2. **Bump Version**:
   ```bash
   npm version minor -m "chore(release): bump version to %s"
   ```
   This automatically updates `version` in `package.json` and creates a Git tag.

3. **Push Tag to GitHub**:
   ```bash
   git push origin main --follow-tags
   ```

4. **Package & Publish**:
   ```bash
   # Package
   npm run package

   # Publish to VS Marketplace
   npm run publish:marketplace -- -p <AZURE_DEVOPS_PAT>

   # Publish to Open VSX
   npm run publish:openvsx -- -p <OPEN_VSX_TOKEN>
   ```

---

## 8. Troubleshooting & Common Pitfalls

### `Error: Personal Access Token verification failed. 401 Unauthorized`
* **Cause**: The Azure DevOps PAT was created scoped to a single organization instead of "All accessible organizations".
* **Solution**: Re-create the token in Azure DevOps and ensure **Organization** is set to **"All accessible organizations"** with scope **Marketplace: Manage**.

### `Error: Publisher 'nirbhay-hiwse' not found`
* **Cause**: The publisher ID has not been created on the portal yet.
* **Solution**: Visit `https://marketplace.visualstudio.com/manage` and create publisher `nirbhay-hiwse`.

### `Error: 403 Forbidden` on Open VSX
* **Cause**: Token does not have ownership or publishing permissions on namespace `nirbhay-hiwse`.
* **Solution**: Visit `https://open-vsx.org/user-settings/namespaces` and ensure `nirbhay-hiwse` is claimed under your user profile.

### `Extension icon must be 128x128 pixels`
* **Verification**: `assets/icon.png` is already verified at exactly 128x128px PNG. Do not replace it with arbitrary dimensions.

### `A .vscodeignore file exists, but...`
* All files in `.vscodeignore` are tested. Critical assets are explicitly un-ignored (`!extension.js`, `!collector.py`, `!package.json`, `!README.md`, `!CHANGELOG.md`, `!LICENSE.txt`, `!assets/icon.png`, `!assets/icon.svg`, `!src/ui/dashboard.html`).
