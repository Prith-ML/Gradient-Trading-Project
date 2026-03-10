# Gradient-Trading-Project

## Overview

A comprehensive trading system leveraging gradient-based optimization and social media signals (Twitter/X) for financial market analysis. Includes a **Twitter data pipeline** that fetches 500,000 tweets and stores them in PostgreSQL.

## Twitter Data Pipeline

Data pipeline for fetching **500,000 tweets** from X (Twitter) API v2 and storing them in a local PostgreSQL database.

### Features

- **Twitter API v2** integration via `tweepy`
- **PostgreSQL** schema with normalized tables
- **Checkpoint/resume** for long-running ingestion
- **Rate limiting** to respect API limits
- **Documented schema** and hardware requirements

### Quick Start

1. **Prerequisites**: Python 3.9+, PostgreSQL 12+, X Developer account (Basic tier or higher for 500k tweets)

2. **Create Database**:
   ```bash
   psql -U postgres -c "CREATE DATABASE twitter_data;"
   ```

3. **Install & Configure**:
   ```bash
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env: set TWITTER_BEARER_TOKEN and DB_PASSWORD
   ```

4. **Initialize Schema**:
   ```bash
   python scripts/setup_db.py
   ```

5. **Run Pipeline**:
   ```bash
   python pipeline.py
   ```

### Project Structure

```
.
├── config.py              # Configuration (env vars)
├── pipeline.py            # Main pipeline entry point
├── etl/
│   └── twitter_etl.py     # ETL logic for DB writes
├── database/
│   ├── twitter_schema.sql # PostgreSQL schema
│   └── SCHEMA_DOCUMENTATION.md
├── scripts/
│   ├── setup_db.py        # Apply schema
│   └── create_database.sql
├── .env.example
├── requirements.txt
├── HARDWARE_REQUIREMENTS.md
└── README.md
```

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TWITTER_BEARER_TOKEN` | — | X API Bearer token (required) |
| `DB_HOST` | localhost | PostgreSQL host |
| `TARGET_TWEET_COUNT` | 500000 | Target number of tweets |
| `SEARCH_QUERY` | lang:en -is:retweet -is:reply | Search query |
| `REQUESTS_PER_WINDOW` | 60 | API requests per 15 min (Basic tier) |

### Hardware Requirements

See **[HARDWARE_REQUIREMENTS.md](HARDWARE_REQUIREMENTS.md)** for CPU, RAM, disk, network, and time estimates.

### Schema

See **[database/SCHEMA_DOCUMENTATION.md](database/SCHEMA_DOCUMENTATION.md)** for table descriptions and example queries.

### API Notes

- **Search Recent** (`/2/tweets/search/recent`) returns tweets from the **last 7 days** only.
- For 500k tweets you need **Basic** ($100/mo) or **Pro** tier.
- Free tier: 1,500 tweets/month (not sufficient for 500k).
