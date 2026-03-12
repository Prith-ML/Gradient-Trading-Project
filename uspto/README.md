# USPTO Patent Data Pipeline

Data pipeline for **USPTO patent data** from [PatentsView](https://patentsview.org/). Downloads bulk TSV files and loads them into PostgreSQL. **Free, no API key required.**

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Ensure .env has DB_PASSWORD and DB_PORT (same as Twitter setup)

# 3. Create database and schema
python scripts/setup_uspto_db.py

# 4. Run pipeline (downloads + loads)
python -m uspto.pipeline
```

## Data Loaded

**Quick mode (default):** 10k patents + 10k applications (~10 min)  
**Full mode:** Set `USPTO_QUICK_MODE=0` and `USPTO_MAX_PATENTS=0` for full dataset.

| Table | Source | Default (quick) | Full |
|-------|--------|-----------------|------|
| patents | g_patent | 10k | 12.5M |
| applications | g_application | 10k | 12.5M |
| inventors | g_inventor_disambiguated | — | 24M |
| assignees | g_assignee_disambiguated | — | 10.6M |

## Schema

See `uspto/database/uspto_schema.sql`. Core tables: `patents`, `applications`, `inventors`, `assignees`, `patent_inventors`, `patent_assignees`, `locations`, `patent_cpc`.

## Hardware

See `uspto/HARDWARE_REQUIREMENTS.md`.
