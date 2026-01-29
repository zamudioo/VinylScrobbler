#ZamudioScrobbler/backend/monitor_service.py
import subprocess
from logger import logger
from config import(
    USER,
    UID,
    WAYLAND_DISPLAY,
    OUTPUT,
    MODE,
)

def _run(cmd):
    subprocess.run(
        [
            "sudo", "-u", USER,
            "bash", "-c",
            f"""
            export XDG_RUNTIME_DIR=/run/user/{UID}
            export WAYLAND_DISPLAY={WAYLAND_DISPLAY}
            {' '.join(cmd)}
            """
        ],
        check=True
    )


def turn_off_monitor():
    try:
        _run([
            "wlr-randr",
            "--output", OUTPUT,
            "--off"
        ])
        logger.info("Monitor turned OFF")
    except Exception as e:
        logger.error(f"Failed to turn off monitor: {e}")


def turn_on_monitor():
    try:
        _run([
            "wlr-randr",
            "--output", OUTPUT,
            "--on",
            "--mode", MODE
        ])
        logger.info("Monitor turned ON")
    except Exception as e:
        logger.error(f"Failed to turn on monitor: {e}")
