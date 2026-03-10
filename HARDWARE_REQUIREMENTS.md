# Hardware Resource Requirements for Twitter Data Pipeline

This document details the exact hardware and resource requirements for running the Twitter/X data pipeline that fetches and stores **500,000 tweets** in a local PostgreSQL database.

---

## 1. Minimum Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **CPU** | 2 cores | 4 cores |
| **RAM** | 4 GB | 8 GB |
| **Disk (SSD)** | 2 GB free | 5 GB free |
| **Network** | 10 Mbps stable | 50+ Mbps |
| **OS** | Windows 10/11, Linux, macOS | Linux (Ubuntu 22.04 LTS) |

---

## 2. Detailed Breakdown

### 2.1 CPU

- **Pipeline process**: Single-threaded Python; 1 core is sufficient for the main loop.
- **PostgreSQL**: Benefits from 2+ cores for concurrent writes and index maintenance.
- **Recommendation**: 4 cores for comfortable headroom during bulk inserts and index creation.

### 2.2 RAM

| Component | Usage |
|-----------|-------|
| Python process | ~200–400 MB (tweepy, psycopg2, JSON parsing) |
| PostgreSQL | ~512 MB–2 GB (shared_buffers, work_mem) |
| OS + overhead | ~1–2 GB |
| **Total** | **4 GB minimum**, **8 GB recommended** |

For 500k tweets, PostgreSQL `shared_buffers` of 256 MB–512 MB is adequate. Increase to 1–2 GB if running other workloads.

### 2.3 Disk Storage

Estimated storage for **500,000 tweets**:

| Table / Component | Estimated Size |
|-------------------|----------------|
| `tweets` | ~250–400 MB |
| `users` | ~50–100 MB |
| `hashtags` + `tweet_hashtags` | ~25–50 MB |
| `urls` + `tweet_urls` | ~50–100 MB |
| `tweet_mentions` | ~50–80 MB |
| `media` + `tweet_media` | ~15–30 MB |
| `ingestion_runs` + `tweet_ingestion` | ~30–50 MB |
| Indexes | ~150–250 MB |
| WAL / temp | ~100–200 MB |
| **Total** | **~700 MB – 1.2 GB** |

**Recommendation**: At least **2 GB free** on SSD for data + indexes + WAL. **5 GB** recommended for safety and future growth.

### 2.4 Network

- **API traffic**: ~50–100 KB per request (100 tweets + metadata).
- **500k tweets** ≈ 5,000 requests → ~250–500 MB total download.
- **Rate limits**: X API typically allows 60–300 requests per 15 minutes depending on tier.
- **Recommendation**: 10 Mbps minimum; 50+ Mbps preferred for faster ingestion.

---

## 3. PostgreSQL Configuration

Suggested `postgresql.conf` settings for this workload:

```ini
# Memory
shared_buffers = 256MB
work_mem = 16MB
maintenance_work_mem = 128MB

# WAL (for bulk inserts)
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# Connections
max_connections = 50
```

---

## 4. Time Estimates

| API Tier | Requests/15 min | Time to 500k tweets |
|----------|-----------------|----------------------|
| Basic ($100/mo) | ~60 | ~21 hours |
| Pro ($5,000/mo) | ~300 | ~4–5 hours |
| Academic Research | Varies | Varies |

*Assumes 100 tweets per request and continuous operation.*

---

## 5. X API Access Requirements

To fetch 500,000 tweets you need:

- **Basic tier** or higher (Free tier: 1,500 tweets/month).
- **Bearer token** from [X Developer Portal](https://developer.x.com/).
- `/2/tweets/search/recent` returns tweets from the **last 7 days** only.

For historical data beyond 7 days, use `/2/tweets/search/all` (Pro or Academic Research).

---

## 6. Checklist Before Running

- [ ] PostgreSQL 12+ installed and running
- [ ] Database `twitter_data` created
- [ ] Schema applied (`python scripts/setup_db.py`)
- [ ] `.env` configured with `TWITTER_BEARER_TOKEN` and DB credentials
- [ ] At least 2 GB free disk space
- [ ] Stable internet connection
