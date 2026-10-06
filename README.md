# R.I.A.T.A
### Responsive Intent Automation & Task Assistant
**Version:** 0.1.0  
**Author & Creator:** Ali Kamrani ([MRThugh](https://github.com/MRThugh))  
**Repository:** [https://github.com/MRThugh/RIATA](https://github.com/MRThugh/RIATA)  
**Platform:** Ubuntu Linux  
**License:** MIT  

---

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-brightgreen.svg)
![GUI](https://img.shields.io/badge/GUI-PySide6-41CD52.svg)
![Platform](https://img.shields.io/badge/platform-Ubuntu%20Linux-E95420.svg)
![Tests](https://img.shields.io/badge/tests-pytest-green.svg)

---

## 💡 What is R.I.A.T.A?

**R.I.A.T.A** (Responsive Intent Automation & Task Assistant) is a modern, privacy-respecting Linux desktop Intent Assistant.

Users communicate with their system through a clean, dark desktop chat interface using natural language in either **Persian (فارسی)** or **English**.

### 🔒 100% Offline & AI-Free in v0.1.0
R.I.A.T.A v0.1 does **not** rely on Large Language Models (LLMs), ChatGPT, cloud APIs, or online NLP endpoints. It is powered by a high-speed, deterministic, rule-based **Intent Engine** that separates natural language understanding from Linux desktop execution.

Both languages resolve to the exact same language-independent Intent representation:

* Persian: `فایرفاکس رو باز کن`
* English: `Open Firefox`

Both resolve to:
```python
Intent(
    name="OPEN_APPLICATION",
    entities={"application": "firefox"}
)
```

---

## ✨ Features in Release 0.1.0

- 🖥️ **PySide6 Desktop Chat Interface:** Minimalist, futuristic dark theme with smooth scrolling and responsive card layouts.
- 🇮🇷 **Native Persian (RTL) Support:** Custom normalizer handling `ي/ی`, `ك/ک`, `ۀ/ه`, ZWNJ, Persian numbers, and informal particles (`رو`, `را`, `لطفا`, `میخوام`).
- 🇬🇧 **Native English (LTR) Support:** Multi-variation matching (`open`, `launch`, `start`, `run`, polite phrases).
- 🧩 **Extensible Language-Pack Architecture:** Drop-in language packs (`languages/<lang>/`) automatically discovered at runtime.
- 🚀 **Application Registry & Dynamic Discovery:** Scans system `.desktop` files and binaries with alias resolution.
- 📁 **Folder & File Navigation:** Resolves canonical XDG directories (`Downloads`, `Documents`, `Pictures`, `Music`, `Desktop`, `Home`).
- 🎵 **Local Audio Search & Disambiguation:** Scans `~/Music` for `.mp3`, `.wav`, `.ogg`, `.flac`. Prompts user with numbered options if multiple tracks match.
- ⚙️ **System Utilities:** One-shot commands for Terminal, File Manager, Control Center Settings, and non-sensitive System Specs.
- 🛡️ **Zero-Shell Execution & Safety Protection:** Blocks destructive commands (`rm`, `sudo`, `mkfs`, `shutdown`) and uses direct `subprocess.Popen` without shell interpretation.
- 🧪 **Mock / Dry-Run Mode:** Test commands safely with `--dry-run` or `RIATA_DRY_RUN=1`.
- ⚡ **Asynchronous Concurrency:** Runs intent parsing and task execution on worker threads so the GUI never freezes.

---

## 🛠️ Technology Stack

- **Python 3.10+** (Python Standard Library wherever possible)
- **PySide6** (Qt6 GUI framework)
- **JSON** (Extensible language packs and configuration)
- **pytest** (Comprehensive automated unit test suite)

---

## 📁 Project Architecture

```text
RIATA/
│
├── app/
│   ├── core/                  # Configuration, constants, structured logging
│   │   ├── config.py
│   │   ├── constants.py
│   │   └── logger.py
│   │
│   ├── engine/                # Rule-based Intent Engine
│   │   ├── intent.py          # Language-independent Intent data model
│   │   ├── matcher.py         # Pattern matching & confidence scoring
│   │   ├── normalizer.py      # Persian/English NLP normalizer
│   │   ├── entity_extractor.py# Extracts apps, folders, song names
│   │   └── router.py          # Execution coordinator & context retention
│   │
│   ├── languages/             # Language pack loader & detector
│   │   ├── detector.py        # Unicode character range detector
│   │   └── loader.py          # Dynamic pack discovery
│   │
│   ├── executor/              # Safe Linux action executors
│   │   ├── application.py     # Desktop app launcher
│   │   ├── music.py           # Local audio player
│   │   ├── files.py           # Folder and file opener
│   │   ├── system.py          # Terminal, settings, sys info
│   │   ├── response_generator.py # Localized response translation
│   │   └── result.py          # ExecutionResult data model
│   │
│   ├── registry/              # Dynamic application discovery
│   │   └── applications.py
│   │
│   └── ui/                    # PySide6 desktop GUI
│       ├── main_window.py     # Main window with QThread concurrency
│       ├── chat_widget.py     # Smooth scrollable chat timeline
│       ├── message_widget.py  # User/Assistant bubbles with RTL/LTR
│       ├── input_widget.py    # Input area with Enter/Shift+Enter
│       └── styles.py          # Modern dark theme stylesheet
│
├── languages/
│   ├── fa/                    # Persian language pack
│   │   ├── language.json
│   │   ├── intents.json
│   │   └── normalization.json
│   └── en/                    # English language pack
│       ├── language.json
│       ├── intents.json
│       └── normalization.json
│
├── tests/                     # 100% passing test suite
│   ├── test_normalizer.py
│   ├── test_matcher.py
│   ├── test_intents.py
│   ├── test_entities.py
│   ├── test_languages.py
│   └── test_executor.py
│
├── docs/                      # Developer guides
│   ├── architecture.md
│   ├── intents.md
│   └── languages.md
│
├── main.py                    # Application entrypoint (GUI & CLI)
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

---

## 🚀 Installation & Running

### 1. Prerequisites
Ensure Python 3 and standard Qt libraries are installed on Ubuntu:
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv libegl1 libgl1 libxkbcommon0
```

### 2. Clone and Setup Environment
```bash
git clone https://github.com/MRThugh/RIATA.git
cd RIATA

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Launch GUI
```bash
python main.py
```

### 4. Developer & Headless Modes
Simulate execution without launching real processes:
```bash
python main.py --dry-run
```

Verbose logging:
```bash
python main.py --debug
```

Run in interactive CLI mode (for SSH/server sessions):
```bash
python main.py --cli
```

---

## 🧪 Running Automated Tests

Run the full automated test suite:
```bash
pytest -v
```

---

## 💬 Usage Examples

### Opening Applications
- 🇮🇷 `فایرفاکس رو باز کن`
- 🇮🇷 `ترمینال رو اجرا کن`
- 🇮🇷 `وی اس کد رو باز کن`
- 🇬🇧 `Open Firefox`
- 🇬🇧 `Launch terminal`
- 🇬🇧 `Start VS Code`

### Navigating Folders
- 🇮🇷 `Downloads رو باز کن`
- 🇮🇷 `پوشه Documents رو باز کن`
- 🇬🇧 `Open Downloads`
- 🇬🇧 `Open my pictures folder`

### Playing Music
- 🇮🇷 `آهنگ Another Love رو پخش کن`
- 🇮🇷 `یه موزیک پخش کن`
- 🇬🇧 `Play Another Love`
- 🇬🇧 `Play music`

### System Specs & Utilities
- 🇮🇷 `مشخصات سیستم`
- 🇮🇷 `اسکرین شات بگیر`
- 🇮🇷 `تنظیمات رو باز کن`
- 🇬🇧 `Show system info`
- 🇬🇧 `Take a screenshot`
- 🇬🇧 `Open settings`

---

## 🔒 Security & Safety Philosophy

R.I.A.T.A is designed as a **safe desktop task assistant, not an unrestricted root shell**.

1. **No Arbitrary Shell Execution:** Input is never evaluated by `bash` or `sh`.
2. **Strict Keyword Blocking:** Commands like `sudo`, `rm`, `mkfs`, `dd`, `shutdown`, `reboot`, and fork bombs are proactively intercepted.
3. **Restricted Filesystem Access:** File operations are strictly bound to user directories (`~`).

---

## 🗺️ Roadmap

- [x] **v0.1.0:** Deterministic rule-based Intent Engine, Persian & English packs, PySide6 GUI, application registry, audio playback, unit tests.
- [ ] **v0.2.0:** Extended system intents (volume control, screen brightness, Wi-Fi status).
- [ ] **v0.3.0:** Local offline speech-to-text (Whisper.cpp) for hands-free voice commands.
- [ ] **v1.0.0:** Pluggable local LLM parsing backend while preserving safety guardrails.

---

## 👨‍💻 Author

Created with pride by **Ali Kamrani ([MRThugh](https://github.com/MRThugh))**.  
Released under the **MIT License**.
