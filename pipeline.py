"""
Twitter/X data pipeline: fetches tweets via API v2 and stores in PostgreSQL.
Supports checkpoint/resume, rate limiting, and configurable targets (e.g. 500k tweets).
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path

import tweepy
from tweepy import Client

from config import Config
from etl.twitter_etl import TwitterETL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class RateLimiter:
    """Token-bucket style rate limiter for API requests."""

    def __init__(self, requests_per_window: int, window_sec: int):
        self.requests_per_window = requests_per_window
        self.window_sec = window_sec
        self.timestamps: list[float] = []

    def wait_if_needed(self) -> None:
        """Block until a request is allowed."""
        now = time.time()
        self.timestamps = [t for t in self.timestamps if now - t < self.window_sec]
        if len(self.timestamps) >= self.requests_per_window:
            sleep_time = self.window_sec - (now - self.timestamps[0])
            if sleep_time > 0:
                logger.info("Rate limit: sleeping %.0f sec", sleep_time)
                time.sleep(sleep_time)
            self.timestamps = self.timestamps[1:]
        self.timestamps.append(time.time())


def load_checkpoint(path: str) -> dict:
    """Load checkpoint for resume."""
    p = Path(path)
    if not p.exists():
        return {}
    try:
        with open(p, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Checkpoint load failed: %s", e)
        return {}


def save_checkpoint(path: str, data: dict) -> None:
    """Save checkpoint."""
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning("Checkpoint save failed: %s", e)


def run_pipeline() -> None:
    """Main pipeline: fetch tweets and store in DB."""
    cfg = Config()
    if not cfg.BEARER_TOKEN:
        raise ValueError("TWITTER_BEARER_TOKEN not set. Copy .env.example to .env and configure.")

    client = Client(bearer_token=cfg.BEARER_TOKEN, wait_on_rate_limit=True)
    rate_limiter = RateLimiter(cfg.REQUESTS_PER_WINDOW, cfg.RATE_LIMIT_WINDOW_SEC)

    etl = TwitterETL(
        db_host=cfg.DB_HOST,
        db_name=cfg.DB_NAME,
        db_user=cfg.DB_USER,
        db_password=cfg.DB_PASSWORD,
        db_port=cfg.DB_PORT,
    )

    checkpoint = load_checkpoint(cfg.CHECKPOINT_FILE)
    next_token = checkpoint.get("next_token")
    total_ingested = etl.get_tweet_count()
    run_id = etl.start_ingestion_run(
        endpoint="/2/tweets/search/recent",
        query=cfg.SEARCH_QUERY,
    )

    logger.info(
        "Starting pipeline. Target: %d tweets. Current DB count: %d.",
        cfg.TARGET_TWEET_COUNT,
        total_ingested,
    )

    max_results = cfg.MAX_RESULTS_PER_REQUEST
    tweet_fields = [
        "created_at", "author_id", "conversation_id", "public_metrics",
        "context_annotations", "entities", "geo", "lang", "referenced_tweets",
        "reply_settings", "source", "possibly_sensitive",
    ]
    user_fields = ["created_at", "description", "public_metrics", "verified", "location", "url"]
    expansions = ["author_id", "referenced_tweets.id", "entities.mentions.username", "attachments.media_keys", "geo.place_id"]
    media_fields = ["url", "preview_image_url", "width", "height", "duration_ms", "alt_text"]
    place_fields = ["full_name", "name", "place_type", "country", "country_code", "geo"]

    request_count = 0
    batch_count = 0

    try:
        while total_ingested < cfg.TARGET_TWEET_COUNT:
            rate_limiter.wait_if_needed()

            try:
                response = client.search_recent_tweets(
                    query=cfg.SEARCH_QUERY,
                    max_results=max_results,
                    next_token=next_token,
                    tweet_fields=tweet_fields,
                    user_fields=user_fields,
                    expansions=expansions,
                    media_fields=media_fields,
                    place_fields=place_fields,
                )
            except tweepy.TooManyRequests:
                logger.warning("Rate limited by API. Waiting %d sec.", cfg.RETRY_DELAY_SEC)
                time.sleep(cfg.RETRY_DELAY_SEC)
                continue
            except tweepy.BadRequest as e:
                logger.warning("Bad request (e.g. expired next_token): %s. Resetting pagination.", e)
                next_token = None
                save_checkpoint(cfg.CHECKPOINT_FILE, {"next_token": None, "total_ingested": total_ingested, "updated_at": datetime.utcnow().isoformat()})
                continue
            except Exception as e:
                logger.error("API error: %s", e)
                raise

            request_count += 1
            data = response.data or []
            includes = response.includes or {}
            meta = response.meta or {}

            users = includes.get("users") or []
            places = includes.get("places") or []
            media_list = includes.get("media") or []

            users_by_id = {str(u["id"]): u for u in users}
            places_by_id = {str(p["id"]): p for p in places}
            media_by_key = {m["media_key"]: m for m in media_list}

            etl.insert_users_batch(users)
            etl.insert_places_batch(places)

            for tweet in data:
                if etl.insert_tweet(tweet, run_id, users_by_id, places_by_id, media_by_key):
                    total_ingested += 1
                    batch_count += 1

            next_token = meta.get("next_token")
            save_checkpoint(
                cfg.CHECKPOINT_FILE,
                {"next_token": next_token, "total_ingested": total_ingested, "updated_at": datetime.utcnow().isoformat()},
            )

            logger.info(
                "Batch: %d tweets this run, %d total. Requests: %d.",
                len(data),
                total_ingested,
                request_count,
            )

            if not next_token or not data:
                logger.info("No more results (end of search window or no next_token).")
                break

            if total_ingested >= cfg.TARGET_TWEET_COUNT:
                logger.info("Target reached: %d tweets.", total_ingested)
                break

    finally:
        etl.finish_ingestion_run(run_id, batch_count, "success" if total_ingested > 0 else "partial")
        final_count = etl.get_tweet_count()
        etl.close()
        logger.info("Pipeline finished. Total tweets in DB: %d", final_count)


if __name__ == "__main__":
    run_pipeline()
