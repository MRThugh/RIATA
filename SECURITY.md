# Security Policy — R.I.A.T.A

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.0   | :white_check_mark: |
| < 0.2.0 | :x:                |

---

## Security Model & Threat Boundaries

R.I.A.T.A is designed as a **strictly bounded desktop assistant**, not an unrestricted root shell or remote command server.

### Core Security Guarantees:
1. **Zero Shell Evaluation**: User strings are **never** evaluated by `sh`, `bash`, `os.system()`, or `subprocess.Popen(..., shell=True)`. All executions use direct binary paths with argument lists.
2. **Filesystem Sandbox Containment**: All file and folder operations are constrained to the current user's home directory (`Path.home()`) or `/tmp`. Symlink escapes to root system paths (`/etc`, `/var`, `/usr`) and path traversals (`../`) are systematically rejected.
3. **Protected Directory Shield**: Access to sensitive credential directories (`~/.ssh`, `~/.gnupg`, `~/.pki`, `~/.aws`, `~/.docker`, `~/.kube`, `~/.password-store`) is blocked from generic intent actions.
4. **Policy Engine (ALLOW, CONFIRM, DENY)**: High-risk operations (`SHUTDOWN`, `RESTART`, `DELETE_FILE`) require explicit user confirmation. Destructive commands (`rm`, `sudo`, `mkfs`, fork bombs) are unconditionally blocked.
5. **Local Web Companion Boundary**:
   - The Web Companion is strictly loopback-only (`127.0.0.1` and `::1`). It is never exposed to external network interfaces or remote addresses.
   - Socket connection validation unconditionally rejects all non-loopback remote IPs; private LAN addresses (`10.x.x.x`, `172.16-31.x.x`, `192.168.x.x`, `169.254.x.x`) are not considered local clients and are rejected with HTTP 403 Forbidden.
   - Enforces `Sec-Fetch-Site` restrictions, Host header loopback matching (supporting IPv4 and bracketed IPv6 `[::1]`), and Origin header validation.
   - The `X-RIATA-Client` header (`web-v0.2.0`) is a companion client identifier used to distinguish browser client requests; it is **not** an authentication credential.
   - Subprocess executions have a strict 15-second timeout and 16KB payload limit.
   - The `/api/run-tests` endpoint is strictly development-only. It is disabled by default (returning HTTP 403 Forbidden) and must be explicitly enabled via `RIATA_ENABLE_TEST_API=true`. Test executions are enforced with a 60-second process timeout and 256KB memory output bound.
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
