"""Reminder worker — polls for due reminders and dispatches them.

Usage:
    python -m app.worker          # loop mode (every 60s)
    python -m app.worker --once   # run once and exit
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("signal_os.worker")


def run_once():
    """Find due reminders, dispatch them, return count."""
    from app.db import SessionLocal
    from app.services.reminders import dispatch_due_reminders

    db = SessionLocal()
    try:
        dispatched = dispatch_due_reminders(db)
        logger.info("Dispatched %d reminder(s)", len(dispatched))
        return len(dispatched)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Signal OS reminder worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (default: loop every WORKER_INTERVAL seconds)",
    )
    args = parser.parse_args()

    interval = int(os.getenv("WORKER_INTERVAL", "60"))

    if args.once:
        logger.info("Worker running once")
        run_once()
        return

    logger.info("Worker starting in loop mode (interval=%ds)", interval)
    while True:
        try:
            run_once()
        except Exception as e:
            logger.error("Worker error: %s", e, exc_info=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
