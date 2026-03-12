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
└── setup_uspto_db.py     # Create DB + schema
```

## Config

| Variable | Default |
|----------|---------|
| `DB_PASSWORD` | — |
| `DB_PORT` | 5433 |
| `USPTO_MAX_PATENTS` | 10000 |
| `USPTO_QUICK_MODE` | 1 (patents + applications only) |

Set `USPTO_QUICK_MODE=0` and `USPTO_MAX_PATENTS=0` for full load (2–5 hrs).
