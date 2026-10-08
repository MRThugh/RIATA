# R.I.A.T.A — Responsive Intent Automation & Task Assistant

**Current Version:** 0.2.0  
**Author & Maintainer:** Ali Kamrani ([MRThugh](https://github.com/MRThugh))  
**Repository:** [https://github.com/MRThugh/RIATA](https://github.com/MRThugh/RIATA)  
**Platform:** Ubuntu Linux  
**License:** MIT  

---

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-brightgreen.svg)
![GUI](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-41CD52.svg)
![Platform](https://img.shields.io/badge/platform-Ubuntu%20Linux-E95420.svg)
![Tests](https://img.shields.io/badge/tests-127%20passed-green.svg)
![Release](https://img.shields.io/badge/release-v0.2.0%20(Context--Aware)-orange.svg)

---

## 💡 What is R.I.A.T.A?

**R.I.A.T.A** (Responsive Intent Automation & Task Assistant) is a deterministic, local-first, privacy-respecting Linux desktop assistant for Ubuntu.

It provides a unified conversational interface to launch and terminate applications, navigate local directories, manage sandbox files and folders, open validated web URLs, play local music, and inspect system telemetry — natively in both **Persian (فارسی)** and **English**.

### 🔒 100% Offline, Deterministic & Local-First
R.I.A.T.A does **not** rely on cloud APIs, external Large Language Models (LLMs), or unpredictable autonomous computer-control agents. It operates deterministically using a decoupled, rule-based **Intent Engine**, **Context Engine**, and **Command Planner** that separates linguistic understanding and conversational state from operating system execution:

* **Persian (RTL):** `کروم رو باز کن و فایل منیجر رو باز کن`
* **English (LTR):** `Open Chrome and open File Manager`

Both multi-step commands are parsed into deterministic dependency-tracked steps without arbitrary code generation:
```python
CommandPlan(
    plan_id="plan-179140...",
    steps=[
        CommandStep(step_id=1, intent=Intent("OPEN_APPLICATION", entities={"application": "chrome"})),
        CommandStep(step_id=2, intent=Intent("OPEN_FILE_MANAGER"), dependencies=[0]),
    ],
    status="PENDING"
)
```

---

## 🏛️ Architecture

R.I.A.T.A v0.2.0 is built on a clean, unidirectional, and strictly gated processing pipeline:

```text
User Input (Persian / English)
    │
    ▼
Language Detection & Normalization (Registry & Declarative Packs)
    │
    ▼
Intent Engine (Grammar, Matcher, Entity Extractor)
    │
    ▼
Context Engine & Entity Resolver (Pronoun & Locative Disambiguation)
    │
    ▼
Command Planner (Multi-Step DAG & Dependency Mapping)
    │
    ▼
Policy Engine (Authoritative Risk Evaluation: ALLOW, CONFIRM, DENY)
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
2. **Deterministic Contextual Memory:** Conversational state (active app, active directory, active file, open applications) is maintained in isolated sessions without fuzzy heuristics.
3. **Command Planning with Failure Isolation:** Sequential commands are planned with explicit step dependencies. If step `n` fails or is blocked by security policy, subsequent steps `n+1..` are safely skipped.
4. **Authoritative Policy Gate:** Context and multi-step plans can never bypass the **Policy Engine** (`ALLOW`, `CONFIRM`, `DENY`).
5. **Zero-Shell Execution:** Arbitrary user strings are never evaluated via `shell=True` or `bash -c`. Binaries are validated through the Application Registry and invoked via `subprocess.Popen` with explicit arguments.
6. **Non-Replayable Confirmations:** High-risk actions require single-use, session-bound confirmation tokens (`PendingConfirmation`) that cannot be replayed.

---

## 🧩 Desktop Capabilities (v0.2.0 Status)

Desktop actions are registered as modular Capabilities in `app/capabilities/`:

| Capability ID | Name | Intents | Status in v0.2.0 | Description |
|---|---|---|---|---|
| `applications` | Applications Manager | `OPEN_APPLICATION`, `CLOSE_APPLICATION`, `OPEN_URL` | **Implemented** | Launches allowlisted apps, terminates apps safely (`pkill`), and opens sanitized HTTP/HTTPS URLs. |
| `filesystem` | Filesystem Sandbox | `OPEN_FOLDER`, `OPEN_FILE`, `CREATE_FILE`, `DELETE_FILE`, `CREATE_FOLDER`, `DELETE_FOLDER` | **Implemented** | Safe file and folder operations strictly contained within `~` and `/tmp`. Traversal outside sandbox is blocked. |
| `media` | Audio & Media | `PLAY_MUSIC` | **Implemented** | Scans `~/Music` for `.mp3`, `.flac`, `.wav`, `.ogg`. Provides candidate disambiguation. |
| `system` | System Utilities | `OPEN_TERMINAL`, `OPEN_SETTINGS`, `OPEN_FILE_MANAGER`, `SHOW_SYSTEM_INFO`, `TAKE_SCREENSHOT`, `EXIT_APPLICATION`, `RESET_CONTEXT` | **Implemented** | Control center, terminal, screenshot capture, hardware info, and context memory wiping. |
| `processes` | Process Management | `LIST_PROCESSES`, `KILL_PROCESS` | **Stub / Foundation** | Architectural contract foundation; safely returns `STATUS_NOT_SUPPORTED`. |
| `windows` | Window Management | `MINIMIZE_WINDOW`, `MAXIMIZE_WINDOW` | **Stub / Foundation** | Architectural contract foundation; safely returns `STATUS_NOT_SUPPORTED`. |
| `notifications`| Desktop Notifications | `SEND_NOTIFICATION` | **Stub / Foundation** | Architectural contract foundation; safely returns `STATUS_NOT_SUPPORTED`. |
| `clipboard` | Clipboard Manager | `GET_CLIPBOARD`, `SET_CLIPBOARD` | **Stub / Foundation** | Architectural contract foundation; safely returns `STATUS_NOT_SUPPORTED`. |

---

## 🧠 Context-Aware Interaction & Pronoun Resolution

R.I.A.T.A v0.2.0 introduces multi-turn entity and reference resolution:

### 1. Pronoun and Deictic References
* **Persian:**
  - `فایرفاکس رو باز کن` (Turn 1: Firefox opens, `active_app="firefox"`)
  - `ببندش` (Turn 2: Suffix pronoun `-ش` resolves to Firefox -> `CLOSE_APPLICATION: firefox`)
  - `پوشه Downloads رو باز کن` (Turn 3: `active_directory="~/Downloads"`)
  - `داخلش فایل notes.txt رو بساز` (Turn 4: `CREATE_FILE` in `~/Downloads/notes.txt`)
* **English:**
  - `Open Firefox` -> `Close it`
  - `Open Downloads` -> `In it create notes.txt`

### 2. Multi-Candidate Ambiguity Detection
If multiple candidate applications are currently open:
* User: `کروم و فایرفاکس باز هستند` (Declares open apps)
* User: `ببندش`
* R.I.A.T.A: `چند برنامه باز هستند (Chrome, Firefox). لطفاً مشخص کنید کدام را ببندم؟` (Returns `STATUS_NEEDS_CLARIFICATION`)

### 3. Context Lifetime & Memory Reset
* Context can be deterministically wiped at any turn:
  - User: `فراموش کن` or `Reset context`
  - R.I.A.T.A: `زمینه گفت‌وگو پاکسازی شد.` (Active entities and session tokens cleared)

---

## 🛡️ Security Model & Policy Engine

R.I.A.T.A uses an authoritative three-tier permission model evaluated **before** execution:

```text
    Intent / Command Step
           │
           ├── Is dangerous command? (rm -rf, sudo, mkfs, dd, forkbomb) ────► DENY (Blocked)
           │
           ├── Is high risk? (DELETE_FILE, DELETE_FOLDER, SHUTDOWN) ───────► CONFIRM (Requires Confirmation Token)
           │
           └── Is standard desktop operation? ─────────────────────────────► ALLOW (Permitted)
```

### 1. Filesystem Containment Sandbox
* Target paths are strictly resolved via `Path.resolve()` and tested with `Path.relative_to(Path.home())`.
* Directory traversal (`../`), symlink escapes to `/etc`, and sibling prefix bypasses (`/home/user2` vs `/home/user`) are systematically rejected with `STATUS_PATH_NOT_ALLOWED`.
* Protected user subdirectories (`.ssh`, `.gnupg`, `.pki`, `.aws`, `.docker`, `.kube`, `.password-store`) are rejected from generic file/folder operations.

### 2. Subprocess Safety
* **Zero `shell=True`:** 100% verified across the entire codebase.
* Executables are strictly matched against the allowlisted Application Registry.
* Arguments are passed as sanitized arrays directly to `subprocess.Popen` / `subprocess.run`.

### 3. Non-Replayable Confirmation Tokens
* When a high-risk intent (e.g. `DELETE_FILE`) is requested, the system creates a unique, expiring `PendingConfirmation` token.
* Confirmation with `بله` / `yes` consumes and invalidates the token. Repeating `بله` on subsequent turns will **not** replay the dangerous action.
* Cancellation with `خیر` / `no` immediately destroys the token.

---

## 🖥️ User Interfaces

### 1. PySide6 Desktop GUI (Primary Ubuntu Desktop App)
* **Stack:** Qt 6 / PySide6.
* **Features:**
  - Asynchronous execution worker thread.
  - Live RTL / LTR layout switching (Persian right-to-left, English left-to-right).
  - Dark and Light desktop themes.
  - Interactive multi-turn chat timeline.

To launch:
```bash
python main.py
```

### 2. React Web Companion (Development, Simulation & Test Suite)
* **Stack:** React 19, TypeScript, Tailwind CSS, Vite.
* **Features:**
  - Live Session Context Bar (inspect `active_app`, `active_directory`, `active_file`, open apps count).
  - Multi-Step Plan visualizer with step statuses and dependency tracking.
  - Interactive one-click Confirmation Action Bar (`بله` / `خیر`).
  - Interactive Disambiguation selection buttons.
  - In-browser live execution of the full automated test suite (**128 tests** across 23 test modules).

To launch:
```bash
npm run dev
```

---

## 🧪 Testing

The test suite contains **128 automated unit and regression tests** (127 passed, 1 skipped) across 23 test modules:

```bash
# Run pytest directly
pytest -v

# Or via npm
npm test
```

Test coverage includes:
* `test_v020_context.py`: SessionContext isolation, turn history, and confirmation token lifecycles.
* `test_v020_entity_resolution.py`: Pronoun resolution, locative container particles, and ambiguity detection in Persian and English.
* `test_v020_planner.py`: Multi-step command splitting, plan generation, step dependencies, and failure isolation.
* `test_v020_policy.py`: High-risk confirmation gating, non-replayability, and policy denials.
* `test_v020_capabilities.py`: Application closing, URL opening, file and folder creation and deletion.
* `test_v020_language_context.py`: Full multi-turn contextual flows in Persian and English.
* `test_v020_security_regressions.py`: Zero `shell=True` verification, path traversal rejection, credential protection, and injection prevention.

---

## 🚀 Installation & Getting Started

### Prerequisites:
* **Ubuntu Linux 20.04+** (Ubuntu 22.04 LTS or 24.04 LTS recommended)
* **Python 3.10+** (Python 3.10, 3.11, 3.12, 3.13)
* **Node.js 20+** (optional, for web development companion)

### 1. Clone & Setup
```bash
git clone https://github.com/MRThugh/RIATA.git
cd RIATA

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### 2. Run Modes
```bash
# Launch Desktop GUI
python main.py

# Launch CLI Interactive Mode
python main.py --cli

# Launch Dry-Run Simulation Mode
python main.py --dry-run

# Launch Web Companion
npm run dev
```

---

## 📦 Releases

RIATA features a smart, automated GitHub Actions release pipeline (`.github/workflows/release.yml`) that builds native Ubuntu Debian packages (`.deb`) and publishes GitHub Releases.

The release workflow **automatically determines the version directly from the source code** (canonical `pyproject.toml`, synchronized with `app/core/constants.py`, `package.json`, and `metadata.json`). The version is never hardcoded or typed manually into the workflow.

### Automated Release Procedure:
1. **Update the project version** across the source tree (e.g. `0.2.0` → `0.3.0`).
2. **Commit and push** the changes to the default branch (`main`).
3. Open **GitHub Actions** in the repository.
4. Select the **RIATA Release** workflow.
5. Click **Run workflow** (confirmation phrase: `release`).
6. The workflow automatically **validates the version** and ensures all sources match.
7. Runs the complete **Python test suite** (`pytest`) and **frontend validation** (`npm run lint`, `npm run build`).
8. Builds the native Ubuntu package (`RIATA_<version>_amd64.deb`).
9. Validates package architecture, control metadata, and runs an **installation smoke test**.
10. Creates the Git tag (`v<version>`).
11. Creates the **GitHub Release** (`RIATA v<version>`).
12. Uploads the `.deb` package and `SHA256SUMS` checksums.

---

## 👨‍💻 Author & License

Created and maintained by **Ali Kamrani ([MRThugh](https://github.com/MRThugh))**.  
Released under the **MIT License**.
