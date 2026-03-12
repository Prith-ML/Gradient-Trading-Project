# Gradient-Trading-Project

USPTO patent data pipeline. Downloads patent data from PatentsView and loads it into PostgreSQL. **Free, no API key required.**

## About

This project builds a data pipeline for **USPTO patent data**—granted patents, applications, inventors, and assignees. Data comes from [PatentsView](https://patentsview.org/), a free, government-backed source. The pipeline downloads bulk TSV files, parses them, and loads them into a normalized PostgreSQL schema for querying and analysis. Use cases include innovation research, competitive intelligence, and patent landscape analysis.

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set DB_PASSWORD and DB_PORT (default 5433)
```

```bash
python scripts/setup_uspto_db.py
python -m uspto.pipeline
```

~10 min to load 10k patents + applications.

## Verify

```sql
SELECT patent_id, patent_title, patent_date FROM patents LIMIT 20;
```

## Project Structure

```
uspto/
├── pipeline.py           # Download + load
├── config.py             # Settings
├── database/
│   └── uspto_schema.sql  # Schema
├── HARDWARE_REQUIREMENTS.md
└── README.md
scripts/
├── setup_uspto_db.py     # Create DB + schema
├── run_uspto_update.py   # Update run (force refresh, for scheduling)
└── schedule_uspto_updates.py  # Daemon: runs pipeline weekly
```

## 10M Patent Load

To load ~10 million patents (full test):

```bash
# Set in .env:
USPTO_MAX_PATENTS=10000000
USPTO_QUICK_MODE=0

python -m uspto.pipeline
```

Expect 2–5 hours for full load (patents + applications + inventors + assignees).

## Incremental Updates

To keep the DB updated when PatentsView publishes new data:

**One-off update:**
```bash
python scripts/run_uspto_update.py
```

**Scheduled updates (Windows Task Scheduler):** Create a task that runs `python scripts/run_uspto_update.py` weekly (e.g. Sundays).

**Scheduled updates (daemon):**
```bash
python scripts/schedule_uspto_updates.py
```
Runs every Sunday at 2 AM. Leave the process running.

## Config

| Variable | Default |
|----------|---------|
| `DB_PASSWORD` | — |
| `DB_PORT` | 5433 |
| `USPTO_MAX_PATENTS` | 10000 |
| `USPTO_QUICK_MODE` | 1 (patents + applications only) |
| `USPTO_FORCE_REFRESH` | 0 (set by run_uspto_update.py) |

Set `USPTO_QUICK_MODE=0` and `USPTO_MAX_PATENTS=0` for full load (2–5 hrs).
