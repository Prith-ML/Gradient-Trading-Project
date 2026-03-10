# Database Quick Reference

## Setup

```bash
# Create DB and schema
python scripts/setup_db.py
```

## Connection

```
Host: localhost (or DB_HOST from .env)
Port: 5432
Database: twitter_data
User: postgres
```

## Useful Queries

**Tweet count:**
```sql
SELECT COUNT(*) FROM tweets;
```

**Recent ingestion runs:**
```sql
SELECT run_id, started_at, result_count, status
FROM ingestion_runs
ORDER BY started_at DESC
LIMIT 10;
```

**Trending hashtags (24h):**
```sql
SELECT h.tag, COUNT(th.tweet_id) AS cnt
FROM hashtags h
JOIN tweet_hashtags th ON h.hashtag_id = th.hashtag_id
JOIN tweets t ON th.tweet_id = t.tweet_id
WHERE t.created_at > NOW() - INTERVAL '24 hours'
GROUP BY h.tag
ORDER BY cnt DESC
LIMIT 100;
```

---
# Database Schema - Quick Reference

## File Structure

```
database/
├── twitter_schema.sql          # Complete SQL schema (run this first)
├── SCHEMA_DOCUMENTATION.md     # Detailed table descriptions and examples
├── ETL_EXAMPLES.md             # Python/SQL examples for loading data
├── setup_database.sh           # Automated database initialization script
├── queries/                    # Useful pre-built queries (optional)
│   ├── trending_hashtags.sql
│   ├── user_analytics.sql
│   └── engagement_analysis.sql
└── migrations/                 # Database versioning (optional)
```

## Setup Steps (5 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Database
```bash
# Copy and edit the environment file
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 3. Initialize Database
```bash
python scripts/setup_db.py
```

Or manually:
```bash
psql -U postgres -d twitter_data -f database/twitter_schema.sql
```

### 4. Verify Installation
```sql
-- Connect to the database
psql -U postgres -d twitter_data

-- Check tables were created
\dt

-- Expected output:
-- users
-- tweets
-- hashtags
-- tweet_hashtags
-- tweet_mentions
-- tweet_urls
-- urls
-- media
-- tweet_media
-- places
-- tweet_relationships
-- ingestion_runs
-- tweet_ingestion
-- user_daily_stats
-- hashtag_daily_stats
```

## Core Tables Overview

### Data Model Diagram

```
                    ┌──────────────┐
                    │    users     │
                    └──────────────┘
                          ▲
                          │
            ┌─────────────┼─────────────┐
            │             │             │
        author_id   mentioned_user    reply_user
            │             │             │
      ┌─────▼─────┐      │      ┌──────▼─────┐
      │   tweets  │◄─────┴──────►│   hashtags │
      └─────┬─────┘  tweet_rel   └────────────┘
            │       (retweet,
            │        quote, reply)
    ┌───────┼───────┬───────────┐
    │       │       │           │
    │     media   urls      mentions
    │       │       │           │
    └───────┴───────┴───────────┘

Additional:
- places: Geo data for tweets
- ingestion_runs: Track API calls
- *_daily_stats: Pre-aggregated metrics
```

## Common Queries

### Find Trending Hashtags (24h)
```sql
SELECT h.tag, COUNT(*) as count
FROM tweet_hashtags th
JOIN hashtags h ON th.hashtag_id = h.hashtag_id
JOIN tweets t ON th.tweet_id = t.tweet_id
WHERE t.created_at > NOW() - INTERVAL '24 hours'
GROUP BY h.tag
ORDER BY count DESC LIMIT 50;
```

### Get User Timeline
```sql
SELECT t.* FROM tweets t WHERE t.author_id = ? ORDER BY t.created_at DESC LIMIT 100;
```

### Find Conversation Thread
```sql
SELECT * FROM tweets WHERE conversation_id = ? ORDER BY created_at;
```

### Find Most Engaged Tweets
```sql
SELECT * FROM tweets
ORDER BY (like_count + retweet_count + quote_count) DESC
LIMIT 50;
```

### Track URL Sharing
```sql
SELECT u.domain, COUNT(tu.tweet_id) as shares
FROM tweet_urls tu
JOIN urls u ON tu.url_id = u.url_id
WHERE u.domain LIKE '%.com'
GROUP BY u.domain
ORDER BY shares DESC LIMIT 50;
```

## Storage Requirements

| Dataset Size | Estimated Storage | Notes |
|--------------|-------------------|-------|
| 1M tweets | ~800 MB | Typical daily ingestion |
| 10M tweets | ~8 GB | 10 days of data |
| 100M tweets | ~80 GB | 100 days of data |
| 1B tweets | ~800 GB | ~2.7 years of data |

## Performance Tips

1. **Always use indexes**: Don't create SELECT where you could index
2. **Batch inserts**: Use `INSERT INTO ... ON CONFLICT` for upserts
3. **Partition large tables**: By `created_at` for tweets older than 1 month
4. **Analyze queries**: Use `EXPLAIN ANALYZE` before optimizing
5. **Archive old data**: Consider moving tweets older than 1 year to archive tables

## Maintenance

### Weekly
```sql
-- Vacuum and analyze
VACUUM ANALYZE;

-- Check ingestion runs for errors
SELECT * FROM ingestion_runs 
WHERE status = 'error' AND started_at > NOW() - INTERVAL '7 days';
```

### Monthly
```sql
-- Check index efficiency
SELECT * FROM pg_stat_user_indexes;
```

## Troubleshooting

### Connection Issues
```bash
# Test connection
psql -h localhost -U postgres -d twitter_data -c "SELECT 1;"
```

### Table Not Found
```sql
-- List all tables
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';
```

### Check Indexes
```sql
-- List all indexes
SELECT tablename, indexname FROM pg_indexes;
```

### Monitor Disk Usage
```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## API Rate Limiting Considerations

- Twitter API v2: 300-450 requests per 15 minutes (varies by endpoint)
- Batch requests: Retrieve multiple fields using expansions
- Pagination: Use `next_token` for efficient pagination
- Data freshness: Balance between API quota and data recency

## Next Steps

1. **Read** [SCHEMA_DOCUMENTATION.md](SCHEMA_DOCUMENTATION.md) for table details
2. **Study** [ETL_EXAMPLES.md](ETL_EXAMPLES.md) for data loading patterns
3. **Configure** Twitter API credentials in `.env`
4. **Build** your data pipeline using provided ETL examples
5. **Monitor** ingestion runs via `ingestion_runs` table
