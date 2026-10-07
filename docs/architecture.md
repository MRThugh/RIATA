# R.I.A.T.A — Architecture Overview
**Responsive Intent Automation & Task Assistant (v0.2.0)**  
**Author:** Ali Kamrani (MRThugh)  
**License:** MIT  
**Platform:** Ubuntu Linux  

---

## 1. Architectural Philosophy

R.I.A.T.A v0.2.0 is an offline, local-first **Context-Aware Interaction Platform** built upon a strict **Unidirectional Processing Pipeline** with clear separation of concerns:

```text
User Input (Natural Language: Persian or English)
       │
       ▼
Language System (Registry & Declarative Language Packs)
       │
       ▼
Intent Engine (Parser, Matcher, Entity Extractor)
       │
       ▼
Context Engine & Entity Resolver (Pronouns, Active Entities, Ambiguity)
       │
       ▼
Command Planner (Multi-Step DAG & Dependency Mapping)
       │
       ▼
Policy Engine (Risk Evaluation: ALLOW, CONFIRM, DENY)
       │
       ▼
Capability Registry (Validation Contracts)
       │
       ▼
Capability Execution (Direct process invocation — zero shell=True)
       │
       ▼
Execution Result & Response Engine (Honest Reporting & Natural Feedback)
       │
       ▼
Context Update (Turns & Established Facts Recorded)
```

### Core Invariants:
1. **Language Independence:** An Intent like `OPEN_APPLICATION` with entity `{"application": "firefox"}` is identical whether entered in Persian (`فایرفاکس رو باز کن`) or English (`Open Firefox`).
2. **Deterministic Contextual Memory:** Conversational state (`active_app`, `active_directory`, `active_file`, `open_applications`) is tracked in bounded, isolated sessions without heuristic hallucination.
3. **Multi-Step Command Planning with Failure Isolation:** Commands with multiple clauses (`Chrome رو باز کن و فایل منیجر رو باز کن`) are mapped into a sequential `CommandPlan`. If step `n` fails or is blocked, subsequent steps `n+1..` are skipped.
4. **Authoritative Policy-First Security:** Neither the Context Engine nor the Command Planner may bypass the Policy Engine. High-risk operations (`DELETE_FILE`, `DELETE_FOLDER`, `SHUTDOWN`) require single-use, non-replayable confirmation tokens (`PendingConfirmation`).
5. **Zero-Shell Execution:** Arbitrary user strings are **never** evaluated by a shell (`os.system` and `shell=True` are strictly banned). Execution occurs only via validated executables identified through the Application Registry or standard desktop utilities.

---

## 2. Directory Structure

```text
RIATA/
├── app/
│   ├── __init__.py
│   ├── core/                  # Core constants, config, context, and logging
│   │   ├── config.py          # Configuration and environment loaders
│   │   ├── constants.py       # Intent names, thresholds, version metadata
│   │   ├── logger.py          # Structured logging with memory ring-buffer
│   │   └── context/           # v0.2.0 Context Engine
│   │       ├── models.py      # SessionContext and PendingConfirmation models
│   │       ├── manager.py     # Thread-safe ContextManager and session isolation
│   │       └── resolver.py    # Deterministic pronoun and deictic entity resolver
│   ├── engine/                # Rule-based Intent Engine & Planner
│   │   ├── intent.py          # Language-independent Intent data model
│   │   ├── matcher.py         # Pattern matching & confidence scoring
│   │   ├── normalizer.py      # Multi-language normalization engine
│   │   ├── entity_extractor.py# Extracts apps, folders, song names
│   │   ├── planner.py         # v0.2.0 Multi-step Command Planner & DAG
│   │   ├── router.py          # Orchestrates parsing, context, planner, policy
│   │   └── task.py            # Async execution and task tracking
│   ├── languages/             # Extensible language pack registry
│   │   ├── registry.py        # Central pack discovery and registry
│   │   ├── rules.py           # Base language rule interfaces
│   │   ├── detector.py        # Unicode script range detector
│   │   └── loader.py          # Backward-compatibility loader facade
│   ├── interaction/           # Conversational state & responses
│   │   ├── context.py         # Interaction turn memory & selection
│   │   └── responses.py       # Localized natural feedback generator
│   ├── policy/                # Risk-aware desktop security engine
│   │   ├── engine.py          # Evaluates ALLOW, CONFIRM, and DENY
│   │   └── decision.py        # Policy evaluation decision models
│   ├── capabilities/          # Modular desktop capabilities
│   │   ├── base.py            # Base capability contract
│   │   ├── registry.py        # Central capability dispatcher
│   │   ├── applications.py    # Desktop app launcher, closer, URL opener
│   │   ├── filesystem.py      # Folder and file creator, opener, deleter
│   │   ├── media.py           # Local audio scanner and playback
│   │   ├── system.py          # Terminal, settings, sysinfo, screenshot, reset
│   │   ├── processes.py       # Process capability foundation (stub)
│   │   ├── windows.py         # Window management foundation (stub)
│   │   ├── notifications.py   # Desktop notifications foundation (stub)
│   │   └── clipboard.py       # Clipboard foundation (stub)
│   ├── executor/              # Safe Linux action executors
│   │   ├── application.py     # App launcher, safe pkill closer, URL opener
│   │   ├── files.py           # Sandboxed file/folder operations
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
├── languages/                 # Modular declarative language packs
│   ├── fa/                    # Persian language pack (manifest, intents, rules)
│   └── en/                    # English language pack
├── src/                       # React Web Companion frontend
│   ├── App.tsx                # Context-aware inspector & interactive UI
│   └── main.tsx               # Web entrypoint
├── tests/                     # Automated test suite (127 tests across 23 modules)
├── docs/                      # Architectural and technical documentation
├── main.py                    # Main desktop application entrypoint
├── requirements.txt           # Runtime dependencies
├── requirements-dev.txt       # Development & test dependencies
├── pyproject.toml             # Modern package configuration
└── vite.config.ts             # Web Companion server with Python bridge
```

---

## 3. Context Engine & Entity Resolver

The **Context Engine** (`app/core/context/`) maintains state across conversation turns:
* `SessionContext`: Records active entities per isolated session (`session_id`).
  - `active_app`: Most recently targeted application (e.g. `Firefox`).
  - `active_directory`: Most recently opened or referenced directory.
  - `active_file`: Most recently opened or referenced file.
  - `open_applications`: Set of currently open desktop applications.
  - `pending_confirmation`: Single-use high-risk confirmation token.
* `Deterministic Entity Resolver` (`resolver.py`):
  - Resolves pronouns (Persian `-ش`, `اون`, `همونو` / English `it`, `that`).
  - Resolves locative containers (Persian `داخلش` / English `in it`, `inside`).
  - Detects ambiguities when multiple candidates exist and prompts for clarification.

---

## 4. Command Planner & Multi-Step Execution

The **Command Planner** (`app/engine/planner.py`) is a deterministic, rule-based sequential planner (not an autonomous or speculative AI agent):
* **Clause Splitting:** Splits complex utterances into ordered, individual clauses based on linguistic conjunction tokens (`و`, `and`, `then`).
* **Step Dependencies:** Maps step dependencies sequentially (step `i` depends on step `i-1` reaching `SUCCESS`).
* **Failure Isolation:** If any step fails or is blocked by security policy, subsequent steps are marked `SKIPPED` and not executed.
* **Deterministic State Machine:**
  - `PENDING` → `IN_PROGRESS` → `WAITING_CONFIRMATION` → `IN_PROGRESS` → `SUCCESS` (or `PARTIAL_SUCCESS` / `FAILED` / `BLOCKED` / `CANCELLED`).
* **Multi-Step Confirmation Flow (`WAITING_CONFIRMATION`):**
  - When a step in a multi-step plan requires confirmation (e.g. deleting a file), the plan transitions to `WAITING_CONFIRMATION`.
  - The overall execution result reports `NEEDS_CONFIRMATION` with `executed=False`.
  - Prior completed steps remain `SUCCESS`, the confirmed step is `PENDING`, and subsequent steps remain `PENDING`.
  - The plan is never marked `SUCCESS` prematurely.
* **Resume Lifecycle:**
  - Upon user confirmation (`بله` / `yes`), prerequisite dependencies are re-validated before execution.
  - If valid, the step undergoes authoritative Policy re-evaluation, Capability validation, and execution.
  - Subsequent steps proceed through the full pipeline. If all steps complete successfully, the plan finishes as `SUCCESS`. If any later step fails, it completes as `PARTIAL_SUCCESS`. If another confirmation is requested, the plan returns to `WAITING_CONFIRMATION`.

---

## 5. Policy Engine & Confirmation Tokens

Every executable step passes through `PolicyEngine.evaluate(intent)`:
* **ALLOW:** Low-risk standard operations proceed directly to capability execution.
* **CONFIRM:** High-risk operations (`DELETE_FILE`, `DELETE_FOLDER`, `SHUTDOWN`) generate a unique, cryptographically-bound `PendingConfirmation` token with an expiration timestamp. The action executes only upon explicit user confirmation (`بله` / `yes`).
* **DENY:** Destructive or privileged commands (`rm -rf`, `sudo`, `mkfs`) are unconditionally blocked before execution, returning `STATUS_PERMISSION_DENIED` with `executed=False`.
