#!/usr/bin/env python3
"""
Run USPTO pipeline in update mode.
Forces re-download of PatentsView bulk files and loads new records.
Use for scheduled syncs (cron, Task Scheduler) to keep DB current.
Existing rows are skipped (ON CONFLICT DO NOTHING); only new patents are inserted.
"""
import os
import sys

# Force refresh so we get latest PatentsView data
os.environ["USPTO_FORCE_REFRESH"] = "1"

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uspto.pipeline import run_pipeline

if __name__ == "__main__":
    run_pipeline()
