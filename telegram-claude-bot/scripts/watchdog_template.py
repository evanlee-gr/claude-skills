"""
Watchdog for telegram_claude_bot.py
- Starts the bot as a subprocess
- If it crashes, waits 5 seconds and restarts it
- Sends a Telegram message to Evan after each restart
- Logs to telegram_watchdog.log
- This is the script that Windows Task Scheduler runs on boot
"""
import subprocess
import time
import os
import sys
import requests
from datetime import datetime

BOT_SCRIPT = r"__BOT_SCRIPT_PATH__"
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telegram_watchdog.log")
LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telegram_bot.lock")
PYTHON = sys.executable

BOT_TOKEN = "__BOT_TOKEN__"
ALLOWED_USER_ID = __ALLOWED_USER_ID__
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def notify(msg):
    """Send a Telegram message directly (bypassing the bot process)."""
    try:
        requests.post(
            f"{BASE_URL}/sendMessage",
            json={"chat_id": ALLOWED_USER_ID, "text": msg},
            timeout=10
        )
    except Exception as e:
        log(f"[WARN] Could not send Telegram notification: {e}")


def cleanup_stale_lock():
    """Remove lock file if the PID inside is no longer running."""
    if not os.path.exists(LOCK_FILE):
        return
    try:
        with open(LOCK_FILE) as f:
            pid = int(f.read().strip())
        # Check if process is alive
        import psutil
        if not psutil.pid_exists(pid):
            log(f"Removing stale lock file (PID {pid} is dead).")
            os.remove(LOCK_FILE)
    except Exception:
        # psutil not available or bad PID — just remove it
        try:
            os.remove(LOCK_FILE)
        except Exception:
            pass


def main():
    log("Watchdog started.")
    log(f"Watching: {BOT_SCRIPT}")
    notify("Watchdog started. Bot coming online...")
    restart_count = 0

    while True:
        cleanup_stale_lock()
        log(f"Starting bot (run #{restart_count + 1})...")
        try:
            proc = subprocess.run([PYTHON, BOT_SCRIPT])
            exit_code = proc.returncode
            if exit_code == 0:
                log("Bot exited cleanly (code 0). Restarting in 5 seconds...")
                notify("Bot restarted (clean exit).")
            else:
                log(f"Bot crashed (exit code {exit_code}). Restarting in 5 seconds...")
                notify(f"Bot crashed (exit {exit_code}). Restarting now...")
        except Exception as e:
            log(f"Failed to launch bot: {e}. Retrying in 5 seconds...")
            notify(f"Bot failed to launch: {e}. Retrying...")

        restart_count += 1
        time.sleep(5)


if __name__ == "__main__":
    main()
