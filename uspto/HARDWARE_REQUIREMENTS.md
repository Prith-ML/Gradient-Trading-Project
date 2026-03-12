# Hardware Requirements - USPTO Patent Data Pipeline

Requirements for running the PatentsView patent data pipeline.

---

## 1. Minimum Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **CPU** | 2 cores | 4 cores |
| **RAM** | 8 GB | 16 GB |
| **Disk (SSD)** | 20 GB free | 50 GB free |
| **Network** | 10 Mbps | 50+ Mbps |
| **OS** | Windows 10/11, Linux, macOS | Linux (Ubuntu 22.04) |

---

## 2. Storage Breakdown

| Dataset | Download (zip) | Uncompressed | Rows (approx) |
|---------|----------------|--------------|---------------|
| g_patent | 219 MB | 1.0 GB | 12.5M |
| g_application | 68 MB | 413 MB | 12.5M |
| g_inventor_disambiguated | 667 MB | 2.1 GB | 24M |
| g_assignee_disambiguated | 342 MB | 1.0 GB | 10.6M |
| **Total downloads** | ~1.3 GB | ~4.5 GB | — |
| **PostgreSQL (estimated)** | — | ~8–15 GB | — |

**Recommendation:** 20 GB free for downloads + database; 50 GB for comfortable headroom.

---

## 3. RAM

- **Python process:** 500 MB–2 GB (streaming TSV, batch inserts)
- **PostgreSQL:** 2–4 GB (shared_buffers, work_mem for bulk loads)
- **OS:** 2 GB
- **Total:** 8 GB minimum, 16 GB recommended

---

## 4. Time Estimates

| Stage | Approx. Time |
|-------|---------------|
| Download g_patent | 5–15 min |
| Load patents | 15–45 min |
| Download g_application | 2–5 min |
| Load applications | 10–30 min |
| Download g_inventor | 15–45 min |
| Load inventors | 45–90 min |
| Download g_assignee | 8–20 min |
| Load assignees | 20–45 min |
| **Total** | **2–5 hours** |

*Depends on network speed and disk I/O.*

---

## 5. Data Source

- **PatentsView** (patentsview.org) – USPTO-backed, free
- **No API key** required
- **Bulk TSV** from S3
