import requests
import subprocess
import time
import os
import re
import threading
import queue
import logging
import signal
import sys
import msvcrt
import tempfile
import base64
import json
from datetime import datetime

BOT_TOKEN = "__BOT_TOKEN__"
ALLOWED_USER_ID = __ALLOWED_USER_ID__
PROJECT_DIR = r"__PROJECT_DIR__"
CLAUDE_PROJECTS_DIR = r"__CLAUDE_PROJECTS_DIR__"

# ── Claude binary path (CRITICAL on Windows) ──────────────────────────────────
# .cmd files CANNOT be executed by subprocess.Popen with a list on Windows.
# Python's CreateProcess looks for .exe files, not .cmd.
# Always use ["cmd", "/c", "full\path\to\claude.cmd"] — never just ["claude", ...].
# The path below must point to the actual claude.cmd in the fnm/npm install dir.
CLAUDE_CMD = [
    "cmd", "/c",
    r"__CLAUDE_CMD_PATH__"   # e.g. C:\Users\zs\AppData\Roaming\fnm\node-versions\v24.14.1\installation\claude.cmd
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OFFSET_FILE = os.path.join(SCRIPT_DIR, "telegram_offset.txt")
LOG_FILE = os.path.join(SCRIPT_DIR, "telegram_bot.log")
LOCK_FILE = os.path.join(SCRIPT_DIR, "telegram_bot.lock")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Warn when session file exceeds this many lines
SESSION_LINE_WARN_THRESHOLD = 10000

# Responses longer than this get sent as a .txt file
MAX_INLINE_LENGTH = 1500

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ── Globals ───────────────────────────────────────────────────────────────────
message_queue = queue.Queue()
current_proc = None          # The running claude subprocess (for /cancel)
current_proc_lock = threading.Lock()
shutdown_event = threading.Event()
notify_chat_id = None        # Set on first message; used for startup notification


# ── Lock file (single instance) ───────────────────────────────────────────────

def acquire_lock():
    """Write PID to lock file. Returns file handle (keep open to hold lock).
    Raises SystemExit if another instance is already running."""
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE) as f:
                old_pid = f.read().strip()
            log.error(f"Lock file exists (PID {old_pid}). Another instance may be running.")
            log.error(f"If it's stale, delete: {LOCK_FILE}")
            sys.exit(1)
        fh = open(LOCK_FILE, "w")
        fh.write(str(os.getpid()))
        fh.flush()
        # Lock the file on Windows so it can't be opened by another process
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        return fh
    except OSError as e:
        log.error(f"Could not acquire lock: {e}")
        sys.exit(1)


def release_lock(fh):
    try:
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        fh.close()
        os.remove(LOCK_FILE)
    except Exception:
        pass


# ── Session detection ─────────────────────────────────────────────────────────

def get_latest_session_id():
    """Auto-detect the most recently modified .jsonl session file."""
    try:
        files = [f for f in os.listdir(CLAUDE_PROJECTS_DIR) if f.endswith(".jsonl")]
        if not files:
            return None
        files.sort(
            key=lambda f: os.path.getmtime(os.path.join(CLAUDE_PROJECTS_DIR, f)),
            reverse=True
        )
        return files[0].replace(".jsonl", "")
    except Exception as e:
        log.warning(f"Could not auto-detect session ID: {e}")
        return None


def get_session_line_count(session_id):
    """Return line count of the session file, or 0 on error."""
    try:
        path = os.path.join(CLAUDE_PROJECTS_DIR, f"{session_id}.jsonl")
        with open(path, encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


# ── Markdown → HTML ───────────────────────────────────────────────────────────

def markdown_to_html(text):
    """Convert Claude's markdown output to Telegram-compatible HTML."""
    parts = re.split(r'(```[\s\S]*?```|`[^`]+`)', text)
    result = []
    for part in parts:
        if part.startswith('```') and part.endswith('```'):
            inner = part[3:-3]
            inner = re.sub(r'^[a-zA-Z]*\n', '', inner)
            inner = inner.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            result.append(f'<pre>{inner}</pre>')
        elif part.startswith('`') and part.endswith('`') and len(part) > 2:
            inner = part[1:-1]
            inner = inner.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            result.append(f'<code>{inner}</code>')
        else:
            p = part.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            p = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', p)
            p = re.sub(r'__(.+?)__', r'<b>\1</b>', p)
            p = re.sub(r'\*(.+?)\*', r'<i>\1</i>', p)
            p = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'<i>\1</i>', p)
            p = re.sub(r'~~(.+?)~~', r'<s>\1</s>', p)
            p = re.sub(r'^#{1,3}\s+(.+)$', r'<b>\1</b>', p, flags=re.MULTILINE)
            p = re.sub(r'^[-*_]{3,}$', '─────────────', p, flags=re.MULTILINE)
            result.append(p)
    return ''.join(result)


# ── Telegram helpers ──────────────────────────────────────────────────────────

def send_message(chat_id, text, use_html=True):
    """Send a message, splitting into chunks over 4000 chars."""
    max_len = 4000
    if use_html:
        text = markdown_to_html(text)
    chunks = [text[i:i + max_len] for i in range(0, len(text), max_len)]
    last_msg_id = None
    for chunk in chunks:
        payload = {"chat_id": chat_id, "text": chunk}
        if use_html:
            payload["parse_mode"] = "HTML"
        resp = requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=10)
        if not resp.ok and use_html:
            resp = requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": chunk}, timeout=10)
        if resp.ok:
            last_msg_id = resp.json().get("result", {}).get("message_id")
    return last_msg_id


def send_placeholder(chat_id):
    """Send 'On it...' and return its message_id for later editing."""
    resp = requests.post(
        f"{BASE_URL}/sendMessage",
        json={"chat_id": chat_id, "text": "On it..."},
        timeout=10
    )
    if resp.ok:
        return resp.json().get("result", {}).get("message_id")
    return None


def edit_message(chat_id, message_id, text, use_html=True):
    """Edit an existing message in-place."""
    max_len = 4000
    if use_html:
        text = markdown_to_html(text)
    # Edit first chunk in-place; send remaining chunks as new messages
    first_chunk = text[:max_len]
    payload = {"chat_id": chat_id, "message_id": message_id, "text": first_chunk}
    if use_html:
        payload["parse_mode"] = "HTML"
    resp = requests.post(f"{BASE_URL}/editMessageText", json=payload, timeout=10)
    if not resp.ok and use_html:
        requests.post(f"{BASE_URL}/editMessageText",
                      json={"chat_id": chat_id, "message_id": message_id, "text": first_chunk},
                      timeout=10)
    # Send any overflow as additional messages
    for i in range(max_len, len(text), max_len):
        chunk = text[i:i + max_len]
        send_message(chat_id, chunk, use_html=False)


def send_typing(chat_id):
    try:
        requests.post(f"{BASE_URL}/sendChatAction",
                      json={"chat_id": chat_id, "action": "typing"}, timeout=5)
    except Exception:
        pass


def send_file(chat_id, filename, content):
    """Send text content as a .txt file attachment."""
    try:
        resp = requests.post(
            f"{BASE_URL}/sendDocument",
            data={"chat_id": chat_id},
            files={"document": (filename, content.encode("utf-8"), "text/plain")},
            timeout=30
        )
        return resp.ok
    except Exception as e:
        log.error(f"send_file failed: {e}")
        return False


def download_photo(message):
    """Download the highest-res photo from a Telegram message. Returns local file path or None."""
    try:
        # Pick the largest photo (last in array = highest resolution)
        photos = message.get("photo", [])
        if not photos:
            return None
        file_id = photos[-1]["file_id"]

        # Get download path from Telegram
        r = requests.get(f"{BASE_URL}/getFile", params={"file_id": file_id}, timeout=10)
        if not r.ok:
            log.error(f"getFile failed: {r.text}")
            return None
        file_path = r.json()["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

        # Download to a temp file
        img_data = requests.get(download_url, timeout=30).content
        ext = os.path.splitext(file_path)[-1] or ".jpg"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext, prefix="tg_photo_")
        tmp.write(img_data)
        tmp.close()
        log.info(f"Photo saved to: {tmp.name}")
        return tmp.name
    except Exception as e:
        log.error(f"download_photo failed: {e}")
        return None


def get_updates(offset=None):
    params = {"timeout": 30, "allowed_updates": ["message"]}
    if offset is not None:
        params["offset"] = offset
    try:
        resp = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=35)
        return resp.json()
    except Exception as e:
        log.error(f"get_updates failed: {e}")
        return None


# ── Claude runner ─────────────────────────────────────────────────────────────

MEDIA_TYPES = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
               '.gif': 'image/gif', '.webp': 'image/webp'}


def run_claude(message, chat_id, image_path=None):
    """Run claude. Images sent as base64 via stream-json (same as desktop app).

    KEY DESIGN DECISIONS:
    - Text messages use --resume <session_id> for full session continuity.
    - Images use --input-format stream-json (base64 over stdin) WITHOUT --resume.
      Reason: combining stream-json with --resume causes an indefinite hang when
      the session file is large (Claude tries to load the full context + the image).
    - stream-json requires ALL THREE flags: -p, --input-format stream-json,
      --output-format stream-json, AND --verbose. Missing any one causes failure.
    """
    global current_proc

    session_id = get_latest_session_id()
    if not session_id:
        return "Could not detect active Claude session. Is Claude Code running?"

    log.info(f"Resuming session: {session_id}")

    line_count = get_session_line_count(session_id)
    if line_count > SESSION_LINE_WARN_THRESHOLD:
        send_message(chat_id,
                     f"Warning: session file is {line_count:,} lines long. "
                     f"Consider running <code>/compact</code> in Claude Code to keep responses fast.",
                     use_html=True)
    try:
        if image_path:
            # Send image as base64 via stream-json — exactly like the desktop app
            ext = os.path.splitext(image_path)[1].lower()
            media_type = MEDIA_TYPES.get(ext, 'image/jpeg')
            with open(image_path, 'rb') as f:
                img_b64 = base64.b64encode(f.read()).decode('utf-8')
            log.info(f"Sending image as {media_type} via stream-json")

            stdin_payload = json.dumps({'type': 'user', 'message': {'role': 'user', 'content': [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': img_b64}},
                {'type': 'text', 'text': message or 'Describe this image.'}
            ]}})

            # NOTE: Do NOT add --resume here. stream-json + --resume hangs indefinitely
            # when the session file is large.
            proc = subprocess.Popen(
                CLAUDE_CMD + ['-p',
                              '--input-format', 'stream-json',
                              '--output-format', 'stream-json',
                              '--verbose', '--dangerously-skip-permissions'],
                cwd=PROJECT_DIR,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='replace'
            )
            with current_proc_lock:
                current_proc = proc
            stdout, stderr = proc.communicate(input=stdin_payload, timeout=300)
            with current_proc_lock:
                current_proc = None

            # Parse stream-json output to extract text
            parts = []
            for line in stdout.splitlines():
                try:
                    obj = json.loads(line)
                    if obj.get('type') == 'assistant':
                        for block in obj.get('message', {}).get('content', []):
                            if block.get('type') == 'text':
                                parts.append(block['text'])
                except Exception:
                    pass
            output = '\n'.join(parts).strip()

        else:
            # Text-only: standard --resume mode for full session continuity
            proc = subprocess.Popen(
                CLAUDE_CMD + ['--resume', session_id, '-p', message, '--dangerously-skip-permissions'],
                cwd=PROJECT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='replace'
            )
            with current_proc_lock:
                current_proc = proc
            stdout, stderr = proc.communicate(timeout=300)
            with current_proc_lock:
                current_proc = None
            output = stdout.strip()

        if proc.returncode == -15:
            return "Cancelled."
        if not output and stderr:
            output = f"Error:\n{stderr.strip()}"
        if not output:
            output = "(No response received)"
        return output

    except subprocess.TimeoutExpired:
        with current_proc_lock:
            if current_proc:
                current_proc.kill()
                current_proc = None
        return "Timed out after 5 minutes."
    except FileNotFoundError:
        return f"`claude.cmd` not found at: {CLAUDE_CMD[2]}\nCheck CLAUDE_CMD path in the script."
    except Exception as e:
        with current_proc_lock:
            current_proc = None
        return f"Unexpected error: {e}"


# ── Worker thread ─────────────────────────────────────────────────────────────

def worker():
    """Process one message at a time — prevents concurrent --resume conflicts.

    IMPORTANT: Unpack `item` OUTSIDE the inner try block. If unpacking is inside
    try and queue.get() raises, `chat_id`/`text`/`image_path` are never defined,
    causing NameError in the except/finally block.

    IMPORTANT: Do NOT delete image_path in the finally block. On Windows, the
    subprocess may still have the file handle open when finally runs, causing
    a PermissionError. Windows Temp folder is cleaned up by the OS periodically.
    """
    while not shutdown_event.is_set():
        item = None
        try:
            item = message_queue.get(timeout=1)
        except queue.Empty:
            continue

        # Unpack outside try so variables are always defined for finally
        chat_id, text, image_path = item
        try:
            send_typing(chat_id)
            placeholder_id = send_placeholder(chat_id)
            response = run_claude(text, chat_id, image_path=image_path)

            # Long response → send as file
            if len(response) > MAX_INLINE_LENGTH:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"claude_response_{ts}.txt"
                sent = send_file(chat_id, filename, response)
                if placeholder_id:
                    edit_message(chat_id, placeholder_id, "Response attached as file.", use_html=False)
                if not sent and not placeholder_id:
                    send_message(chat_id, response)
            else:
                if placeholder_id:
                    edit_message(chat_id, placeholder_id, response)
                else:
                    send_message(chat_id, response)

            log.info(f"[OUT] {response[:120]}")
        except Exception as e:
            log.error(f"Worker error: {e}")
            send_message(chat_id, f"Internal error: {e}", use_html=False)
        finally:
            message_queue.task_done()
            # Do NOT delete image_path here — Windows may still have the file
            # handle open. Temp files are cleaned by Windows automatically.


# ── Graceful shutdown ─────────────────────────────────────────────────────────

def handle_shutdown(signum, frame):
    log.info("Shutdown signal received. Finishing current task then exiting...")
    shutdown_event.set()
    # Wait for queue to drain (max 60s)
    try:
        message_queue.join()
    except Exception:
        pass
    sys.exit(0)


# ── Offset helpers ────────────────────────────────────────────────────────────

def load_offset():
    if os.path.exists(OFFSET_FILE):
        try:
            with open(OFFSET_FILE) as f:
                return int(f.read().strip())
        except Exception:
            pass
    return None


def save_offset(offset):
    with open(OFFSET_FILE, "w") as f:
        f.write(str(offset))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global notify_chat_id

    lock_fh = acquire_lock()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    log.info("Telegram-Claude bot started.")
    log.info(f"PID         : {os.getpid()}")
    log.info(f"Project dir : {PROJECT_DIR}")
    log.info(f"Allowed user: {ALLOWED_USER_ID}")
    log.info(f"Log file    : {LOG_FILE}")
    detected = get_latest_session_id()
    log.info(f"Active session: {detected or 'NONE FOUND'}")
    log.info("Polling for messages...")

    # Start worker thread
    t = threading.Thread(target=worker, daemon=True)
    t.start()

    offset = load_offset()
    last_session_id = detected
    start_time = datetime.now()

    # Send startup notification once we know the chat_id (first message)
    startup_notified = False

    try:
        while not shutdown_event.is_set():
            updates = get_updates(offset)

            if not updates or not updates.get("ok"):
                time.sleep(5)
                continue

            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                save_offset(offset)

                message = update.get("message")
                if not message:
                    continue

                user_id = message.get("from", {}).get("id")
                chat_id = message.get("chat", {}).get("id")
                text = message.get("text") or message.get("caption") or ""
                text = text.strip()
                has_photo = bool(message.get("photo"))

                if user_id != ALLOWED_USER_ID:
                    log.warning(f"Ignored message from unknown user {user_id}")
                    continue

                # Must have text, a photo, or both
                if not text and not has_photo:
                    continue

                # Save chat_id for notifications
                notify_chat_id = chat_id

                # Send startup notification on first interaction
                if not startup_notified:
                    send_message(chat_id, "Bot online.", use_html=False)
                    startup_notified = True

                # Detect session change
                current_session = get_latest_session_id()
                if current_session and current_session != last_session_id:
                    send_message(chat_id,
                                 f"New session detected: <code>{current_session[:8]}...</code> — switched over automatically.",
                                 use_html=True)
                    last_session_id = current_session

                # ── Commands ──────────────────────────────────────────────────

                if text == "/start":
                    send_message(chat_id,
                                 "Hi! I'm your Claude Code assistant.\n\nSend any message and I'll run it in your active Claude Code session.\n\nType /help for commands.",
                                 use_html=False)
                    continue

                if text == "/help":
                    send_message(chat_id,
                                 "<b>Available commands</b>\n\n"
                                 "/status — uptime, session, queue depth\n"
                                 "/session — show active session ID\n"
                                 "/cancel — abort the current Claude task\n"
                                 "/help — show this message\n\n"
                                 "Send any text message to Claude.\n"
                                 "Send a photo (with optional caption) and Claude will analyse it.",
                                 use_html=True)
                    continue

                if text == "/status":
                    sid = get_latest_session_id()
                    uptime = str(datetime.now() - start_time).split(".")[0]
                    queued = message_queue.qsize()
                    lines = get_session_line_count(sid) if sid else 0
                    warn = " (consider /compact)" if lines > SESSION_LINE_WARN_THRESHOLD else ""
                    send_message(chat_id,
                                 f"<b>Bot status</b>\n"
                                 f"Uptime: <code>{uptime}</code>\n"
                                 f"Session: <code>{sid}</code>\n"
                                 f"Session size: <code>{lines:,} lines{warn}</code>\n"
                                 f"Queue: <code>{queued} pending</code>",
                                 use_html=True)
                    continue

                if text == "/session":
                    sid = get_latest_session_id()
                    send_message(chat_id, f"Active session ID:\n<code>{sid}</code>", use_html=True)
                    continue

                if text == "/cancel":
                    with current_proc_lock:
                        if current_proc:
                            current_proc.terminate()
                            send_message(chat_id, "Cancelling current task...", use_html=False)
                        else:
                            send_message(chat_id, "Nothing is running right now.", use_html=False)
                    continue

                # ── Download photo if present ─────────────────────────────────
                image_path = None
                if has_photo:
                    image_path = download_photo(message)
                    if not image_path:
                        send_message(chat_id, "Could not download the image. Please try again.", use_html=False)
                        continue
                    if not text:
                        text = "Please analyse this image and describe what you see."

                # ── Queue message ─────────────────────────────────────────────
                log.info(f"[IN]  {'[photo] ' if has_photo else ''}{text[:100]}")
                q_size = message_queue.qsize()
                if q_size >= 5:
                    send_message(chat_id, "Queue is full (5 pending). Please wait.", use_html=False)
                elif q_size > 0:
                    send_message(chat_id,
                                 f"Queued (position {q_size + 1}) — waiting for current task to finish.",
                                 use_html=False)
                    message_queue.put((chat_id, text, image_path))
                else:
                    message_queue.put((chat_id, text, image_path))

    finally:
        release_lock(lock_fh)
        log.info("Bot shut down cleanly.")


if __name__ == "__main__":
    main()
