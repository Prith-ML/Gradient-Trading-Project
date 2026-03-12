#!/usr/bin/env python3
"""
Schedule USPTO pipeline to run periodically (e.g. weekly).
Keeps the database updated when PatentsView publishes new bulk data.
Run this script and leave it running; it will invoke the pipeline on schedule.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import schedule
except ImportError:
    print("Install schedule: pip install schedule")
    sys.exit(1)


def run_update():
    os.environ["USPTO_FORCE_REFRESH"] = "1"
    from uspto.pipeline import run_pipeline
    run_pipeline()


if __name__ == "__main__":
    # Default: run every Sunday at 2 AM (when PatentsView typically updates)
    schedule.every().sunday.at("02:00").do(run_update)

    # Or run daily at 3 AM: schedule.every().day.at("03:00").do(run_update)
    # Or run every 6 hours: schedule.every(6).hours.do(run_update)

    print("USPTO update scheduler started. Runs every Sunday at 02:00.")
    print("Press Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        import time
        time.sleep(60)
