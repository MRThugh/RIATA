# Security Policy — R.I.A.T.A

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.1   | :white_check_mark: |
| < 0.1.1 | :x:                |

---

## Security Model & Threat Boundaries

R.I.A.T.A is designed as a **strictly bounded desktop assistant**, not an unrestricted root shell or remote command server.

### Core Security Guarantees:
1. **Zero Shell Evaluation**: User strings are **never** evaluated by `sh`, `bash`, `os.system()`, or `subprocess.Popen(..., shell=True)`. All executions use direct binary paths with argument lists.
2. **Filesystem Sandbox Containment**: All file and folder operations are constrained to the current user's home directory (`Path.home()`) or `/tmp`. Symlink escapes to root system paths (`/etc`, `/var`, `/usr`) and path traversals (`../`) are systematically rejected.
3. **Protected Directory Shield**: Access to sensitive credential directories (`~/.ssh`, `~/.gnupg`, `~/.pki`, `~/.aws`, `~/.docker`, `~/.kube`, `~/.password-store`) is blocked from generic intent actions.
4. **Policy Engine (ALLOW, CONFIRM, DENY)**: High-risk operations (`SHUTDOWN`, `RESTART`, `DELETE_FILE`) require explicit user confirmation. Destructive commands (`rm`, `sudo`, `mkfs`, fork bombs) are unconditionally blocked.
5. **Local Web Companion Boundary**:
   - The web development companion is strictly intended for local developer use.
   - Enforces `Sec-Fetch-Site` restrictions, Host/Origin validation, and requires the `X-RIATA-Client: web-v0.1.1` anti-CSRF token on all API routes.
   - Subprocess executions have a strict 15-second timeout and 16KB payload limit.
6. **Language Pack Trust Model**: Language pack `rules.py` files execute arbitrary Python. Users must only install language packs from trusted sources.

---

## Reporting a Vulnerability

If you discover a security vulnerability in R.I.A.T.A, please report it responsibly:

* **Email:** [kamrani.exe@gmail.com](mailto:kamrani.exe@gmail.com)
* **Maintainer:** Ali Kamrani ([MRThugh](https://github.com/MRThugh))

Please provide:
1. A description of the vulnerability and attack vector.
2. Steps to reproduce or proof-of-concept payload.
3. Potential impact.

We take security issues seriously and will respond promptly to validate and coordinate fixes before public disclosure.
