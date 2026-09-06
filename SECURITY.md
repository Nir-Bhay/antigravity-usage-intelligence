# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

The security of Antigravity Usage Intelligence and our users' privacy is our top priority.

Because this extension operates entirely offline by parsing local SQLite ledgers on your machine:
- It maintains **zero external telemetry servers**.
- It opens databases in **read-only WAL mode** (`?mode=ro&immutable=1`).
- It connects strictly to the local loopback interface (`127.0.0.1`) when querying the local Antigravity Language Server with CSRF token protection.

If you believe you have found a security vulnerability in Antigravity Usage Intelligence, please do not open a public issue. Instead, report it privately:

1. Use GitHub's **Private Vulnerability Reporting** on the repository: [Report a vulnerability](https://github.com/Nir-Bhay/antigravity-usage-intelligence/security/advisories/new).
2. Or contact the maintainer directly via GitHub [@Nir-Bhay](https://github.com/Nir-Bhay).

You can expect an acknowledgment within 48 hours and a coordinated fix timeline.
