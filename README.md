# Gradient Trading – Twitter Data Pipeline

Data pipeline for fetching **500,000 tweets** from X (Twitter) API v2 and storing them in a local PostgreSQL database. Built for the [Gradient-Trading-Project](https://github.com/Prith-ML/Gradient-Trading-Project).

## Features

- **Twitter API v2** integration via `tweepy`
- **PostgreSQL** schema with normalized tables
- **Checkpoint/resume** for long-running ingestion
- **Rate limiting** to respect API limits
- **Documented schema** and hardware requirements

## Quick Start

### 1. Prerequisites

- Python 3.9+
- PostgreSQL 12+
- X Developer account with API access (Basic tier or higher for 500k tweets)

### 2. Create Database

```bash
# Create database (as postgres user)
psql -U postgres -c "CREATE DATABASE twitter_data;"
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env: set TWITTER_BEARER_TOKEN and DB_PASSWORD
```

### 5. Initialize Schema

```bash
python scripts/setup_db.py
```

### 6. Run Pipeline

```bash
python pipeline.py
```

The pipeline will run until it reaches 500,000 tweets (or runs out of results). Progress is checkpointed; you can stop and resume later.

## Project Structure

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

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TWITTER_BEARER_TOKEN` | — | X API Bearer token (required) |
| `DB_HOST` | localhost | PostgreSQL host |
| `DB_NAME` | twitter_data | Database name |
| `TARGET_TWEET_COUNT` | 500000 | Target number of tweets |
| `SEARCH_QUERY` | lang:en -is:retweet -is:reply | Search query |
| `REQUESTS_PER_WINDOW` | 60 | API requests per 15 min (Basic tier) |

## Hardware Requirements

See **[HARDWARE_REQUIREMENTS.md](HARDWARE_REQUIREMENTS.md)** for:

- CPU, RAM, disk, network
- PostgreSQL tuning
- Time estimates by API tier

## Schema

See **[database/SCHEMA_DOCUMENTATION.md](database/SCHEMA_DOCUMENTATION.md)** for table descriptions and example queries.

## API Notes

- **Search Recent** (`/2/tweets/search/recent`) returns tweets from the **last 7 days** only.
- For 500k tweets you need **Basic** ($100/mo) or **Pro** tier.
- Free tier: 1,500 tweets/month (not sufficient for 500k).
