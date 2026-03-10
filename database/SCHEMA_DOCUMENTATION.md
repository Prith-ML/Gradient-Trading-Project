# Twitter/X Data Schema Documentation

## Overview

Fully normalized relational schema for ingesting and storing Twitter/X data from API v2. No JSON blobs; each entity has its own table for efficient querying and analysis.

## Design Principles

1. **Normalization**: Each logical entity has its own table
2. **Relational Integrity**: Foreign keys enforce consistency
3. **Queryability**: Indexes on frequently queried columns
4. **Auditability**: `ingestion_runs` and `tweet_ingestion` track data provenance

## Core Tables

| Table | Purpose |
|-------|---------|
| `users` | Twitter user profiles and metrics |
| `tweets` | Tweet content, metadata, engagement |
| `tweet_relationships` | Retweets, quotes, replies |
| `hashtags` / `tweet_hashtags` | Hashtag tracking |
| `tweet_mentions` | User mentions |
| `urls` / `tweet_urls` | Links and domains |
| `media` / `tweet_media` | Images, videos, GIFs |
| `places` | Geographic locations |
| `ingestion_runs` | API run tracking |
| `tweet_ingestion` | Links tweets to runs |

## Entity Relationship Summary

```
users ──< tweets ──< tweet_hashtags >── hashtags
  │          │
  │          ├──< tweet_mentions
  │          ├──< tweet_urls >── urls
  │          ├──< tweet_media >── media
  │          ├──< tweet_relationships (self-ref)
  │          └──< tweet_ingestion >── ingestion_runs
  │
  └── places (via tweets.place_id)
```

## Example Queries

**Trending hashtags (24h):**
```sql
SELECT h.tag, COUNT(th.tweet_id) AS usage_count
FROM hashtags h
JOIN tweet_hashtags th ON h.hashtag_id = th.hashtag_id
JOIN tweets t ON th.tweet_id = t.tweet_id
WHERE t.created_at > NOW() - INTERVAL '24 hours'
GROUP BY h.tag
ORDER BY usage_count DESC
LIMIT 50;
```

**Top tweets by engagement:**
```sql
SELECT tweet_id, text, like_count, retweet_count
FROM tweets
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY (like_count + retweet_count) DESC
LIMIT 100;
```

## Storage Estimates

| Tweets | Approx. Storage |
|--------|-----------------|
| 100k | ~150 MB |
| 500k | ~700 MB – 1.2 GB |
| 1M | ~1.5 GB |
