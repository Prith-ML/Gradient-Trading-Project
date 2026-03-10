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
