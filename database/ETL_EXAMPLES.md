# Twitter Data ETL Examples

This document provides practical Python/SQL examples for loading Twitter API v2 data into the schema.

## Python ETL Module Example

```python
"""
twitter_etl.py - ETL module for loading Twitter data into PostgreSQL
"""

import psycopg2
from datetime import datetime
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TwitterETL:
    def __init__(self, db_host: str, db_name: str, db_user: str, db_password: str):
        """Initialize database connection"""
        self.conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password
        )
        self.cur = self.conn.cursor()

    def insert_user(self, user_data: Dict) -> bool:
        """Insert or update a user"""
        try:
            self.cur.execute("""
                INSERT INTO users (
                    user_id, username, name, description, location, url,
                    created_at, verified, protected, followers_count,
                    following_count, tweet_count, listed_count, 
                    profile_image_url, raw_language, last_seen_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    followers_count = EXCLUDED.followers_count,
                    following_count = EXCLUDED.following_count,
                    tweet_count = EXCLUDED.tweet_count,
                    listed_count = EXCLUDED.listed_count,
                    last_seen_at = NOW()
            """, (
                user_data['id'],
                user_data['username'],
                user_data.get('name'),
                user_data.get('description'),
                user_data.get('location'),
                user_data.get('url'),
                user_data.get('created_at'),
                user_data.get('verified', False),
                user_data.get('protected', False),
                user_data.get('public_metrics', {}).get('followers_count', 0),
                user_data.get('public_metrics', {}).get('following_count', 0),
                user_data.get('public_metrics', {}).get('tweet_count', 0),
                user_data.get('public_metrics', {}).get('listed_count', 0),
                user_data.get('profile_image_url'),
                user_data.get('lang'),
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error inserting user {user_data.get('id')}: {e}")
            self.conn.rollback()
            return False

    def insert_tweet(self, tweet_data: Dict) -> bool:
        """Insert or update a tweet"""
        try:
            # Extract engagement counts
            public_metrics = tweet_data.get('public_metrics', {})
            
            self.cur.execute("""
                INSERT INTO tweets (
                    tweet_id, author_id, conversation_id, in_reply_to_tweet_id,
                    in_reply_to_user_id, created_at, text, lang, 
                    is_retweet, is_quote, is_reply, possibly_sensitive,
                    like_count, quote_count, reply_count, retweet_count,
                    bookmark_count, source, place_id, coordinates_lat,
                    coordinates_lon
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tweet_id) DO UPDATE SET
                    like_count = EXCLUDED.like_count,
                    quote_count = EXCLUDED.quote_count,
                    reply_count = EXCLUDED.reply_count,
                    retweet_count = EXCLUDED.retweet_count,
                    bookmark_count = EXCLUDED.bookmark_count,
                    updated_at = NOW()
            """, (
                tweet_data['id'],
                tweet_data['author_id'],
                tweet_data.get('conversation_id'),
                tweet_data.get('in_reply_to_user_id'),  # Fix: get reply tweet id from context
                tweet_data.get('in_reply_to_user_id'),
                tweet_data['created_at'],
                tweet_data['text'],
                tweet_data.get('lang'),
                'retweeted' in str(tweet_data.get('referenced_tweets', [])),
                'quoted' in str(tweet_data.get('referenced_tweets', [])),
                tweet_data.get('in_reply_to_user_id') is not None,
                tweet_data.get('possibly_sensitive', False),
                public_metrics.get('like_count', 0),
                public_metrics.get('quote_count', 0),
                public_metrics.get('reply_count', 0),
                public_metrics.get('retweet_count', 0),
                public_metrics.get('bookmark_count', 0),
                tweet_data.get('source'),
                tweet_data.get('geo', {}).get('place_id'),
                tweet_data.get('geo', {}).get('coordinates', {}).get('latitude'),
                tweet_data.get('geo', {}).get('coordinates', {}).get('longitude'),
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error inserting tweet {tweet_data.get('id')}: {e}")
            self.conn.rollback()
            return False

    def insert_hashtags(self, tweet_id: int, hashtags: List[Dict]) -> bool:
        """Insert hashtags and link to tweet"""
        try:
            for position, hashtag in enumerate(hashtags):
                tag = hashtag['tag'].lower()
                
                # Insert hashtag
                self.cur.execute(
                    "INSERT INTO hashtags (tag) VALUES (%s) ON CONFLICT DO NOTHING",
                    (tag,)
                )
                
                # Get hashtag ID
                self.cur.execute("SELECT hashtag_id FROM hashtags WHERE tag = %s", (tag,))
                hashtag_id = self.cur.fetchone()
                
                if hashtag_id:
                    # Link to tweet
                    self.cur.execute("""
                        INSERT INTO tweet_hashtags (tweet_id, hashtag_id, position)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (tweet_id, hashtag_id[0], position))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error inserting hashtags for tweet {tweet_id}: {e}")
            self.conn.rollback()
            return False

    def insert_mentions(self, tweet_id: int, mentions: List[Dict]) -> bool:
        """Insert user mentions for a tweet"""
        try:
            for position, mention in enumerate(mentions):
                self.cur.execute("""
                    INSERT INTO tweet_mentions (tweet_id, mentioned_user_id, position)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (tweet_id, mention['id'], position))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error inserting mentions for tweet {tweet_id}: {e}")
            self.conn.rollback()
            return False

    def insert_urls(self, tweet_id: int, urls: List[Dict]) -> bool:
        """Insert URLs and link to tweet"""
        try:
            for position, url_data in enumerate(urls):
                expanded_url = url_data.get('expanded_url', '')
                display_url = url_data.get('display_url', '')
                
                # Extract domain from URL
                from urllib.parse import urlparse
                domain = urlparse(expanded_url).netloc
                
                # Insert URL
                self.cur.execute("""
                    INSERT INTO urls (expanded_url, display_url, domain)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (expanded_url) DO NOTHING
                """, (expanded_url, display_url, domain))
                
                # Get URL ID
                self.cur.execute(
                    "SELECT url_id FROM urls WHERE expanded_url = %s",
                    (expanded_url,)
                )
                url_id = self.cur.fetchone()
                
                if url_id:
                    # Link to tweet
                    self.cur.execute("""
                        INSERT INTO tweet_urls (tweet_id, url_id, position)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (tweet_id, url_id[0], position))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error inserting URLs for tweet {tweet_id}: {e}")
            self.conn.rollback()
            return False

    def insert_media(self, tweet_id: int, media_list: List[Dict]) -> bool:
        """Insert media attachments and link to tweet"""
        try:
            for position, media in enumerate(media_list):
                media_key = media['media_key']
                media_type = media['type']  # 'photo', 'video', 'animated_gif'
                
                self.cur.execute("""
                    INSERT INTO media (
                        media_key, media_type, url, preview_image_url,
                        width, height, duration_ms, alt_text
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (media_key) DO NOTHING
                """, (
                    media_key,
                    media_type,
                    media.get('url'),
                    media.get('preview_image_url'),
                    media.get('width'),
                    media.get('height'),
                    media.get('duration_ms'),
                    media.get('alt_text'),
                ))
                
                # Link to tweet
                self.cur.execute("""
                    INSERT INTO tweet_media (tweet_id, media_key, position)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (tweet_id, media_key, position))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error inserting media for tweet {tweet_id}: {e}")
            self.conn.rollback()
            return False

    def process_api_response(self, response: Dict) -> bool:
        """Process a complete Twitter API v2 response"""
        try:
            logger.info("Processing API response...")
            
            # Start ingestion run
            self.cur.execute("""
                INSERT INTO ingestion_runs (started_at, endpoint, status)
                VALUES (NOW(), %s, 'running')
                RETURNING run_id
            """, ("search_endpoint",))
            run_id = self.cur.fetchone()[0]
            self.conn.commit()
            
            # Process users
            if 'includes' in response and 'users' in response['includes']:
                for user in response['includes']['users']:
                    self.insert_user(user)
            
            # Process tweets
            if 'data' in response:
                for tweet in response['data']:
                    self.insert_tweet(tweet)
                    self.cur.execute("""
                        INSERT INTO tweet_ingestion (run_id, tweet_id)
                        VALUES (%s, %s)
                    """, (run_id, tweet['id']))
                    
                    # Process tweet entities
                    if 'entities' in tweet:
                        entities = tweet['entities']
                        if 'hashtags' in entities:
                            self.insert_hashtags(tweet['id'], entities['hashtags'])
                        if 'mentions' in entities:
                            self.insert_mentions(tweet['id'], entities['mentions'])
                        if 'urls' in entities:
                            self.insert_urls(tweet['id'], entities['urls'])
                    
                    if 'attachments' in tweet and 'media_keys' in tweet['attachments']:
                        # Process media  (needs proper media objects from includes)
                        pass
            
            # Mark run as complete
            self.cur.execute("""
                UPDATE ingestion_runs SET
                    finished_at = NOW(),
                    result_count = %s,
                    status = 'success'
                WHERE run_id = %s
            """, (len(response.get('data', [])), run_id))
            self.conn.commit()
            
            logger.info(f"Successfully processed response. Run ID: {run_id}")
            return True
        except Exception as e:
            logger.error(f"Error processing API response: {e}")
            self.conn.rollback()
            return False

    def close(self):
        """Close database connection"""
        self.cur.close()
        self.conn.close()


# Usage Example
if __name__ == "__main__":
    etl = TwitterETL(
        db_host="localhost",
        db_name="twitter_data",
        db_user="postgres",
        db_password="password"
    )
    
    # Load from API response (example)
    api_response = {
        "data": [...],
        "includes": {"users": [...]}
    }
    
    etl.process_api_response(api_response)
    etl.close()
```

## SQL Bulk Insert Example

For high-performance bulk inserts with PostgreSQL COPY:

```sql
-- Load users from CSV
\COPY users (user_id, username, name, followers_count) 
FROM '/tmp/users.csv' 
WITH (FORMAT CSV, HEADER, DELIMITER ',');

-- Load tweets from CSV
\COPY tweets (
    tweet_id, author_id, created_at, text, lang,
    like_count, retweet_count, quote_count, reply_count
) FROM '/tmp/tweets.csv' 
WITH (FORMAT CSV, HEADER, DELIMITER ',');
```

## Real-time Ingestion Pattern

```python
import tweepy
from datetime import datetime, timedelta

class TwitterStreamListener(tweepy.StreamListener):
    def __init__(self, etl: TwitterETL):
        self.etl = etl
        super().__init__()

    def on_data(self, raw_data):
        """Handle incoming tweets"""
        tweet = json.loads(raw_data)
        self.etl.insert_tweet(tweet)
        return True

    def on_error(self, status):
        logger.error(f"Stream error: {status}")
        return False


# Usage
listener = TwitterStreamListener(etl)
stream = tweepy.Stream(auth=auth, listener=listener)

# Filter stream for terms
stream.filter(track=['cryptocurrency', 'bitcoin'])
```

## Batch Query Example

```python
# Find trending hashtags in the last 24 hours
def get_trending_hashtags(etl: TwitterETL, hours: int = 24) -> List[Dict]:
    query = """
        SELECT 
            h.tag,
            COUNT(th.tweet_id) as usage_count,
            COUNT(DISTINCT t.author_id) as unique_users,
            AVG(t.like_count + t.retweet_count + t.quote_count) as avg_engagement
        FROM hashtags h
        JOIN tweet_hashtags th ON h.hashtag_id = th.hashtag_id
        JOIN tweets t ON th.tweet_id = t.tweet_id
        WHERE t.created_at > NOW() - INTERVAL '%d hours'
        GROUP BY h.hashtag_id, h.tag
        ORDER BY usage_count DESC
        LIMIT 100
    """ % hours
    
    etl.cur.execute(query)
    return etl.cur.fetchall()
```

