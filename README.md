# R.I.A.T.A — Responsive Intent Automation & Task Assistant

**Current Version:** 0.1.1  
**Author & Maintainer:** Ali Kamrani ([MRThugh](https://github.com/MRThugh))  
**Repository:** [https://github.com/MRThugh/RIATA](https://github.com/MRThugh/RIATA)  
**Platform:** Ubuntu Linux  
**License:** MIT  

---

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-brightgreen.svg)
![GUI](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-41CD52.svg)
![Platform](https://img.shields.io/badge/platform-Ubuntu%20Linux-E95420.svg)
![Tests](https://img.shields.io/badge/tests-73%20passed-green.svg)
![Release](https://img.shields.io/badge/release-v0.1.1%20(Stabilization)-orange.svg)

---

## 💡 What is R.I.A.T.A?

**R.I.A.T.A** (Responsive Intent Automation & Task Assistant) is a deterministic, privacy-first Linux desktop intent assistant for Ubuntu.

It provides a unified conversational interface to launch applications, navigate local folders, search and play music, manage desktop windows, and inspect system telemetry — natively in both **Persian (فارسی)** and **English**.

### 🔒 100% Offline & Deterministic
R.I.A.T.A does **not** rely on cloud APIs, Large Language Models (LLMs), or black-box autonomous agents. It operates deterministically using a decoupled, rule-based **Intent Engine** that separates language understanding from operating system execution:

* **Persian (RTL):** `فایرفاکس رو باز کن`
* **English (LTR):** `Open Firefox`

Both inputs normalize and extract into the identical language-independent structure:
```python
Intent(
    name="OPEN_APPLICATION",
    confidence=0.95,
    entities={"application": "firefox"},
    language="fa" # or "en"
)
```

---

## 🏛️ Architecture

R.I.A.T.A is built on a clean, unidirectional processing pipeline:

```text
User Input
    │
    ▼
Language Detection & Normalization (Registry & Language Packs)
    │
    ▼
Intent Engine (Parser, Matcher, Entity Extractor)
    │
    ▼
Interaction Context (Turn Memory, Disambiguation, Clarification)
    │
    ▼
Policy Engine (Risk Evaluation: ALLOW, CONFIRM, DENY)
    │
    ▼
Capability Registry (Modular Capability Routing)
    │
    ▼
Capability Provider (Applications, Filesystem, Media, System)
    │
    ▼
Executor (Direct binary invocation — zero shell=True)
    │
    ▼
Operating System (Ubuntu Linux Desktop)
```

### Architectural Principles:
1. **Language-Agnostic Core:** Core modules know nothing about Persian or English grammar. All linguistics are encapsulated in self-contained Language Packs.
2. **Deterministic Confidence:** Intent matching scores confidence through transparent pattern weights (`0.0` to `1.0`), never heuristic hallucination.
3. **Execution Safety:** All desktop operations pass through the **Policy Engine** (`ALLOW`, `CONFIRM`, `DENY`) before reaching executors.
4. **Zero-Shell Execution:** Arbitrary user strings are never evaluated via `shell=True` or `bash -c`. Binaries are validated through the Application Registry and invoked via `subprocess.Popen` with explicit arguments.

---

## 🧩 Desktop Capabilities (v0.1.1 Status)

Desktop actions are registered as modular Capabilities in `app/capabilities/`:

| Capability ID | Name | Intents | Status in v0.1.1 | Description |
|---|---|---|---|---|
| `applications` | Applications Launcher | `OPEN_APPLICATION` | **Implemented** | Resolves applications via desktop entries and system paths; launches without shell. |
| `filesystem` | Filesystem & Folders | `OPEN_FOLDER`, `OPEN_FILE` | **Implemented** | Opens standard XDG folders and user files within sandbox. Traversal outside `~` is blocked. |
| `media` | Audio & Media | `PLAY_MUSIC` | **Implemented** | Scans `~/Music` for `.mp3`, `.flac`, `.wav`, `.ogg`. Provides candidate disambiguation. |
| `system` | System Utilities | `OPEN_TERMINAL`, `OPEN_SETTINGS`, `OPEN_FILE_MANAGER`, `SHOW_SYSTEM_INFO`, `TAKE_SCREENSHOT`, `EXIT_APPLICATION` | **Implemented** | One-shot control center, terminal, screenshot capture, and non-sensitive hardware info. |
| `processes` | Process Management | `LIST_PROCESSES`, `KILL_PROCESS` | **Stub / Planned** | Registered in capability registry foundation; returns `STATUS_NOT_SUPPORTED` in v0.1.1. |
| `windows` | Window Management | `MINIMIZE_WINDOW`, `MAXIMIZE_WINDOW` | **Stub / Planned** | Registered in capability registry foundation; returns `STATUS_NOT_SUPPORTED` in v0.1.1. |
| `notifications`| Desktop Notifications | `SEND_NOTIFICATION` | **Stub / Planned** | Registered in capability registry foundation; returns `STATUS_NOT_SUPPORTED` in v0.1.1. |
| `clipboard` | Clipboard Manager | `GET_CLIPBOARD`, `SET_CLIPBOARD` | **Stub / Planned** | Registered in capability registry foundation; returns `STATUS_NOT_SUPPORTED` in v0.1.1. |

> **Note on Stubs:** Capabilities marked *Stub / Planned* define the architectural contracts for upcoming releases. They safely report `STATUS_NOT_SUPPORTED` with `executed=False` and do not simulate false execution.

---

## 🌐 Language Packs

Language packs reside under `languages/<code >/` and are auto-discovered at boot:

```text
languages/
└── fa/
    ├── manifest.json        # Pack metadata, language code, script patterns
    ├── intents.json         # Regex grammar and intent matching patterns
    ├── normalization.json   # Character mappings, diacritics, stop particles
    ├── entities.json        # Standard XDG folders, ordinals (e.g. اول، دوم)
    ├── responses.json       # Localized natural feedback templates
    ├── conversational.json  # Affirmations, cancellations, vague phrase rules
    └── rules.py             # Optional language-specific rule hooks
```

### ⚠️ Language Pack Trust & Code Execution
`rules.py` is a Python module executed within the assistant's process context to evaluate language-specific edge cases.  
**Security Requirement:** Language packs containing Python code must be installed **only from trusted sources**. When importing third-party language packs, verify the contents of `rules.py`. If a pack has syntax errors or invalid imports, the loader safely quarantines the rule hook and falls back to JSON definitions without crashing.

---

## 🛡️ Security Model & Policy Engine

R.I.A.T.A uses a three-tier permission model evaluated **before** execution:

```text
    Intent Received
          │
          ├── Is dangerous command? (rm, sudo, mkfs, dd, forkbomb) ────► DENY (Blocked)
          │
          ├── Is high risk? (SHUTDOWN, RESTART, DELETE_FILE) ─────────► CONFIRM (Requires User Confirmation)
          │
          └── Is standard desktop operation? ────────────────────────► ALLOW (Permitted)
```

### 1. Filesystem Containment Sandbox
* Target paths are strictly resolved via `Path.resolve()` and tested with `Path.relative_to(Path.home())`.
* Directory traversal (`../`), symlink escape attacks to `/etc` or `/var`, and sibling prefix bypasses (`/home/user2` vs `/home/user`) are systematically rejected with `STATUS_PATH_NOT_ALLOWED`.
* Protected user subdirectories (`.ssh`, `.gnupg`, `.pki`, `.aws`, `.docker`, `.kube`, `.password-store`) are blocked from generic file/folder commands.

### 2. Command Execution Safety
* Zero usage of `shell=True` or shell string concatenation across all executors.
* Executables are validated against the allowlisted Application Registry.
* Destructive keywords (`rm`, `sudo`, `mkfs`, `dd`, `chmod`, `chown`, `:(){ :|:& };:`, etc.) are intercepted with `STATUS_PERMISSION_DENIED`.

### 3. Web Companion Security Boundary
* **Local Loopback Only:** The development server is bound strictly to `127.0.0.1:3000` (loopback only) and is not exposed to external networks or LAN interfaces.
* **Strict Browser Guardrails:** Enforces `Sec-Fetch-Site` restrictions, Host loopback validation, Origin verification, and a companion client identifier header (`X-RIATA-Client: web-v0.1.1`). Cross-site or non-loopback requests are rejected with HTTP 403 Forbidden.
* **Timeout & Payload Limits:** Subprocess execution has an enforced 15-second timeout and 16KB payload limit.

---

## 🖥️ User Interfaces

R.I.A.T.A provides two complementary interfaces:

### 1. PySide6 Desktop GUI (Primary Desktop App)
* **Target:** Linux desktop users (Ubuntu / GNOME / X11 / Wayland).
* **Stack:** Native Qt 6 / PySide6.
* **Features:**
  * Asynchronous QThread worker execution (UI thread never freezes).
  * Dynamic live RTL / LTR layout switching (Persian right-to-left, English left-to-right).
  * Smooth theme toggling (Dark and Light themes).
  * Multi-session conversational history threads.
  * Disambiguation selection cards and typing indicators.

To run:
```bash
python main.py
```

### 2. React / Web Companion (Development & Simulation Environment)
* **Target:** Developers, browser-based inspection, and test runner.
* **Stack:** React 19, TypeScript, Tailwind CSS, Vite.
* **Features:**
  * Live Intent Engine Inspector (inspect confidence scores, extracted entities, and safety flags).
  * One-click interactive `pytest` test runner in the browser.
  * Dry-Run toggle to simulate commands without invoking Linux system binaries.

To run:
```bash
npm run dev
```

---

## 🧪 Testing

The test suite contains **73 comprehensive unit and regression tests** covering:
* Core Intent matching, entity extraction, and normalization
* Filesystem sandbox containment, symlink escape rejection, and prefix bypass prevention
* Policy Engine risk levels (`ALLOW`, `CONFIRM`, `DENY`) and confirmation cycles
* Extensible language pack registry and third-language runtime loading
* PySide6 GUI components in offscreen mode
* Dry-run simulation and honest execution reporting

To run all automated tests:
```bash
# Run pytest directly
pytest -v

# Or via npm
npm test
```

---

## 🚀 Installation & Getting Started

### Prerequisites:
* **Ubuntu Linux 20.04+** (Ubuntu 22.04 LTS or 24.04 LTS recommended)
* **Python 3.10+** (Python 3.10, 3.11, 3.12, 3.13)
* **Node.js 22** (optional, for web development companion)

### 1. Clone the Repository
```bash
git clone https://github.com/MRThugh/RIATA.git
cd RIATA
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate

# Install runtime dependencies
pip install -r requirements.txt

# Or install all development & testing dependencies
pip install -r requirements-dev.txt
```

### 3. Launch R.I.A.T.A
```bash
# Launch Desktop GUI
python main.py

# Launch in Dry-Run mode (simulates actions safely)
python main.py --dry-run

# Launch in CLI terminal mode
python main.py --cli

# Launch with verbose debug logs
python main.py --debug
```

---

## 📊 Current Release Status: v0.1.1

> **Status:** **Foundation & Stabilization Release**

Version **0.1.1** is a stabilization and security hardening release focused on:
* Consolidating architecture across Intent Engine, Policy Engine, and Capability Registry.
* Eliminating security vulnerabilities in filesystem traversal and local API bridges.
* Establishing reproducible test environments and CI workflows.
* Unifying documentation, terminology, and version consistency.

No experimental autonomous agents or LLM bloat have been introduced. This release establishes a solid foundation for upcoming v0.2 desktop enhancements.

---

## 👨‍💻 Author & Open Source

Created and maintained by **Ali Kamrani ([MRThugh](https://github.com/MRThugh))**.  
Released under the **MIT License**. Contributions and feedback are welcome!
