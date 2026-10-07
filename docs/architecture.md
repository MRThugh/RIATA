# R.I.A.T.A — Architecture Overview
**Responsive Intent Automation & Task Assistant (v0.1.1)**  
**Author:** Ali Kamrani (MRThugh)  
**License:** MIT  
**Platform:** Ubuntu Linux  

---

## 1. Architectural Philosophy

R.I.A.T.A v0.1.1 is built upon a strict **Unidirectional Processing Pipeline** with clear separation of concerns:

```text
User Input (Natural Language: Persian or English)
       │
       ▼
Language System (Registry & Language Packs)
       │
       ▼
Intent Engine (Parser, Matcher, Entity Extractor)
       │
       ▼
Interaction System (Context, Disambiguation, Confirmation)
       │
       ▼
Policy Engine (Risk Evaluation: ALLOW, CONFIRM, DENY)
       │
       ▼
Capability Registry (Applications, Filesystem, Media, System)
       │
       ▼
Desktop Capability Provider
       │
       ▼
Safe Executor (Direct process invocation — zero shell=True)
       │
       ▼
Operating System (Ubuntu Linux Desktop)
```

### Core Invariants:
1. **Language Independence:** An Intent like `OPEN_APPLICATION` with entity `{"application": "firefox"}` is identical whether entered in Persian (`فایرفاکس رو باز کن`) or English (`Open Firefox`).
2. **Safe Execution:** Arbitrary user strings are **never** evaluated by a shell (`os.system` and `shell=True` are strictly banned). Execution occurs only via validated executables identified through the Application Registry or standard desktop utilities.
3. **Policy-First Security:** High-risk actions (`SHUTDOWN`, `DELETE_FILE`, `RESTART`) require explicit user confirmation (`CONFIRM`). Malicious commands (`rm`, `sudo`, `mkfs`, fork bombs) are unconditionally rejected (`DENY`).
4. **Offline & Deterministic:** Version 0.1.1 operates deterministically without cloud NLP services or machine learning models.

---

## 2. Directory Structure

```text
RIATA/
├── app/
│   ├── __init__.py
│   ├── core/                  # Configuration, constants, structured logging
│   │   ├── config.py          # Configuration and environment loaders
│   │   ├── constants.py       # Intent names, thresholds, banned commands
│   │   └── logger.py          # Structured logging with memory ring-buffer
│   ├── engine/                # Rule-based Intent Engine
│   │   ├── intent.py          # Language-independent Intent data model
│   │   ├── matcher.py         # Pattern matching & confidence scoring
│   │   ├── normalizer.py      # Multi-language normalization engine
│   │   ├── entity_extractor.py# Extracts apps, folders, song names
│   │   ├── router.py          # Orchestrates parsing, policy, capability dispatch
│   │   └── task.py            # Async execution and task tracking
│   ├── languages/             # Extensible language pack registry
│   │   ├── registry.py        # Central pack discovery and registry
│   │   ├── rules.py           # Base language rule interfaces
│   │   ├── detector.py        # Unicode script range detector
│   │   └── loader.py          # Backward-compatibility loader facade
│   ├── interaction/           # Conversational state & responses
│   │   ├── context.py         # Short-lived turn memory & disambiguation
│   │   └── responses.py       # Localized natural feedback generator
│   ├── policy/                # Risk-aware desktop security engine
│   │   ├── engine.py          # Evaluates ALLOW, CONFIRM, and DENY
│   │   └── decision.py        # Policy evaluation decision models
│   ├── capabilities/          # Modular desktop capabilities
│   │   ├── base.py            # Base capability contract
│   │   ├── registry.py        # Central capability dispatcher
│   │   ├── applications.py    # Desktop app launcher
│   │   ├── filesystem.py      # Folder and file navigation
│   │   ├── media.py           # Local audio scanner and playback
│   │   ├── system.py          # Terminal, settings, sysinfo, screenshot
│   │   ├── processes.py       # Process capability foundation (stub)
│   │   ├── windows.py         # Window management foundation (stub)
│   │   ├── notifications.py   # Desktop notifications foundation (stub)
│   │   └── clipboard.py       # Clipboard foundation (stub)
│   ├── executor/              # Safe Linux action executors
│   │   ├── application.py     # Subprocess launcher for applications
│   │   ├── files.py           # Sandboxed folder and file opener
│   │   ├── music.py           # ~/Music audio player
│   │   ├── system.py          # Desktop utilities executor
│   │   └── result.py          # ExecutionResult data model
│   ├── registry/              # Dynamic application discovery
│   │   └── applications.py    # Desktop entries and binary scanner
│   └── ui/                    # Native PySide6 Qt 6 desktop interface
│       ├── main_window.py     # Asynchronous desktop main window
│       ├── chat/              # Chat timeline, message items, typing indicators
│       ├── input/             # Message input composer
│       ├── shell/             # Header bar and collapsible sidebar
│       └── themes/            # Dark and light theme manager
├── languages/                 # Modular language packs
│   ├── fa/                    # Persian language pack (manifest, intents, rules)
│   └── en/                    # English language pack
├── tests/                     # Automated test suite (73 tests)
├── docs/                      # Architectural and technical documentation
├── main.py                    # Main desktop application entrypoint
├── requirements.txt           # Runtime dependencies
├── requirements-dev.txt       # Development & test dependencies
└── pyproject.toml             # Modern package configuration
```

---

## 3. Asynchronous Concurrency

To ensure the desktop UI remains fluid and responsive:
* The `MainWindow` employs `QThread` and `QObject` worker patterns (`ExecutionWorker`).
* Command processing and intent execution run on background threads.
* UI slots handle completion events on the main thread, guaranteeing that background tasks never freeze the interface.
* In the event of an unhandled exception, `ExecutionWorker` safely emits a fallback error result, ensuring the user input composer is never permanently locked.

---

## 4. Policy Engine Lifecycle

Every parsed intent is audited by `PolicyEngine.evaluate(intent)`:
* **ALLOW:** Low-risk standard operations (opening browser, navigating to Downloads, playing music) proceed directly to capability execution.
* **CONFIRM:** High-risk system operations (shutdown, reboot, file deletion) establish an interaction state (`AWAITING_CONFIRMATION`). The system prompts the user and executes only upon positive confirmation.
* **DENY:** Destructive or privileged commands (`rm`, `sudo`, `mkfs`) are intercepted before execution, returning `STATUS_PERMISSION_DENIED` with `executed=False`.
