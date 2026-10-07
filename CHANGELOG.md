# Changelog

All notable changes to R.I.A.T.A will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.1] - 2026-10-07

### Summary
Release v0.1.1 is a stabilization, security hardening, and architecture consolidation release. It solidifies the foundation of R.I.A.T.A without introducing experimental AI agents or scope creep.

### Added
- **Policy Engine**: Integrated a three-tier permission model (`ALLOW`, `CONFIRM`, `DENY`) evaluated prior to any desktop execution.
- **Interaction Context**: Added short-lived turn memory supporting numbered candidate disambiguation, confirmation prompts, and explicit cancellation.
- **Capability Registry**: Established a modular desktop capability dispatch system (`app/capabilities/`) with clean contracts for applications, filesystem, media, and system utilities.
- **Language Pack Extensibility**: Added dynamic registration for new languages at runtime through standardized declarative manifests (`manifest.json`, `intents.json`, `normalization.json`, `entities.json`, `responses.json`, `conversational.json`).
- **Development & Packaging Configs**: Added `pyproject.toml` and separated `requirements.txt` (runtime) from `requirements-dev.txt` (testing/dev).
- **GitHub Actions CI**: Added multi-version Python CI matrix (`3.10`, `3.11`, `3.12`, `3.13`) covering compilation, imports, unit tests, and security regression checks.

### Changed
- **Version Unification**: Unified versioning to `0.1.1` across all modules, constants, manifests, metadata, documentation, and user interfaces with a single source of truth in `app.core.constants`.
- **Router Workflow**: Updated `IntentRouter` to coordinate the full pipeline: Input → Language → Intent → Interaction → Policy → Capability → Executor.
- **Async Execution Worker**: Hardened `ExecutionWorker` in PySide6 to safely emit fallback error results on unexpected exceptions, ensuring the user input composer never locks up.

### Security
- **Filesystem Sandbox Hardening**:
  - Replaced string prefix validation with strict `Path.resolve()` and `Path.relative_to(Path.home())` containment.
  - Eliminated directory traversal (`../`) and symlink escape vulnerabilities.
  - Blocked sibling directory prefix bypasses (`/home/user2` vs `/home/user`).
  - Added protections against accessing sensitive credential folders (`.ssh`, `.gnupg`, `.pki`, `.aws`, `.docker`, `.kube`, `.password-store`, `.netrc`).
- **Web API Bridge Hardening**:
  - Enforced `Sec-Fetch-Site` blocking to reject cross-site browser requests.
  - Required anti-CSRF authentication header token (`X-RIATA-Client: web-v0.1.1`) on all API endpoints.
  - Removed insecure origin fallbacks (`if (!originHeader) return true;`).
  - Added Host and Origin hostname matching against local loopback.
  - Added a 15-second subprocess execution timeout to prevent hanging or zombie processes.
- **Subprocess Safety**: Verified 100% zero usage of `shell=True` or arbitrary shell strings across all executor modules.
- **Language Pack Fault Isolation**: Isolated `rules.py` imports with `BaseException` handling so malformed third-party packs log warnings without crashing the core assistant.

### Fixed
- **Policy Confirmation Loop**: Fixed an issue where confirmed high-risk intents in `InteractionContext` re-triggered confirmation loops instead of executing upon positive affirmation.
- **Headless Test Discovery**: Added graceful environment checks in `test_v011_pyside6_ui.py` allowing headless CI runners without X11/EGL to execute tests without collection errors.
- **Boolean Configuration Parsing**: Retained safe parsing avoiding unsafe `bool("false")` pitfalls in `app/core/config.py`.

### Testing
- Expanded test suite to **73 automated tests** covering core NLP, security containment, policy evaluations, and UI lifecycles.
- Added regression tests for sensitive credential path blocking and policy confirmation transitions.

### Documentation
- Completely updated `README.md` to reflect the actual v0.1.1 architecture and status.
- Updated `docs/architecture.md`, `docs/intents.md`, and `docs/languages.md`.
- Documented the trusted-code model for language pack `rules.py`.
- Added `SECURITY.md`, `CONTRIBUTING.md`, and `CHANGELOG.md`.

---

## [0.1.0] - 2026-09-15

### Initial Release
- Deterministic, rule-based Intent Engine for Ubuntu Linux.
- Native Persian (RTL) and English (LTR) language support.
- PySide6 desktop GUI with dark theme.
- Dynamic Application Registry and `.desktop` scanner.
- Local audio scanner and playback in `~/Music`.
- Zero-shell execution and dry-run simulation mode.
