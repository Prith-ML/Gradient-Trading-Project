# Gradient-Trading-Project

## Overview

A comprehensive trading system leveraging gradient-based optimization and social media signals (Twitter/X) for financial market analysis.

## Project Structure

```
.
├── README.md                          # This file
├── database/                          # Database schema and documentation
│   ├── twitter_schema.sql             # Complete SQL schema for Twitter data
│   ├── SCHEMA_DOCUMENTATION.md        # Detailed schema documentation
│   └── ETL_EXAMPLES.md                # ETL examples and data loading patterns
```

## Database Schema

This project uses a **fully normalized relational database** to store Twitter/X data for market analysis. The schema is designed for:

- **Efficiency**: Optimized queries for common trading analysis patterns
- **Scalability**: Handles millions of tweets with proper indexing
- **Integrity**: Foreign keys and constraints ensure data consistency
- **Auditability**: Tracks data ingestion via ingestion logs

### Core Tables

| Table | Purpose |
|-------|---------|
| `users` | Twitter user profiles and metrics |
| `tweets` | Tweet content and metadata |
| `hashtags` / `tweet_hashtags` | Hashtag tracking and mapping |
| `mentions` / `tweet_mentions` | User mentions within tweets |
| `urls` / `tweet_urls` | Links and domain tracking |
| `media` / `tweet_media` | Images, videos, and GIFs |
| `places` | Geographic location data |
| `tweet_relationships` | Retweets, quotes, and replies |
| `ingestion_runs` | API ingestion pipeline logs |
| `user_daily_stats` | Pre-aggregated user statistics |
| `hashtag_daily_stats` | Pre-aggregated hashtag statistics |

### Key Design Principles

1. **No JSON Blobs**: Each entity has its own table, fully normalized
2. **Relational Integrity**: Foreign keys enforce consistency
3. **Easy Joins**: Simple IDs make querying straightforward
4. **Queryable**: Efficient indexes on frequently queried columns
5. **Scalable**: Partitioning strategy for large datasets

### Quick Start

1. **Create the database schema**:
   ```bash
   psql -U postgres -d twitter_data -f database/twitter_schema.sql
   ```

2. **Review the documentation**:
   - [SCHEMA_DOCUMENTATION.md](database/SCHEMA_DOCUMENTATION.md) - Detailed table descriptions
   - [ETL_EXAMPLES.md](database/ETL_EXAMPLES.md) - Python/SQL examples for data loading

3. **Example Query - Find trending hashtags (24 hours)**:
   ```sql
   SELECT 
       h.tag,
       COUNT(th.tweet_id) as usage_count,
       COUNT(DISTINCT t.author_id) as unique_users,
       AVG(t.like_count + t.retweet_count + t.quote_count) as avg_engagement
   FROM hashtags h
   JOIN tweet_hashtags th ON h.hashtag_id = th.hashtag_id
   JOIN tweets t ON th.tweet_id = t.tweet_id
   WHERE t.created_at > NOW() - INTERVAL '24 hours'
   GROUP BY h.tag
   ORDER BY usage_count DESC
   LIMIT 100;
   ```

## Data Sources

- **Twitter/X API v2**: Real-time tweet ingestion via `tweepy` or direct API calls
- **Provided expansions**: users, media, places, hashtags, mentions, URLs

## Storage & Performance

For **1 million tweets**:
- Estimated storage: ~800 MB
- Efficient queries with strategic indexing
- Support for millions of tweets with proper partitioning

## Next Steps

1. Set up PostgreSQL database
2. Execute `database/twitter_schema.sql`
3. Implement ETL pipeline using examples in [ETL_EXAMPLES.md](database/ETL_EXAMPLES.md)
4. Configure Twitter API v2 credentials
5. Schedule regular ingestion runs
6. Build analytical queries for trading signals