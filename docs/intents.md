# R.I.A.T.A — Intent Reference
**Responsive Intent Automation & Task Assistant (v0.1.0)**  
**Author:** Ali Kamrani (MRThugh)  

---

## Supported Intents

| Intent | Description | Sample Persian Input | Sample English Input | Extracted Entities |
|---|---|---|---|---|
| `OPEN_APPLICATION` | Launches registered desktop applications | `فایرفاکس رو باز کن` | `Open Firefox` | `application`: `"firefox"` |
| `OPEN_FOLDER` | Opens standard user directories | `Downloads رو باز کن` | `Open Downloads` | `folder`: `"Downloads"` |
| `OPEN_FILE` | Opens safe file within user home | `فایل report.pdf رو باز کن` | `Open file report.pdf` | `file`: `"report.pdf"` |
| `PLAY_MUSIC` | Searches local `~/Music` directory and plays | `آهنگ Another Love رو پخش کن` | `Play Another Love` | `song`: `"Another Love"` |
| `OPEN_TERMINAL` | Launches default terminal emulator | `ترمینال رو باز کن` | `Open terminal` | *(None)* |
| `OPEN_FILE_MANAGER`| Opens Ubuntu file manager | `فایل منیجر رو باز کن` | `Open file manager` | *(None)* |
| `OPEN_SETTINGS` | Opens desktop control center | `تنظیمات رو باز کن` | `Open settings` | *(None)* |
| `SHOW_SYSTEM_INFO` | Gathers OS, kernel, CPU, RAM, hostname | `مشخصات سیستم` | `System info` | *(None)* |
| `TAKE_SCREENSHOT` | Takes safe screenshot to `~/Pictures` | `اسکرین شات بگیر` | `Take a screenshot` | *(None)* |
| `EXIT_APPLICATION` | Gracefully closes R.I.A.T.A | `ریاتا رو ببند` | `Close riata` | *(None)* |
| `CLARIFY` | Prompts user when request is ambiguous | `اون رو باز کن` | `Open that` | *(None)* |
| `UNKNOWN` | Suggests example syntax for unrecognized commands | `xyz 123` | `foo bar` | *(None)* |

---

## Adding a New Intent

To introduce a new intent (e.g., `CHECK_BATTERY`):
1. **Define Constant:** Add `INTENT_CHECK_BATTERY = "CHECK_BATTERY"` to `app/core/constants.py`.
2. **Grammar & Patterns:** In each language pack (`languages/<lang>/intents.json`), add regular expressions and keywords.
3. **Response Strings:** In `languages/<lang>/language.json`, define localized success and error messages.
4. **Executor:** In `app/executor/system.py` (or a dedicated executor), create `execute_check_battery(intent: Intent) -> ExecutionResult`.
5. **Dispatch:** Register the handler in `app/engine/router.py`.
