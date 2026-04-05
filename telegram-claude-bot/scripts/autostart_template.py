"""
Run this ONCE to register the Telegram bot watchdog as a Windows Scheduled Task.
It will start automatically every time you log into Windows.

Run with: python setup_telegram_autostart.py
To remove: python setup_telegram_autostart.py --remove
"""
import subprocess
import sys
import os

TASK_NAME = "TelegramClaudeBot"
PYTHON = sys.executable
WATCHDOG = r"__WATCHDOG_SCRIPT_PATH__"
WORKING_DIR = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    return result.returncode


def install():
    print(f"Registering scheduled task: {TASK_NAME}")
    print(f"Python : {PYTHON}")
    print(f"Script : {WATCHDOG}")
    print()

    # Delete existing task if present (ignore errors)
    run(f'schtasks /Delete /TN "{TASK_NAME}" /F')

    # Create task: runs at logon, for current user, in hidden window
    cmd = (
        f'schtasks /Create /TN "{TASK_NAME}" '
        f'/TR "\\\"{PYTHON}\\\" \\\"{WATCHDOG}\\\"" '
        f'/SC ONLOGON '
        f'/RL HIGHEST '
        f'/F'
    )
    code = run(cmd)
    if code == 0:
        print()
        print("SUCCESS! Bot will now auto-start every time you log in.")
        print(f"To start it right now without rebooting, run:")
        print(f'  schtasks /Run /TN "{TASK_NAME}"')
        print()
        print("To check status:")
        print(f'  schtasks /Query /TN "{TASK_NAME}"')
    else:
        print()
        print("ERROR: Could not create scheduled task.")
        print("Try running this script as Administrator (right-click -> Run as administrator).")


def remove():
    print(f"Removing scheduled task: {TASK_NAME}")
    code = run(f'schtasks /Delete /TN "{TASK_NAME}" /F')
    if code == 0:
        print("Task removed successfully.")
    else:
        print("Task not found or could not be removed.")


if __name__ == "__main__":
    if "--remove" in sys.argv:
        remove()
    else:
        install()
