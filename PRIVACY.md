# Privacy Policy — Antigravity Usage Intelligence

**Last updated:** 2026-09-06
**Extension:** `nirbhay-hiwse.antigravity-usage-intelligence` (community-built, unofficial — not affiliated with or endorsed by Google)

## Short version

Your data never leaves your machine. This extension makes **zero internet connections**.
The only network activity is a local connection to Antigravity on your own computer
(`127.0.0.1` loopback). No accounts, no telemetry, no analytics, no cloud.

## What the extension reads (on your machine only)

| Data | Source | Purpose |
| :--- | :--- | :--- |
| Token counts per agent step (input, cache-read, output, thinking) | `~/.gemini/antigravity*/conversations/*.db` (SQLite, opened read-only: `?mode=ro`, `PRAGMA query_only = ON`) | Token analytics dashboard |
| Tool names + success/failure counts | `~/.gemini/antigravity*/brain/<id>/.system_generated/logs/transcript.jsonl` | Tool reliability stats |
| Workspace folder names | Trajectory metadata inside the same local DBs | Per-project breakdown |
| Quota fractions + reset times | Local Antigravity language server via `127.0.0.1` loopback (Connect-RPC `GetUserStatus`, CSRF-protected) | Live quota card + threshold alerts |

## What the extension never does

- **No internet access.** No `fetch`, no telemetry SDK, no update checks, no error reporting
  leave the machine. Verify with DevTools Network panel or a firewall: everything works offline.
- **No prompt or code content.** Conversation text, source code, and file contents are never
  read, stored, or transmitted — only counts and metadata.
- **No credentials.** API keys, OAuth tokens, and passwords are never accessed. The local
  CSRF token is used solely to authenticate the loopback quota query and is never stored.
- **No account or identifier.** No `machineId` collection, no fingerprinting, no user tracking.

## Name and email

When the local language server is reachable, it reports the signed-in profile name/email
with the quota response. These values live **only in memory**, are shown only in your local
dashboard header, and are never written to disk or sent anywhere. If the server is
unreachable, the extension works fully without them.

## Local storage and retention

- Derived statistics cache: `~/.gemini/antigravity/antigravity_stats_cache.json`
  (rebuilt automatically; delete the file or run **Rebuild Full History Cache** to regenerate).
- VS Code settings you configure (`antigravity-stats.*`) stay in your local VS Code profile.
- Uninstalling the extension removes its code; delete the cache file above to remove all traces.

## Changes to this policy

Material changes will be described in `CHANGELOG.md` before release. Questions:
open an issue at <https://github.com/Nir-Bhay/antigravity-usage-intelligence/issues>.
