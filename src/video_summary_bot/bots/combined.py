"""Combined bot - Runs both scheduler and listen bot in separate threads"""

import threading
import time
import logging
from video_summary_bot.bots.listen import main as listen_main
from video_summary_bot.scheduler import main as scheduler_main

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

_stop_event = threading.Event()

MAX_RESTARTS = 5
RESTART_DELAY = 10  # seconds between restarts


def _run_with_restart(target_fn, name):
    """Run a function in a loop, restarting it if it crashes."""
    restarts = 0
    while not _stop_event.is_set():
        try:
            logger.info(f"Starting {name}...")
            target_fn()
            # target_fn returned cleanly (shouldn't happen in normal operation)
            logger.warning(f"{name} exited cleanly — restarting")
        except Exception as e:
            logger.error(f"{name} crashed: {e}", exc_info=True)

        if _stop_event.is_set():
            break

        restarts += 1
        if restarts > MAX_RESTARTS:
            logger.critical(f"{name} has crashed {restarts} times — giving up")
            break

        logger.info(f"{name} restarting in {RESTART_DELAY}s (attempt {restarts}/{MAX_RESTARTS})...")
        _stop_event.wait(timeout=RESTART_DELAY)

    logger.info(f"{name} thread exiting")


def main():
    """Main function - runs both bots in parallel with automatic restart on crash"""
    print("Starting Video Summary Bot in COMBINED mode")
    print("=" * 60)
    print("Running both scheduler and listen bot simultaneously...")
    print("=" * 60)

    listen_thread = threading.Thread(
        target=_run_with_restart,
        args=(listen_main, "ListenBot"),
        name="ListenBot",
        daemon=True,
    )
    scheduler_thread = threading.Thread(
        target=_run_with_restart,
        args=(scheduler_main, "Scheduler"),
        name="Scheduler",
        daemon=True,
    )

    listen_thread.start()
    scheduler_thread.start()

    print("\nBoth bots are running!")
    print("   - Scheduler: Checking channels every 10 minutes")
    print("   - Listen Bot: Waiting for YouTube URLs from users")
    print("\nPress Ctrl+C to stop both bots...\n")

    try:
        while listen_thread.is_alive() or scheduler_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping both bots...")
        _stop_event.set()
        listen_thread.join(timeout=15)
        scheduler_thread.join(timeout=15)
        print("Goodbye!")


if __name__ == "__main__":
    main()
