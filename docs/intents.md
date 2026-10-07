# R.I.A.T.A — Intent Reference
**Responsive Intent Automation & Task Assistant (v0.2.0)**  
**Author:** Ali Kamrani (MRThugh)  

---

## Supported Intents in v0.2.0

| Intent | Capability | Description | Sample Persian Input | Sample English Input | Extracted Entities |
|---|---|---|---|---|---|
| `OPEN_APPLICATION` | `applications` | Launches registered desktop applications | `فایرفاکس رو باز کن` | `Open Firefox` | `application`: `"firefox"` |
| `CLOSE_APPLICATION` | `applications` | Safely terminates running applications via pkill | `فایرفاکس رو ببند` / `ببندش` | `Close Firefox` / `Close it` | `application`: `"firefox"` |
| `OPEN_URL` | `applications` | Opens sanitized HTTP/HTTPS web links in browser | `سایت github رو باز کن` | `Open URL github.com` | `url`: `"https://github.com"` |
| `OPEN_FOLDER` | `filesystem` | Opens standard user directories | `Downloads رو باز کن` | `Open Downloads` | `folder`: `"Downloads"` |
| `OPEN_FILE` | `filesystem` | Opens safe file within user home sandbox | `فایل report.pdf رو باز کن` | `Open file report.pdf` | `file`: `"report.pdf"` |
| `CREATE_FILE` | `filesystem` | Creates a new file inside sandbox | `فایل notes.txt رو بساز` | `Create file notes.txt` | `file`: `"notes.txt"`, `folder` *(opt)* |
| `DELETE_FILE` | `filesystem` | Safely deletes a file (requires confirmation) | `فایل old.txt رو حذف کن` | `Delete file old.txt` | `file`: `"old.txt"`, `folder` *(opt)* |
| `CREATE_FOLDER` | `filesystem` | Creates a new folder inside sandbox | `پوشه Projects رو بساز` | `Create folder Projects` | `folder`: `"Projects"` |
| `DELETE_FOLDER` | `filesystem` | Safely deletes empty directory inside sandbox | `پوشه temp رو حذف کن` | `Delete folder temp` | `folder`: `"temp"` |
| `PLAY_MUSIC` | `media` | Searches `~/Music` directory and plays audio | `آهنگ Another Love رو پخش کن` | `Play Another Love` | `song`: `"Another Love"` |
| `OPEN_TERMINAL` | `system` | Launches default terminal emulator | `ترمینال رو باز کن` | `Open terminal` | *(None)* |
| `OPEN_FILE_MANAGER`| `system` | Opens system file manager | `فایل منیجر رو باز کن` | `Open file manager` | *(None)* |
| `OPEN_SETTINGS` | `system` | Opens desktop control center | `تنظیمات رو باز کن` | `Open settings` | *(None)* |
| `SHOW_SYSTEM_INFO` | `system` | Gathers OS, kernel, CPU, RAM, hostname | `مشخصات سیستم` | `System info` | *(None)* |
| `TAKE_SCREENSHOT` | `system` | Captures screenshot to `~/Pictures` | `اسکرین شات بگیر` | `Take a screenshot` | *(None)* |
| `RESET_CONTEXT` | `system` | Clears conversation context and active entities | `فراموش کن` | `Forget` / `Reset context` | *(None)* |
| `EXIT_APPLICATION` | `system` | Gracefully closes R.I.A.T.A | `ریاتا رو ببند` | `Close riata` | *(None)* |
| `CLARIFY_AMBIGUITY`| *(Context)* | Prompts user when multiple candidates match pronoun | `ببندش` *(when 2+ apps open)* | `Close it` *(when 2+ apps open)*| `candidates` |
| `CONFIRM` | *(Context)* | Confirms a pending high-risk action token | `بله` / `آره` / `تأیید` | `yes` / `confirm` | *(None)* |
| `CANCEL` | *(Context)* | Cancels a pending action or selection | `کنسل` / `نه` / `لغو` | `cancel` / `no` | *(None)* |
| `UNKNOWN` | *(Engine)* | Provides example syntax for unrecognized inputs | `xyz 123` | `foo bar` | *(None)* |

---

## Multi-Step Planning in v0.2.0

When the user enters a compound command (e.g. `کروم رو باز کن و فایل منیجر رو باز کن`), the **Command Planner** decomposes the input into a `CommandPlan` containing sequential `CommandStep` objects. Each step is evaluated against the Policy Engine and executed with failure isolation.
