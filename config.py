"""
Configuration for Twitter/X data pipeline.
Loads from environment variables via .env file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent / ".env")


class Config:
    """Pipeline configuration."""

    # Twitter API v2 credentials (Bearer Token for app-only auth)
    BEARER_TOKEN: str = os.getenv("TWITTER_BEARER_TOKEN", "")

    # Database (PostgreSQL)
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "twitter_data")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    # Pipeline targets
    TARGET_TWEET_COUNT: int = int(os.getenv("TARGET_TWEET_COUNT", "500000"))
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "100"))  # Max per API request (10-100)
    MAX_RESULTS_PER_REQUEST: int = min(100, max(10, int(os.getenv("MAX_RESULTS", "100"))))

    # Rate limiting (X API: ~60-300 requests per 15 min depending on tier)
    REQUESTS_PER_WINDOW: int = int(os.getenv("REQUESTS_PER_WINDOW", "60"))
    RATE_LIMIT_WINDOW_SEC: int = int(os.getenv("RATE_LIMIT_WINDOW_SEC", "900"))  # 15 min
    RETRY_DELAY_SEC: int = int(os.getenv("RETRY_DELAY_SEC", "60"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "5"))

    # Checkpoint/resume
    CHECKPOINT_FILE: str = os.getenv("CHECKPOINT_FILE", "pipeline_checkpoint.json")

    # Search query (configurable)
    SEARCH_QUERY: str = os.getenv(
        "SEARCH_QUERY",
        "lang:en -is:retweet -is:reply",  # Broad English tweets
    )

    @property
    def db_connection_string(self) -> str:
        """PostgreSQL connection string."""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
