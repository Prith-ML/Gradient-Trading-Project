"""
USPTO PatentsView pipeline configuration.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class USPTOConfig:
    """Pipeline configuration."""

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("USPTO_DB_NAME", "uspto_data")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    # Download
    DATA_DIR: str = os.getenv("USPTO_DATA_DIR", "uspto_data_downloads")
    BATCH_SIZE: int = int(os.getenv("USPTO_BATCH_SIZE", "5000"))

    # Row limits (set to 0 for full load). 10k patents ~10 min in quick mode.
    MAX_PATENTS: int = int(os.getenv("USPTO_MAX_PATENTS", "10000"))
    MAX_INVENTORS: int = int(os.getenv("USPTO_MAX_INVENTORS", "50000"))
    MAX_ASSIGNEES: int = int(os.getenv("USPTO_MAX_ASSIGNEES", "25000"))
    # Quick mode: only patents + applications (~15 min). Skip inventors/assignees (huge files).
    QUICK_MODE: bool = os.getenv("USPTO_QUICK_MODE", "1").lower() in ("1", "true", "yes")

    # PatentsView S3 base URL
    PATENTSVIEW_BASE = "https://s3.amazonaws.com/data.patentsview.org/download"
