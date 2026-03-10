"""
Twitter/X ETL module for loading API v2 data into PostgreSQL.
Handles users, tweets, hashtags, mentions, URLs, media, and ingestion tracking.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)


class TwitterETL:
    """ETL for Twitter API v2 data into the normalized schema."""

    def __init__(self, db_host: str, db_name: str, db_user: str, db_password: str, db_port: int = 5432):
        """Initialize database connection."""
        self.conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
        )
        self.conn.autocommit = False
        self.cur = self.conn.cursor()

    @staticmethod
    def _parse_id(value: Any) -> Optional[int]:
        """Parse Twitter ID (API returns strings)."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_ts(value: Any) -> Optional[datetime]:
        """Parse ISO timestamp."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            from dateutil import parser
            return parser.parse(value)
        except Exception:
            return None

    def insert_users_batch(self, users: List[Dict]) -> int:
        """Insert or update users in batch."""
        if not users:
            return 0
        inserted = 0
        for u in users:
            try:
                user_id = self._parse_id(u.get("id"))
                if not user_id:
                    continue
                metrics = u.get("public_metrics") or {}
                self.cur.execute(
                    """
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
                    """,
                    (
                        user_id,
                        (u.get("username") or "unknown")[:50],
                        (u.get("name") or "")[:100],
                        u.get("description"),
                        (u.get("location") or "")[:255],
                        u.get("url"),
                        self._parse_ts(u.get("created_at")),
                        u.get("verified", False),
                        u.get("protected", False),
                        metrics.get("followers_count", 0),
                        metrics.get("following_count", 0),
                        metrics.get("tweet_count", 0),
                        metrics.get("listed_count", 0),
                        u.get("profile_image_url"),
                        u.get("lang"),
                    ),
                )
                inserted += 1
            except Exception as e:
                logger.warning("User insert failed for %s: %s", u.get("id"), e)
        self.conn.commit()
        return inserted

    def insert_tweet(
        self,
        tweet: Dict,
        run_id: int,
        users_by_id: Dict[str, Dict],
        places_by_id: Dict[str, Dict],
        media_by_key: Dict[str, Dict],
    ) -> bool:
        """Insert a single tweet and its related entities."""
        try:
            tweet_id = self._parse_id(tweet.get("id"))
            author_id = self._parse_id(tweet.get("author_id"))
            if not tweet_id or not author_id:
                return False

            refs = tweet.get("referenced_tweets") or []
            is_retweet = any(r.get("type") == "retweeted" for r in refs)
            is_quote = any(r.get("type") == "quoted" for r in refs)
            reply_ref = next((r for r in refs if r.get("type") == "replied_to"), None)
            in_reply_to_tweet_id = self._parse_id(reply_ref.get("id")) if reply_ref else None
            in_reply_to_user_id = self._parse_id(tweet.get("in_reply_to_user_id"))

            metrics = tweet.get("public_metrics") or {}
            geo = tweet.get("geo") or {}
            coords_arr = (geo.get("coordinates") or {}).get("coordinates")
            if isinstance(coords_arr, list) and len(coords_arr) >= 2:
                coord_lon, coord_lat = float(coords_arr[0]), float(coords_arr[1])
            else:
                coord_lon, coord_lat = None, None

            text = (tweet.get("text") or "").strip()
            if not text:
                text = "[empty]"

            self.cur.execute(
                """
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
                """,
                (
                    tweet_id,
                    author_id,
                    self._parse_id(tweet.get("conversation_id")),
                    in_reply_to_tweet_id,
                    in_reply_to_user_id,
                    self._parse_ts(tweet.get("created_at")) or datetime.utcnow(),
                    text,
                    (tweet.get("lang") or "")[:10],
                    is_retweet,
                    is_quote,
                    in_reply_to_tweet_id is not None,
                    tweet.get("possibly_sensitive", False),
                    metrics.get("like_count", 0),
                    metrics.get("quote_count", 0),
                    metrics.get("reply_count", 0),
                    metrics.get("retweet_count", 0),
                    metrics.get("bookmark_count", 0),
                    (tweet.get("source") or "")[:255],
                    geo.get("place_id"),
                    coord_lat,
                    coord_lon,
                ),
            )

            self.cur.execute(
                "INSERT INTO tweet_ingestion (run_id, tweet_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (run_id, tweet_id),
            )

            entities = tweet.get("entities") or {}
            if entities.get("hashtags"):
                self._insert_hashtags(tweet_id, entities["hashtags"])
            if entities.get("mentions"):
                self._insert_mentions(tweet_id, entities["mentions"])
            if entities.get("urls"):
                self._insert_urls(tweet_id, entities["urls"])

            media_keys = (tweet.get("attachments") or {}).get("media_keys") or []
            if media_keys and media_by_key:
                self._insert_media(tweet_id, media_keys, media_by_key)

            self.conn.commit()
            return True
        except Exception as e:
            logger.error("Tweet insert failed for %s: %s", tweet.get("id"), e)
            self.conn.rollback()
            return False

    def _insert_hashtags(self, tweet_id: int, hashtags: List[Dict]) -> None:
        """Insert hashtags and link to tweet."""
        for pos, h in enumerate(hashtags):
            tag = (h.get("tag") or "").lower().strip()
            if not tag:
                continue
            self.cur.execute(
                "INSERT INTO hashtags (tag) VALUES (%s) ON CONFLICT (tag) DO NOTHING",
                (tag[:255],),
            )
            self.cur.execute("SELECT hashtag_id FROM hashtags WHERE tag = %s", (tag[:255],))
            row = self.cur.fetchone()
            if row:
                self.cur.execute(
                    "INSERT INTO tweet_hashtags (tweet_id, hashtag_id, position) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (tweet_id, row[0], pos),
                )

    def _insert_mentions(self, tweet_id: int, mentions: List[Dict]) -> None:
        """Insert user mentions."""
        for pos, m in enumerate(mentions):
            uid = self._parse_id(m.get("id"))
            if uid:
                self.cur.execute(
                    "INSERT INTO tweet_mentions (tweet_id, mentioned_user_id, position) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (tweet_id, uid, pos),
                )

    def _insert_urls(self, tweet_id: int, urls: List[Dict]) -> None:
        """Insert URLs and link to tweet."""
        for pos, u in enumerate(urls):
            expanded = (u.get("expanded_url") or u.get("url") or "").strip()
            if not expanded:
                continue
            display = (u.get("display_url") or "")[:255]
            domain = urlparse(expanded).netloc[:255] if expanded else None
            self.cur.execute(
                """
                INSERT INTO urls (expanded_url, display_url, domain)
                VALUES (%s, %s, %s)
                ON CONFLICT (expanded_url) DO NOTHING
                """,
                (expanded[:2048], display, domain),
            )
            self.cur.execute("SELECT url_id FROM urls WHERE expanded_url = %s", (expanded[:2048],))
            row = self.cur.fetchone()
            if row:
                self.cur.execute(
                    "INSERT INTO tweet_urls (tweet_id, url_id, position) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (tweet_id, row[0], pos),
                )

    def _insert_media(
        self, tweet_id: int, media_keys: List[str], media_by_key: Dict[str, Dict]
    ) -> None:
        """Insert media and link to tweet."""
        for pos, key in enumerate(media_keys):
            m = media_by_key.get(key)
            if not m:
                continue
            mt = m.get("type", "photo")
            if mt not in ("photo", "video", "animated_gif"):
                mt = "photo"
            self.cur.execute(
                """
                INSERT INTO media (media_key, media_type, url, preview_image_url, width, height, duration_ms, alt_text)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (media_key) DO NOTHING
                """,
                (
                    key,
                    mt,
                    m.get("url"),
                    m.get("preview_image_url"),
                    m.get("width"),
                    m.get("height"),
                    m.get("duration_ms"),
                    m.get("alt_text"),
                ),
            )
            self.cur.execute(
                "INSERT INTO tweet_media (tweet_id, media_key, position) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (tweet_id, key, pos),
            )

    def insert_places_batch(self, places: List[Dict]) -> int:
        """Insert places from includes."""
        if not places:
            return 0
        for p in places:
            try:
                pid = p.get("id")
                if not pid:
                    continue
                self.cur.execute(
                    """
                    INSERT INTO places (place_id, full_name, name, place_type, country, country_code, geo_bbox)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (place_id) DO NOTHING
                    """,
                    (
                        pid[:64],
                        (p.get("full_name") or "")[:255],
                        (p.get("name") or "")[:255],
                        (p.get("place_type") or "")[:50],
                        (p.get("country") or "")[:100],
                        (p.get("country_code") or "")[:10],
                        str(p.get("geo", {}).get("bbox"))[:500] if p.get("geo") else None,
                    ),
                )
            except Exception as e:
                logger.warning("Place insert failed: %s", e)
        self.conn.commit()
        return len(places)

    def start_ingestion_run(self, endpoint: str, query: str) -> int:
        """Start an ingestion run and return run_id."""
        self.cur.execute(
            """
            INSERT INTO ingestion_runs (started_at, endpoint, query, status)
            VALUES (NOW(), %s, %s, 'running')
            RETURNING run_id
            """,
            (endpoint, query),
        )
        run_id = self.cur.fetchone()[0]
        self.conn.commit()
        return run_id

    def finish_ingestion_run(self, run_id: int, result_count: int, status: str = "success") -> None:
        """Mark ingestion run as complete."""
        self.cur.execute(
            """
            UPDATE ingestion_runs SET finished_at = NOW(), result_count = %s, status = %s
            WHERE run_id = %s
            """,
            (result_count, status, run_id),
        )
        self.conn.commit()

    def get_tweet_count(self) -> int:
        """Return total tweets in database."""
        self.cur.execute("SELECT COUNT(*) FROM tweets")
        return self.cur.fetchone()[0]

    def close(self) -> None:
        """Close database connection."""
        self.cur.close()
        self.conn.close()
