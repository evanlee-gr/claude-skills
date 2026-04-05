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

## Phase 1: Onboarding — Gather all required info

Work through these questions conversationally. Ask them all at once in a single message so the user
can answer in one go. Explain each briefly so they know why you need it.

```
I need 5 things before I can set everything up:

1. **Telegram bot token** — from @BotFather. If you don't have one yet, I'll walk you through it.
2. **Your Telegram user ID** — a number (not username). Message @userinfobot on Telegram to get it.
3. **Session tethering** — should the bot:
   (a) Always auto-detect your most recently active Claude Code session (recommended — survives /clear)
   (b) Be pinned to a specific session ID you provide
4. **Project directory** — the working directory Claude should use (e.g. the folder you have open in Claude Code right now)
5. **Save location** — where to save the bot scripts (default: C:\Users\<yourname>\)
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

### If they want a specific session ID (option b):
- Find it by running: `ls -lt ~/.claude/projects/<project-dir>/*.jsonl | head -1`
- Or ask Claude Code: "what is the current session ID?"

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

### 2b. Test claude --resume
Run a quick test to confirm `--resume` works non-interactively:
```bash
claude --resume <session_id> -p "say the word PINEAPPLE and nothing else" --dangerously-skip-permissions
```
- If output contains `PINEAPPLE` → great, proceed
- If `claude` not found → check PATH, advise running from the Claude Code terminal
- If session not found → auto-detect the latest `.jsonl` in the project dir

To auto-detect the latest session:
```python
import os, glob
files = sorted(glob.glob(os.path.join(CLAUDE_PROJECTS_DIR, "*.jsonl")), key=os.path.getmtime, reverse=True)
session_id = os.path.basename(files[0]).replace(".jsonl", "") if files else None
```

The Claude projects dir is derived from the project directory path:
- Replace path separators with `--` and strip the drive letter colon
- e.g. `C:\Users\zs\MyProject` → `C--Users-zs-MyProject`
- Full path: `C:\Users\<user>\.claude\projects\<encoded-path>\`

---

## Phase 3: Generate the three files

Use the values collected in Phase 1. Fill in all the placeholders before writing.

### File 1: `telegram_claude_bot.py`

See the full template in `scripts/bot_template.py`. Copy it verbatim and substitute:
- `__BOT_TOKEN__` → their token
- `__ALLOWED_USER_ID__` → their user ID (integer)
- `__PROJECT_DIR__` → their project directory (raw string)
- `__CLAUDE_PROJECTS_DIR__` → derived Claude projects dir (see above)

### File 2: `telegram_bot_watchdog.py`

See `scripts/watchdog_template.py`. Substitute same `__BOT_TOKEN__` and `__ALLOWED_USER_ID__`,
plus `__BOT_SCRIPT_PATH__` → full path to `telegram_claude_bot.py`.

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
Run as Administrator:
```
python C:\Users\<name>\setup_telegram_autostart.py
```
Then to start immediately without rebooting:
```
schtasks /Run /TN "TelegramClaudeBot"
```

### Step D — Test it
Send your bot a message on Telegram. It should reply "Bot online." on first contact.
Then send something like "what session are you connected to?" to verify continuity.

---

## Available bot commands (tell the user)

| Command | What it does |
|---------|-------------|
| `/help` | List all commands |
| `/status` | Show uptime, session ID, queue depth, session size |
| `/session` | Show current session ID |
| `/cancel` | Abort the currently running Claude task |

Any other message is forwarded to Claude and the response comes back in Telegram.

---

## Edge cases to handle

- **Two instances conflict**: The bot uses a lock file (`telegram_bot.lock`). If it complains about an existing instance, check if another process is running or delete the stale lock file.
- **Session file gets huge**: The bot warns at 10,000 lines. Advise the user to run `/compact` in Claude Code periodically.
- **Long responses**: Anything over 1,500 characters is sent as a `.txt` file attachment automatically.
- **Windows PATH issue**: If `claude` isn't found, run the bot from the Claude Code terminal (which has the right PATH), or add the Claude Code binary directory to system PATH.
- **psutil missing**: The watchdog uses psutil for stale lock cleanup. If missing, `pip install psutil`. The bot will still work without it but stale lock cleanup is less reliable.

---

## What the bot does (feature summary — share with user if they ask)

- Messages Telegram → forwarded to Claude Code session via `claude --resume`
- Full session continuity — Claude remembers everything from the current Claude Code session
- Auto-detects new sessions when you `/clear` in Claude Code
- Single worker thread (no concurrent `--resume` conflicts)
- HTML rendering (Claude markdown renders properly in Telegram)
- UTF-8 safe (no garbled characters)
- Typing indicator + edit-in-place responses
- Long responses (>1500 chars) sent as `.txt` file attachments
- `/help` `/status` `/session` `/cancel` commands
- Lock file (prevents two bot instances)
- Startup + crash notifications to your Telegram
- Graceful shutdown on Ctrl+C
- Watchdog process with auto-restart
- Windows Scheduled Task for boot auto-start
