# Twitter/X Data Schema Documentation

## Overview

This document describes the complete relational database schema for ingesting and storing Twitter/X data from the Twitter API v2. The schema is **fully normalized** with no JSON blobs, ensuring efficient querying, joining, and analysis.

## Design Principles

1. **Normalization**: Each logical entity has its own table
2. **Relational Integrity**: Foreign keys enforce data consistency
3. **Queryability**: Easy joins between related entities
4. **Scalability**: Proper indexing on frequently queried columns
5. **Auditability**: Timestamps track data ingestion and updates

## Core Tables

### 1. Users Table
**Purpose**: Stores Twitter user profiles

**Key Fields**:
- `user_id` (BIGINT): Twitter's numeric user ID (primary key)
- `username`: @handle (unique, indexed)
- `name`: Display name
- `followers_count`, `following_count`, `tweet_count`: Engagement metrics
- `verified`, `protected`: Account status flags
- `created_at`: Account creation date
- `last_seen_at`: When this user was last encountered

**Indexes**:
- `username`: For quick user lookups by handle
- `created_at`: For temporal analysis

**Query Examples**:
```sql
-- Find most-followed users
SELECT username, followers_count FROM users 
ORDER BY followers_count DESC LIMIT 100;

-- Find verified accounts tweeting recently
SELECT * FROM users WHERE verified = TRUE AND last_seen_at > NOW() - INTERVAL '7 days';
```

---

### 2. Tweets Table
**Purpose**: Core table storing all tweet content and metadata

**Key Fields**:
- `tweet_id` (BIGINT): Twitter's numeric tweet ID
- `author_id`: Foreign key to `users` table
- `text`: Full tweet content
- `created_at`: Tweet publication timestamp
- Classification flags:
  - `is_retweet`: Indicates if this is a retweet
  - `is_quote`: Indicates if this is a quote tweet
  - `is_reply`: Indicates if this is a reply
- `conversation_id`: Root tweet ID in a thread
- `in_reply_to_tweet_id`, `in_reply_to_user_id`: Reply chain tracking
- Engagement metrics:
  - `like_count`, `retweet_count`, `quote_count`, `reply_count`, `bookmark_count`
- `lang`: Language code (BCP 47)
- `source`: Client app (e.g., "Twitter Web App")
- Geo data:
  - `place_id`: References places table
  - `coordinates_lat`, `coordinates_lon`: Numeric coordinates for efficient range queries
- `possibly_sensitive`: Content warning flag

**Indexes**:
- `author_id`: Find tweets by user
- `created_at`: Temporal queries
- `conversation_id`: Thread reconstruction
- `in_reply_to_tweet_id`: Reply chain traversal
- `lang`: Language-specific analysis
- `is_retweet`, `is_quote`, `is_reply`: Partial indexes on popular filters

**Query Examples**:
```sql
-- Find tweets in a conversation thread
SELECT * FROM tweets WHERE conversation_id = ? ORDER BY created_at;

-- Find top tweets by engagement (last 7 days)
SELECT * FROM tweets 
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY (like_count + retweet_count + quote_count) DESC LIMIT 50;

-- Find tweets by language
SELECT * FROM tweets WHERE lang = 'en' AND created_at > NOW() - INTERVAL '24 hours';
```

---

### 3. Tweet Relationships Table
**Purpose**: Models complex relationships between tweets (retweets, quotes, replies)

**Key Fields**:
- `tweet_id`: The tweet that has a relationship
- `related_tweet_id`: The related tweet
- `relation_type`: One of `'retweet'`, `'quote'`, `'reply'`

**Use Cases**:
- Track all retweets of a specific tweet
- Find all quotes commenting on a tweet
- Reconstruct reply chains with multiple ancestors

**Query Examples**:
```sql
-- Find all retweets of a specific tweet
SELECT t.tweet_id, u.username, t.created_at
FROM tweet_relationships tr
JOIN tweets t ON tr.tweet_id = t.tweet_id
JOIN users u ON t.author_id = u.user_id
WHERE tr.related_tweet_id = ? AND tr.relation_type = 'retweet';

-- Find all quote tweets on a thread
SELECT DISTINCT tr.tweet_id FROM tweet_relationships tr
WHERE tr.related_tweet_id = ? AND tr.relation_type = 'quote';
```

---

### 4. Hashtags & Tweet-Hashtags
**Purpose**: Store and map unique hashtags to tweets

**Structure**:
- `hashtags` table: Unique hashtags (normalized to lowercase)
- `tweet_hashtags`: Many-to-many mapping with optional position

**Why Separate?**
- Avoid storing hashtags as text in tweets (not queryable)
- Track hashtag frequency and trends
- Avoid duplicates (case-insensitive)

**Query Examples**:
```sql
-- Find tweets using a specific hashtag
SELECT t.* FROM tweets t
JOIN tweet_hashtags th ON t.tweet_id = th.tweet_id
JOIN hashtags h ON th.hashtag_id = h.hashtag_id
WHERE h.tag = 'cryptocurrency';

-- Count hashtag usage
SELECT h.tag, COUNT(th.tweet_id) as usage_count
FROM hashtags h
LEFT JOIN tweet_hashtags th ON h.hashtag_id = th.hashtag_id
GROUP BY h.tag ORDER BY usage_count DESC LIMIT 100;
```

---

### 5. Mentions & Tweet-Mentions
**Purpose**: Track which users are mentioned in each tweet

**Structure**:
- `tweet_mentions`: Maps tweets to mentioned users with optional position

**Query Examples**:
```sql
-- Find all mentions of a specific user
SELECT t.tweet_id, u.username, t.text, t.created_at
FROM tweet_mentions tm
JOIN tweets t ON tm.tweet_id = t.tweet_id
JOIN users u ON t.author_id = u.user_id
WHERE tm.mentioned_user_id = ? 
ORDER BY t.created_at DESC;

-- Find users mentioned most frequently
SELECT u.username, COUNT(*) as mention_count
FROM tweet_mentions tm
JOIN users u ON tm.mentioned_user_id = u.user_id
GROUP BY u.user_id ORDER BY mention_count DESC LIMIT 50;
```

---

### 6. URLs & Tweet-URLs
**Purpose**: Store and map URLs found in tweets

**Structure**:
- `urls` table: Unique URLs with expanded form and domain
- `tweet_urls`: Many-to-many mapping with position

**Fields**:
- `expanded_url`: Full URL (for deduplication)
- `display_url`: Shortened display version
- `domain`: Extracted domain (useful for domain-level analysis)

**Query Examples**:
```sql
-- Find tweets sharing a specific URL
SELECT DISTINCT t.* FROM tweets t
JOIN tweet_urls tu ON t.tweet_id = tu.tweet_id
JOIN urls u ON tu.url_id = u.url_id
WHERE u.expanded_url = ?;

-- Find most-shared domains
SELECT u.domain, COUNT(tu.tweet_id) as share_count
FROM urls u
JOIN tweet_urls tu ON u.url_id = tu.url_id
GROUP BY u.url_id ORDER BY share_count DESC LIMIT 50;
```

---

### 7. Media & Tweet-Media
**Purpose**: Store metadata for images, videos, and GIFs

**Structure**:
- `media` table: Unique media items with type and dimensions
- `tweet_media`: Many-to-many mapping with position

**Media Types**:
- `'photo'`: Static image
- `'video'`: Video content
- `'animated_gif'`: GIF (technically a video)

**Fields**:
- `media_key`: Twitter's media identifier
- `url`, `preview_image_url`: Media URLs
- `width`, `height`: Dimensions
- `duration_ms`: Video/GIF duration
- `alt_text`: Accessibility description

**Query Examples**:
```sql
-- Find all tweets with video media
SELECT DISTINCT t.* FROM tweets t
JOIN tweet_media tm ON t.tweet_id = tm.tweet_id
JOIN media m ON tm.media_key = m.media_key
WHERE m.media_type = 'video';

-- Count media types
SELECT m.media_type, COUNT(tm.tweet_id) as tweet_count
FROM media m
JOIN tweet_media tm ON m.media_key = tm.media_key
GROUP BY m.media_type;
```

---

### 8. Places Table
**Purpose**: Store geographic location information

**Fields**:
- `place_id`: Twitter's place ID
- `full_name`, `name`: Location names
- `place_type`: City, region, country, etc.
- `country`, `country_code`: Country information
- `geo_bbox`: Bounding box (text) for the place

**Query Examples**:
```sql
-- Find tweets from a specific country
SELECT t.* FROM tweets t
JOIN places p ON t.place_id = p.place_id
WHERE p.country_code = 'US' AND t.created_at > NOW() - INTERVAL '24 hours';

-- Count tweets by country
SELECT p.country, COUNT(t.tweet_id) as tweet_count
FROM tweets t
JOIN places p ON t.place_id = p.place_id
GROUP BY p.country ORDER BY tweet_count DESC;
```

---

### 9. Ingestion Runs Table
**Purpose**: Track API calls and data pipeline execution

**Fields**:
- `run_id`: Unique run identifier
- `started_at`, `finished_at`: Execution timeline
- `endpoint`: API endpoint called (e.g., `/2/tweets/search/recent`)
- `query`: Search parameters or query string
- `result_count`: Number of results retrieved
- `status`: `'success'`, `'partial'`, `'running'`, or `'error'`
- `error_message`: Details if status is `'error'`

**Use Cases**:
- Debug failed ingestions
- Calculate data freshness
- Replay specific queries
- Monitor API usage

**Query Examples**:
```sql
-- Find recent successful runs
SELECT * FROM ingestion_runs 
WHERE status = 'success' AND started_at > NOW() - INTERVAL '24 hours'
ORDER BY started_at DESC;

-- Find failed runs requiring investigation
SELECT * FROM ingestion_runs 
WHERE status = 'error' ORDER BY started_at DESC LIMIT 20;
```

---

### 10. Tweet-Ingestion Mapping Table
**Purpose**: Link tweets to the ingestion runs that imported them

**Use Cases**:
- Determine which tweets were imported in which run
- Re-process tweets from a specific run
- Calculate coverage across runs

**Query Examples**:
```sql
-- Find all tweets from a specific ingestion run
SELECT t.* FROM tweet_ingestion ti
JOIN tweets t ON ti.tweet_id = t.tweet_id
WHERE ti.run_id = ?;

-- Count how many tweets were imported in each run
SELECT ti.run_id, COUNT(*) as tweet_count
FROM tweet_ingestion ti
GROUP BY ti.run_id;
```

---

## Analytics/Aggregation Tables

### 11. User Daily Stats
**Purpose**: Pre-aggregated daily statistics by user

**Use**: Faster queries for user analytics without scanning millions of tweets

**Query Examples**:
```sql
-- Get user's tweeting trend over last 30 days
SELECT date, tweet_count, total_likes_received
FROM user_daily_stats
WHERE user_id = ? AND date >= NOW()::DATE - INTERVAL '30 days'
ORDER BY date;
```

### 12. Hashtag Daily Stats
**Purpose**: Pre-aggregated daily statistics by hashtag

**Use**: Trending hashtag analysis

**Query Examples**:
```sql
-- Track hashtag growth over time
SELECT date, mention_count, unique_users
FROM hashtag_daily_stats
WHERE hashtag_id = ? AND date >= NOW()::DATE - INTERVAL '30 days'
ORDER BY date;
```

---

## Data Relationships Overview

```
users
├── one-to-many: tweets (via author_id)
├── one-to-many: tweet_mentions (when mentioned)
└── one-to-many: tweet_relationships (when related)

tweets
├── many-to-one: users (author_id)
├── many-to-one: tweets (in_reply_to_tweet_id, conversation_id)
├── many-to-many: hashtags (via tweet_hashtags)
├── many-to-many: users (via tweet_mentions)
├── many-to-many: urls (via tweet_urls)
├── many-to-many: media (via tweet_media)
├── many-to-many: places (via place_id)
├── many-to-many: ingestion_runs (via tweet_ingestion)
└── one-to-many: tweet_relationships (self-referential)
```

---

## Storage & Performance Considerations

### Partitioning Strategy (for large-scale deployment)

For high-volume deployments, partition the `tweets` and analytics tables by `created_at`:

```sql
-- Partition tweets by month (PostgreSQL example)
CREATE TABLE tweets_2024_01 PARTITION OF tweets
  FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE tweets_2024_02 PARTITION OF tweets
  FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- ... and so on
```

### Storage Estimates

For **1 million tweets**:
- `tweets` table: ~500 MB
- `hashtags` + `tweet_hashtags`: ~50 MB
- `urls` + `tweet_urls`: ~100 MB
- `media` + `tweet_media`: ~30 MB
- `mentions`: ~100 MB
- **Total**: ~800 MB

For **100 million tweets**, expect ~80-100 GB depending on text length and media count.

### Index Strategy

- **Hot Columns**: `created_at`, `author_id`, `lang`, `is_retweet`, `is_quote`, `is_reply`
- **Partial Indexes**: On `is_retweet`, `is_quote`, `is_reply` (many NULLs)
- **Composite Indexes**: Consider `(author_id, created_at)` for user timelines

---

## Data Validation & Constraints

All tables include:
- **NOT NULL constraints** on critical fields
- **CHECK constraints** for enum-like fields (`relation_type`, `status`, `media_type`)
- **FOREIGN KEY constraints** with appropriate cascade policies
- **UNIQUE constraints** to prevent duplicates

---

## Example ETL Query

**Load tweets from API v2 response into schema**:

```sql
-- Step 1: Insert unique users
INSERT INTO users (user_id, username, name, followers_count, created_at)
SELECT id, username, name, public_metrics->followers_count, created_at
FROM json_api_response->'includes'->'users'
ON CONFLICT (user_id) DO UPDATE SET
  followers_count = EXCLUDED.followers_count,
  last_seen_at = NOW();

-- Step 2: Insert tweets and their relationships
INSERT INTO tweets (tweet_id, author_id, text, created_at, lang, is_retweet, is_quote)
SELECT id, author_id, text, created_at, lang, 
       (referenced_tweets @> '[{"type": "retweeted"}]'),
       (referenced_tweets @> '[{"type": "quoted"}]')
FROM json_api_response->'data'
ON CONFLICT (tweet_id) DO UPDATE SET
  like_count = EXCLUDED.like_count,
  retweet_count = EXCLUDED.retweet_count,
  updated_at = NOW();

-- Step 3: Insert hashtags and mappings
INSERT INTO hashtags (tag)
SELECT LOWER(tag) FROM json_api_response->'entities'->'hashtags'
ON CONFLICT DO NOTHING;

INSERT INTO tweet_hashtags (tweet_id, hashtag_id)
SELECT tweet_id, hashtag_id FROM (
  -- Join logic to connect tweets with hashtags
) ON CONFLICT DO NOTHING;
```

---

## Next Steps

1. **Database Setup**: Run `twitter_schema.sql` to create tables
2. **Implement ETL**: Build Python/JavaScript scripts to ingest API data
3. **Add Monitoring**: Instruments to track ingestion health
4. **Schedule Runs**: Cron jobs or task scheduler for continuous ingestion
5. **Query API**: Use provided examples to build analytics
