# R.I.A.T.A — Intent Reference
**Responsive Intent Automation & Task Assistant (v0.1.1)**  
**Author:** Ali Kamrani (MRThugh)  

---

## Supported Intents in v0.1.1

| Intent | Capability | Description | Sample Persian Input | Sample English Input | Extracted Entities |
|---|---|---|---|---|---|
| `OPEN_APPLICATION` | `applications` | Launches registered desktop applications | `فایرفاکس رو باز کن` | `Open Firefox` | `application`: `"firefox"` |
| `OPEN_FOLDER` | `filesystem` | Opens standard user directories | `Downloads رو باز کن` | `Open Downloads` | `folder`: `"Downloads"` |
| `OPEN_FILE` | `filesystem` | Opens safe file within user home sandbox | `فایل report.pdf رو باز کن` | `Open file report.pdf` | `file`: `"report.pdf"` |
| `PLAY_MUSIC` | `media` | Searches `~/Music` directory and plays audio | `آهنگ Another Love رو پخش کن` | `Play Another Love` | `song`: `"Another Love"` |
| `OPEN_TERMINAL` | `system` | Launches default terminal emulator | `ترمینال رو باز کن` | `Open terminal` | *(None)* |
| `OPEN_FILE_MANAGER`| `system` | Opens system file manager | `فایل منیجر رو باز کن` | `Open file manager` | *(None)* |
| `OPEN_SETTINGS` | `system` | Opens desktop control center | `تنظیمات رو باز کن` | `Open settings` | *(None)* |
| `SHOW_SYSTEM_INFO` | `system` | Gathers OS, kernel, CPU, RAM, hostname | `مشخصات سیستم` | `System info` | *(None)* |
| `TAKE_SCREENSHOT` | `system` | Captures screenshot to `~/Pictures` | `اسکرین شات بگیر` | `Take a screenshot` | *(None)* |
| `EXIT_APPLICATION` | `system` | Gracefully closes R.I.A.T.A | `ریاتا رو ببند` | `Close riata` | *(None)* |
| `CLARIFY` | *(Engine)* | Prompts user when request is ambiguous | `اون رو باز کن` | `Open that` | *(None)* |
| `CONFIRM` | *(Context)* | Confirms a pending high-risk action | `بله` / `آره` | `yes` / `confirm` | *(None)* |
| `CANCEL` | *(Context)* | Cancels a pending action or selection | `کنسل` / `نه` | `cancel` / `no` | *(None)* |
| `UNKNOWN` | *(Engine)* | Provides example syntax for unrecognized inputs | `xyz 123` | `foo bar` | *(None)* |

---

## Adding a New Intent in v0.1.1

To introduce a new intent (e.g. `CHECK_BATTERY`):
1. **Define Constant:** Add `INTENT_CHECK_BATTERY = "CHECK_BATTERY"` to `app/core/constants.py`.
2. **Grammar & Patterns:** In each language pack (`languages/<lang>/intents.json`), add regular expressions and pattern rules.
3. **Responses:** In `languages/<lang>/responses.json`, define localized feedback templates.
4. **Capability Execution:** Implement the action in the corresponding capability (e.g. `app/capabilities/system.py`).
5. **Policy Definition:** If the action poses system risk, register it in `HIGH_RISK_INTENTS` in `app/policy/engine.py`.
