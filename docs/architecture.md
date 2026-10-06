# R.I.A.T.A — Architecture Overview
**Responsive Intent Automation & Task Assistant (v0.1.0)**  
**Author:** Ali Kamrani (MRThugh)  
**License:** MIT  
**Platform:** Ubuntu Linux  

---

## 1. Architectural Philosophy

R.I.A.T.A is built upon a strict **Separation of Concerns**:

```
[ User Input (Natural Language) ]
               │
               ▼
   [ Language Detection ] ────────► (fa / en)
               │
               ▼
    [ Language Normalizer ] ───────► (Normalizes character variants, whitespace, polite particles)
               │
               ▼
     [ Intent Matcher ] ──────────► (Deterministic rule-based pattern matching)
               │
               ▼
    [ Entity Extractor ] ─────────► (Isolates application, folder, song entities)
               │
               ▼
     [ Intent Object ] ───────────► (Language-independent: Intent name + Entity dictionary)
               │
               ▼
     [ Intent Router ] ───────────► (Routes to specialized executor modules)
               │
               ▼
    [ Controlled Action ] ────────► (subprocess.Popen with registered binaries — NO shell=True)
               │
               ▼
   [ Execution Result ] ──────────► (Status code, message key, parameters)
               │
               ▼
  [ Response Generator ] ─────────► (Translates result to user language pack)
               │
               ▼
   [ Visual Presentation ] ───────► (Modern PySide6 chat UI with RTL/LTR support)
```

### Core Invariants:
1. **Language Independence:** An Intent like `OPEN_APPLICATION` with entity `{"application": "firefox"}` is identical whether entered in Persian (`فایرفاکس رو باز کن`) or English (`Open Firefox`).
2. **Safe Execution:** Arbitrary user strings are **never** evaluated by a shell (`os.system` and `shell=True` are banned). Execution occurs only via validated executables identified through the Application Registry or standard desktop utilities.
3. **Destructive Protection:** Dangerous actions (`sudo`, `rm`, `mkfs`, `shutdown`, `reboot`, etc.) are recognized and rejected before reaching execution.
4. **Offline & AI-Free:** Version 0.1 operates deterministically without machine learning models, external internet APIs, or cloud NLP services.

---

## 2. Directory Structure

```text
RIATA/
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── config.py             # Configuration and environment loaders
│   │   ├── constants.py          # Intent names, thresholds, banned commands
│   │   └── logger.py             # Structured logging with memory broadcast
│   ├── engine/
│   │   ├── intent.py             # Dataclass representation of parsed intent
│   │   ├── matcher.py            # Rule-based intent parser and disambiguation
│   │   ├── normalizer.py         # Multi-language normalization engine
│   │   ├── entity_extractor.py   # Extracts application, folder, audio entities
│   │   └── router.py             # Orchestrates parsing, dispatch, and context
│   ├── languages/
│   │   ├── detector.py           # Local Unicode-based script detector
│   │   └── loader.py             # Dynamic language pack discovery
│   ├── executor/
│   │   ├── application.py        # Safe execution of desktop apps
│   │   ├── files.py              # XDG folder and safe user file opener
│   │   ├── music.py              # ~/Music recursive scanner & player
│   │   ├── system.py             # Terminal, settings, file manager, sys info
│   │   ├── response_generator.py # Localized response translation
│   │   └── result.py             # ExecutionResult dataclass
│   ├── registry/
│   │   └── applications.py       # Application aliases, .desktop scanner, which
│   └── ui/
│       ├── main_window.py        # PySide6 main window with QThread execution
│       ├── chat_widget.py        # Scrollable timeline container
│       ├── message_widget.py     # User and Assistant bubbles with RTL/LTR
│       ├── input_widget.py       # Text editor with Enter/Shift+Enter
│       └── styles.py             # Futuristic dark stylesheet
├── languages/
│   ├── fa/                       # Persian language pack
│   └── en/                       # English language pack
├── tests/                        # Full automated test suite (pytest)
├── docs/                         # Architecture, intents, and language guides
├── main.py                       # CLI / GUI desktop entrypoint
└── requirements.txt
```

---

## 3. Asynchronous Concurrency

To ensure the desktop UI remains fluid and responsive (preventing GUI freezes when searching directories or launching external processes):
- The `MainWindow` employs `QThread` and `QObject` worker patterns.
- Command processing runs on a separate worker thread.
- Results are signaled back to the Qt main event loop for message bubble rendering.

---

## 4. Future AI Extensibility

The `BaseIntentParser` interface is abstract:
```python
class BaseIntentParser(ABC):
    @abstractmethod
    def parse(self, text: str, context: Optional[dict[str, Any]] = None) -> Intent:
        pass
```
In future releases, an `AIIntentParser` or hybrid parser can be plugged into `IntentRouter` without altering executors, UI components, or language pack structures.
