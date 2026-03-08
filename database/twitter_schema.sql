-- ============================================================================
-- Twitter/X Data Ingestion Schema
-- Fully normalized relational schema for storing Twitter API v2 data
-- ============================================================================

-- ============================================================================
-- 1. USERS TABLE
-- Represents Twitter accounts (authors, mentioned users, etc.)
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id                BIGINT PRIMARY KEY,
    username               VARCHAR(50) NOT NULL,
    name                   VARCHAR(100),
    description            TEXT,
    location               VARCHAR(255),
    url                    TEXT,
    created_at             TIMESTAMP WITH TIME ZONE,
    verified               BOOLEAN DEFAULT FALSE,
    protected              BOOLEAN DEFAULT FALSE,
    followers_count        INTEGER DEFAULT 0,
    following_count        INTEGER DEFAULT 0,
    tweet_count            INTEGER DEFAULT 0,
    listed_count           INTEGER DEFAULT 0,
    profile_image_url      TEXT,
    raw_language           VARCHAR(10),
    last_seen_at           TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT username_not_empty CHECK (LENGTH(username) > 0)
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);


-- ============================================================================
-- 2. TWEETS TABLE
-- Represents each tweet ingested from the API
-- ============================================================================
CREATE TABLE IF NOT EXISTS tweets (
    tweet_id               BIGINT PRIMARY KEY,
    author_id              BIGINT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    conversation_id        BIGINT,
    in_reply_to_tweet_id   BIGINT,
    in_reply_to_user_id    BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
    created_at             TIMESTAMP WITH TIME ZONE NOT NULL,
    text                   TEXT NOT NULL,
    lang                   VARCHAR(10),
    
    -- Tweet classification flags
    is_retweet             BOOLEAN NOT NULL DEFAULT FALSE,
    is_quote               BOOLEAN NOT NULL DEFAULT FALSE,
    is_reply               BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Content sensitivity
    possibly_sensitive     BOOLEAN DEFAULT FALSE,
    
    -- Engagement metrics
    like_count             INTEGER DEFAULT 0,
    quote_count            INTEGER DEFAULT 0,
    reply_count            INTEGER DEFAULT 0,
    retweet_count          INTEGER DEFAULT 0,
    bookmark_count         INTEGER DEFAULT 0,
    
    -- Source information
    source                 VARCHAR(255),
    
    -- Geo data (flattened for efficient querying)
    place_id               VARCHAR(64),
    coordinates_lat        DOUBLE PRECISION,
    coordinates_lon        DOUBLE PRECISION,
    
    -- Metadata
    inserted_at            TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at             TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT text_not_empty CHECK (LENGTH(TRIM(text)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_tweets_author_id ON tweets(author_id);
CREATE INDEX IF NOT EXISTS idx_tweets_created_at ON tweets(created_at);
CREATE INDEX IF NOT EXISTS idx_tweets_conversation_id ON tweets(conversation_id);
CREATE INDEX IF NOT EXISTS idx_tweets_in_reply_to_tweet_id ON tweets(in_reply_to_tweet_id);
CREATE INDEX IF NOT EXISTS idx_tweets_lang ON tweets(lang);
CREATE INDEX IF NOT EXISTS idx_tweets_inserted_at ON tweets(inserted_at);
CREATE INDEX IF NOT EXISTS idx_tweets_is_retweet ON tweets(is_retweet) WHERE is_retweet = TRUE;
CREATE INDEX IF NOT EXISTS idx_tweets_is_quote ON tweets(is_quote) WHERE is_quote = TRUE;
CREATE INDEX IF NOT EXISTS idx_tweets_is_reply ON tweets(is_reply) WHERE is_reply = TRUE;


-- ============================================================================
-- 3. TWEET RELATIONSHIPS TABLE
-- Models retweets, quotes, and replies (relationships between tweets)
-- ============================================================================
CREATE TABLE IF NOT EXISTS tweet_relationships (
    tweet_id               BIGINT NOT NULL REFERENCES tweets(tweet_id) ON DELETE CASCADE,
    related_tweet_id       BIGINT NOT NULL REFERENCES tweets(tweet_id) ON DELETE CASCADE,
    relation_type          VARCHAR(20) NOT NULL,
    created_at             TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (tweet_id, related_tweet_id, relation_type),
    
    CONSTRAINT relation_type_valid CHECK (relation_type IN ('retweet', 'quote', 'reply'))
);

CREATE INDEX IF NOT EXISTS idx_tweet_relationships_related_tweet ON tweet_relationships(related_tweet_id);
CREATE INDEX IF NOT EXISTS idx_tweet_relationships_type ON tweet_relationships(relation_type);


-- ============================================================================
-- 4. HASHTAGS TABLE
-- Stores unique hashtags
-- ============================================================================
CREATE TABLE IF NOT EXISTS hashtags (
    hashtag_id             BIGSERIAL PRIMARY KEY,
    tag                    VARCHAR(255) UNIQUE NOT NULL,
    
    CONSTRAINT hashtag_not_empty CHECK (LENGTH(TRIM(tag)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_hashtags_tag ON hashtags(tag);


-- ============================================================================
-- 5. TWEET-HASHTAGS MAPPING
-- Maps tweets to the hashtags they contain
-- ============================================================================
CREATE TABLE IF NOT EXISTS tweet_hashtags (
    tweet_id               BIGINT NOT NULL REFERENCES tweets(tweet_id) ON DELETE CASCADE,
    hashtag_id             BIGINT NOT NULL REFERENCES hashtags(hashtag_id) ON DELETE RESTRICT,
    position               INTEGER,
    
    PRIMARY KEY (tweet_id, hashtag_id)
);

CREATE INDEX IF NOT EXISTS idx_tweet_hashtags_hashtag_id ON tweet_hashtags(hashtag_id);


-- ============================================================================
-- 6. MENTIONS TABLE
-- Stores users mentioned in tweets
-- ============================================================================
CREATE TABLE IF NOT EXISTS tweet_mentions (
    tweet_id               BIGINT NOT NULL REFERENCES tweets(tweet_id) ON DELETE CASCADE,
    mentioned_user_id      BIGINT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    position               INTEGER,
    
    PRIMARY KEY (tweet_id, mentioned_user_id)
);

CREATE INDEX IF NOT EXISTS idx_tweet_mentions_mentioned_user_id ON tweet_mentions(mentioned_user_id);


-- ============================================================================
-- 7. URLS TABLE
-- Stores unique URLs with metadata
-- ============================================================================
CREATE TABLE IF NOT EXISTS urls (
    url_id                 BIGSERIAL PRIMARY KEY,
    expanded_url           TEXT NOT NULL,
    display_url            TEXT,
    domain                 VARCHAR(255),
    created_at             TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT url_not_empty CHECK (LENGTH(TRIM(expanded_url)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_urls_expanded_url ON urls(expanded_url(255));
CREATE INDEX IF NOT EXISTS idx_urls_domain ON urls(domain);


-- ============================================================================
-- 8. TWEET-URLS MAPPING
-- Maps tweets to the URLs they contain
-- ============================================================================
CREATE TABLE IF NOT EXISTS tweet_urls (
    tweet_id               BIGINT NOT NULL REFERENCES tweets(tweet_id) ON DELETE CASCADE,
    url_id                 BIGINT NOT NULL REFERENCES urls(url_id) ON DELETE RESTRICT,
    position               INTEGER,
    
    PRIMARY KEY (tweet_id, url_id)
);

CREATE INDEX IF NOT EXISTS idx_tweet_urls_url_id ON tweet_urls(url_id);


-- ============================================================================
-- 9. MEDIA TABLE
-- Stores media metadata (photos, videos, GIFs)
-- ============================================================================
CREATE TABLE IF NOT EXISTS media (
    media_key              VARCHAR(100) PRIMARY KEY,
    media_type             VARCHAR(20) NOT NULL,
    url                    TEXT,
    preview_image_url      TEXT,
    width                  INTEGER,
    height                 INTEGER,
    duration_ms            INTEGER,
    alt_text               TEXT,
    created_at             TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT media_type_valid CHECK (media_type IN ('photo', 'video', 'animated_gif'))
);

CREATE INDEX IF NOT EXISTS idx_media_media_type ON media(media_type);


-- ============================================================================
-- 10. TWEET-MEDIA MAPPING
-- Maps tweets to the media they contain
-- ============================================================================
CREATE TABLE IF NOT EXISTS tweet_media (
    tweet_id               BIGINT NOT NULL REFERENCES tweets(tweet_id) ON DELETE CASCADE,
    media_key              VARCHAR(100) NOT NULL REFERENCES media(media_key) ON DELETE RESTRICT,
    position               INTEGER,
    
    PRIMARY KEY (tweet_id, media_key)
);

CREATE INDEX IF NOT EXISTS idx_tweet_media_media_key ON tweet_media(media_key);


-- ============================================================================
-- 11. PLACES TABLE
-- Stores geographic location data from tweets
-- ============================================================================
CREATE TABLE IF NOT EXISTS places (
    place_id               VARCHAR(64) PRIMARY KEY,
    full_name              VARCHAR(255),
    name                   VARCHAR(255),
    place_type             VARCHAR(50),
    country                VARCHAR(100),
    country_code           VARCHAR(10),
    geo_bbox               TEXT,
    created_at             TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_places_country ON places(country);
CREATE INDEX IF NOT EXISTS idx_places_country_code ON places(country_code);


-- ============================================================================
-- 12. INGESTION RUNS TABLE
-- Tracks API ingestion jobs and their outcomes
-- ============================================================================
CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id                 BIGSERIAL PRIMARY KEY,
    started_at             TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at            TIMESTAMP WITH TIME ZONE,
    query                  TEXT,
    endpoint               TEXT NOT NULL,
    result_count           INTEGER DEFAULT 0,
    status                 VARCHAR(20) NOT NULL,
    error_message          TEXT,
    
    CONSTRAINT status_valid CHECK (status IN ('success', 'partial', 'running', 'error'))
);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_started_at ON ingestion_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_status ON ingestion_runs(status);


-- ============================================================================
-- 13. TWEET-INGESTION MAPPING
-- Links tweets to the ingestion runs that brought them in
-- ============================================================================
CREATE TABLE IF NOT EXISTS tweet_ingestion (
    run_id                 BIGINT NOT NULL REFERENCES ingestion_runs(run_id) ON DELETE RESTRICT,
    tweet_id               BIGINT NOT NULL REFERENCES tweets(tweet_id) ON DELETE CASCADE,
    
    PRIMARY KEY (run_id, tweet_id)
);

CREATE INDEX IF NOT EXISTS idx_tweet_ingestion_tweet_id ON tweet_ingestion(tweet_id);


-- ============================================================================
-- ANALYTICS/AGGREGATION TABLES (Optional but useful)
-- ============================================================================

-- Daily tweet counts by user
CREATE TABLE IF NOT EXISTS user_daily_stats (
    user_id                BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    date                   DATE NOT NULL,
    tweet_count            INTEGER DEFAULT 0,
    retweet_count          INTEGER DEFAULT 0,
    quote_count            INTEGER DEFAULT 0,
    reply_count            INTEGER DEFAULT 0,
    total_likes_received   INTEGER DEFAULT 0,
    total_retweets_received INTEGER DEFAULT 0,
    
    PRIMARY KEY (user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_user_daily_stats_date ON user_daily_stats(date);


-- Hashtag trending statistics
CREATE TABLE IF NOT EXISTS hashtag_daily_stats (
    hashtag_id             BIGINT NOT NULL REFERENCES hashtags(hashtag_id) ON DELETE CASCADE,
    date                   DATE NOT NULL,
    mention_count          INTEGER DEFAULT 0,
    unique_users           INTEGER DEFAULT 0,
    engagement_count       INTEGER DEFAULT 0,
    
    PRIMARY KEY (hashtag_id, date)
);

CREATE INDEX IF NOT EXISTS idx_hashtag_daily_stats_date ON hashtag_daily_stats(date);
