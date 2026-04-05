---
name: telegram-claude-bot
description: >
  Sets up a production-ready Telegram bot that bridges Telegram messages directly into a Claude Code
  session using `claude --resume`, giving the user mobile access to their active Claude Code session.
  Use this skill whenever the user wants to: control Claude Code from Telegram, set up a Telegram bot
  that talks to Claude, create a mobile interface for Claude Code, bridge Telegram to a Claude session,
  or asks anything like "can I use Claude from my phone?", "set up telegram bot for claude",
  "telegram claude integration", "access claude code remotely". Trigger even if the user says
  "telegram bot" without mentioning Claude Code — they almost certainly mean this.
---

# Telegram → Claude Code Bot Setup

You are helping the user set up a production-ready Telegram bot that bridges their Telegram messages
into their active Claude Code session via `claude --resume`. The bot lets them chat with their Claude
Code session from their phone or any Telegram client.

---

## ⚠️ Windows-Specific Gotchas — Read This First

These are hard-won lessons from real debugging. Every one of these has caused silent failures.

### 1. `.cmd` files CANNOT be executed directly by `subprocess.Popen` on Windows

`subprocess.Popen(["claude", ...])` **will fail** with "file not found" because Python's
`CreateProcess` looks for `.exe` files, not `.cmd` wrappers.

**Always use this pattern:**
```python
CLAUDE_CMD = [
    "cmd", "/c",
    r"C:\Users\<name>\AppData\Roaming\fnm\node-versions\v24.14.1\installation\claude.cmd"
]
# Then call it like:
subprocess.Popen(CLAUDE_CMD + ["--resume", session_id, "-p", prompt, ...])
```

**Never do this:**
```python
subprocess.Popen(["claude", "--resume", ...])   # BROKEN on Windows
subprocess.Popen(["claude.cmd", "--resume", ...])  # Also broken
```

### 2. fnm PATH is NOT available outside interactive PowerShell

Claude CLI is often installed via fnm (Fast Node Manager). fnm only adds itself to PATH when an
interactive PowerShell session loads the profile script. Scripts launched from:
- Regular PowerShell windows
- Windows Task Scheduler
- Watchdog scripts

...do NOT have fnm in PATH. Even `os.environ["PATH"]` injection is not enough — the `.cmd` wrapper
itself is the fix. Use the `["cmd", "/c", "full\path\claude.cmd"]` pattern above.

**How to find the full path to claude.cmd:**
```powershell
Get-Command claude | Select-Object -ExpandProperty Source
# e.g. C:\Users\zs\AppData\Roaming\fnm\node-versions\v24.14.1\installation\claude.cmd
```

### 3. Images: use stream-json, NOT `--resume`

Two separate approaches are needed for text vs image messages:

| Message type | Claude invocation |
|---|---|
| Text | `CLAUDE_CMD + ["--resume", session_id, "-p", message, ...]` |
| Image | `CLAUDE_CMD + ["-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose", ...]` |

**Never combine `--resume` with `--input-format stream-json`.** This causes an indefinite hang when
the session file is large — Claude loads the full session context AND the image at the same time
and never finishes.

### 4. stream-json requires ALL THREE flags

`--input-format stream-json` requires:
- `--output-format stream-json`
- `--verbose`
- `-p` (print mode)

Missing any one causes a silent failure or wrong output format.

### 5. Do NOT delete temp image files in the `finally` block

On Windows, the subprocess may still hold the file handle open when `finally` runs,
causing a `PermissionError`. Don't delete temp images — Windows cleans `%TEMP%` automatically.

### 6. Unpack worker queue item OUTSIDE the inner try block

```python
# CORRECT — variables always defined for except/finally
def worker():
    while not shutdown_event.is_set():
        item = None
        try:
            item = message_queue.get(timeout=1)
        except queue.Empty:
            continue

        chat_id, text, image_path = item  # ← outside try
        try:
            ...

# WRONG — if queue.get() raises, chat_id/text/image_path are never defined
def worker():
    while not shutdown_event.is_set():
        try:
            chat_id, text, image_path = message_queue.get(timeout=1)  # ← inside try
            ...
```

### 7. Use HTML parse mode, not Markdown, for Telegram

Claude's output contains `**bold**`, `--` dashes, and special characters that render as literal
asterisks or garbled UTF-8 (`â€"`) in Telegram's Markdown mode.

Use `parse_mode: "HTML"` and convert markdown to `<b>`, `<i>`, `<pre>`, `<code>` tags.
Also always set `encoding='utf-8', errors='replace'` on all subprocess calls.

### 8. Windows Scheduled Task requires Administrator

`setup_telegram_autostart.py` uses `schtasks` with `/RL HIGHEST`. Running from a regular
PowerShell window gives "Access denied". Must right-click → **Run as Administrator**.

---

## Phase 1: Onboarding — Gather all required info

Work through these questions conversationally. Ask them all at once in a single message so the user
can answer in one go.

```
I need 6 things before I can set everything up:

1. **Telegram bot token** — from @BotFather. If you don't have one yet, I'll walk you through it.
2. **Your Telegram user ID** — a number (not username). Message @userinfobot on Telegram to get it.
3. **Claude binary path** — the full path to claude.cmd on your machine. Run this in PowerShell:
      Get-Command claude | Select-Object -ExpandProperty Source
   It will look like: C:\Users\<name>\AppData\Roaming\fnm\node-versions\v24.x.x\installation\claude.cmd
4. **Project directory** — the working directory Claude should use (the folder open in Claude Code)
5. **Save location** — where to save the bot scripts (default: C:\Users\<name>\)
6. **Auto-start on Windows boot?** — yes/no (sets up a Windows Scheduled Task)
```

### If they don't have a bot token yet — guide them:
1. Open Telegram → search **@BotFather** (verified ✅)
2. Send `/newbot`
3. Give it a display name (e.g. "My Claude Assistant")
4. Give it a username ending in `bot` (e.g. `myassistant_bot`)
5. Copy the token BotFather sends back

### If they don't have their user ID yet:
- Open Telegram → search **@userinfobot** → send `/start`
- Copy the number next to "Id:"

### If they can't find claude.cmd:
Run in PowerShell: `Get-Command claude | Select-Object -ExpandProperty Source`
If that fails (fnm not in PATH), look in:
`C:\Users\<name>\AppData\Roaming\fnm\node-versions\` — find the latest version folder.
The file is at `<version-folder>\installation\claude.cmd`

---

## Phase 2: Validate before writing anything

### 2a. Verify bot token
```python
import requests
r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe")
print(r.json())
```
- If `ok: true` → proceed, show them the bot name
- If `ok: false` → tell them the token is invalid and ask them to check @BotFather

### 2b. Test claude.cmd via cmd /c

Run a quick test to confirm `claude.cmd` works non-interactively via the cmd /c pattern:
```python
import subprocess
result = subprocess.run(
    ["cmd", "/c", r"<their-claude-cmd-path>", "--version"],
    capture_output=True, text=True
)
print(result.stdout)  # Should print: "2.x.xx (Claude Code)"
```
- If it prints the version → perfect, the path is correct
- If "not found" or error → the path is wrong, ask them to re-run `Get-Command claude`
- Do NOT test with `["claude", "--version"]` — that will fail with FileNotFoundError on Windows

### 2c. Derive the Claude projects directory

The Claude projects dir is derived from the project directory path:
- Replace path separators with `--` and strip the drive letter colon
- e.g. `C:\Users\zs\MyProject` → `C--Users-zs-MyProject`
- Full path: `C:\Users\<user>\.claude\projects\<encoded-path>\`

Auto-detect the latest session:
```python
import os
files = [f for f in os.listdir(CLAUDE_PROJECTS_DIR) if f.endswith(".jsonl")]
files.sort(key=lambda f: os.path.getmtime(os.path.join(CLAUDE_PROJECTS_DIR, f)), reverse=True)
session_id = files[0].replace(".jsonl", "") if files else None
```

---

## Phase 3: Generate the three files

Use the values collected in Phase 1. Fill in all placeholders before writing.

### File 1: `telegram_claude_bot.py`

See the full template in `scripts/bot_template.py`. Copy it verbatim and substitute:
- `__BOT_TOKEN__` → their token
- `__ALLOWED_USER_ID__` → their user ID (integer, no quotes)
- `__PROJECT_DIR__` → their project directory (raw string, e.g. `r"C:\Users\zs\MyProject"`)
- `__CLAUDE_PROJECTS_DIR__` → derived Claude projects dir (see Phase 2c)
- `__CLAUDE_CMD_PATH__` → full path to claude.cmd (e.g. `C:\Users\zs\AppData\Roaming\fnm\node-versions\v24.14.1\installation\claude.cmd`)

### File 2: `telegram_bot_watchdog.py`

See `scripts/watchdog_template.py`. Substitute:
- `__BOT_TOKEN__` → their token
- `__ALLOWED_USER_ID__` → their user ID
- `__BOT_SCRIPT_PATH__` → full path to `telegram_claude_bot.py`

### File 3: `setup_telegram_autostart.py`

See `scripts/autostart_template.py`. Substitute `__WATCHDOG_SCRIPT_PATH__` → full path to watchdog.

---

## Phase 4: Install dependencies

```bash
pip install requests psutil
```

If pip install fails, try `python -m pip install requests psutil`.
Confirm with `python -c "import requests, psutil; print('OK')"`.

---

## Phase 5: Guide the user through launch

Give them these steps in order:

### Step A — Start a chat with your bot on Telegram
1. Open Telegram, search for your bot's username (e.g. `@myassistant_bot`)
2. Tap **Start** — required before the bot can message you

### Step B — Run the watchdog (not the bot directly)
```
python C:\Users\<name>\telegram_bot_watchdog.py
```
The watchdog will start the bot and restart it automatically if it ever crashes.
You should see "Watchdog started. Bot coming online..." in the terminal.

### Step C — Auto-start on Windows boot (if they said yes)
**IMPORTANT: Must be run as Administrator (right-click PowerShell → Run as Administrator)**
```
python C:\Users\<name>\setup_telegram_autostart.py
```
Then to start immediately without rebooting:
```
schtasks /Run /TN "TelegramClaudeBot"
```

### Step D — Test it
Send your bot a message on Telegram. It should reply "Bot online." on first contact.
Then send something like "say PINEAPPLE and nothing else" to verify Claude is connected.
Then send a photo with a caption to verify image upload works.

---

## Available bot commands (tell the user)

| Command | What it does |
|---------|-------------|
| `/help` | List all commands |
| `/status` | Show uptime, session ID, queue depth, session size |
| `/session` | Show current session ID |
| `/cancel` | Abort the currently running Claude task |

Any other text message is forwarded to Claude.
Photos (with optional caption) are sent to Claude for vision analysis.

---

## Edge cases to handle

- **Two instances conflict**: The bot uses a lock file (`telegram_bot.lock`). If it complains about an existing instance, check if another process is running or delete the stale lock file. The watchdog auto-cleans stale locks using psutil.
- **Session file gets huge**: The bot warns at 10,000 lines. Advise the user to run `/compact` in Claude Code periodically.
- **Long responses**: Anything over 1,500 characters is sent as a `.txt` file attachment automatically.
- **`claude.cmd` not found**: Path in `CLAUDE_CMD` is wrong. Run `Get-Command claude | Select-Object -ExpandProperty Source` in PowerShell to get the correct path.
- **Image not processing**: Check that `--resume` is NOT being used with stream-json. Check that all three flags are present: `--input-format stream-json`, `--output-format stream-json`, `--verbose`.
- **Scheduled Task "Access denied"**: Must run `setup_telegram_autostart.py` from an **Administrator** PowerShell window.
- **psutil missing**: The watchdog uses psutil for stale lock cleanup. If missing, `pip install psutil`. The bot will still work without it but stale lock cleanup is less reliable.
- **Markdown not rendering**: Bot uses HTML parse mode. Claude's markdown is converted to HTML tags. If you see `**bold**` or `â€"` in Telegram, check `parse_mode` and `encoding='utf-8'` on subprocess calls.

---

## What the bot does (feature summary — share with user if they ask)

- Messages Telegram → forwarded to Claude Code session via `claude --resume`
- Full session continuity — Claude remembers everything from the current Claude Code session
- Auto-detects new sessions when you `/clear` in Claude Code
- **Image upload support** — send a photo from Telegram (with optional caption); Claude analyses it via vision (base64 stream-json, same as desktop app)
- Single worker thread (no concurrent `--resume` conflicts)
- HTML rendering (Claude markdown renders properly in Telegram — no `**` or garbled characters)
- UTF-8 safe (no garbled characters)
- Typing indicator + edit-in-place responses
- Long responses (>1500 chars) sent as `.txt` file attachments
- `/help` `/status` `/session` `/cancel` commands
- Lock file (prevents two bot instances)
- Startup + crash notifications to your Telegram
- Graceful shutdown on Ctrl+C
- Watchdog process with auto-restart
- Windows Scheduled Task for boot auto-start

---

## Lessons Learned (debugging history)

These mistakes were all made during initial development. They're documented so future installs avoid them.

| # | Mistake | Why it happened | Fix |
|---|---------|-----------------|-----|
| 1 | `subprocess.Popen(["claude", ...])` fails silently | `.cmd` files aren't `.exe`; Python's CreateProcess can't execute them directly | Use `["cmd", "/c", "full\path\claude.cmd", ...]` |
| 2 | `claude` not found even after PATH injection | fnm only adds PATH in interactive PowerShell sessions, not in scripts/tasks | Use full absolute path in `CLAUDE_CMD` — don't rely on PATH at all |
| 3 | Images: tried telling Claude to "use Read tool on path X" | Claude didn't comply; it's non-interactive in `-p` mode | Abandoned; use base64 stream-json instead |
| 4 | `stream-json + --resume` hangs indefinitely | Loading a large session file AND a base64 image simultaneously overwhelms the startup | Remove `--resume` for image calls; images don't need session history |
| 5 | `stream-json` produced no output | Missing `--output-format stream-json` and/or `--verbose` | All three flags required together |
| 6 | `NameError: image_path not defined` in worker finally | `image_path` unpacked inside `try`; undefined if `queue.get()` raised | Unpack `item` outside the try block |
| 7 | `**bold**` and `â€"` showing in Telegram | Telegram Markdown mode doesn't handle Claude's output | Switch to HTML parse mode + markdown_to_html converter |
| 8 | Image file deleted before subprocess could read it | `finally` block deleted temp file while subprocess still had handle open | Don't delete — let Windows Temp auto-clean |
| 9 | Scheduled Task "Access denied" | `schtasks /RL HIGHEST` requires admin | Right-click PowerShell → Run as Administrator |
