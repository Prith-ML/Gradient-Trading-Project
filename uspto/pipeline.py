"""
USPTO PatentsView data pipeline.
Downloads patent data from PatentsView S3 and loads into PostgreSQL.
Free, no API key required.
"""

import csv
import io
import logging
import zipfile
from pathlib import Path

import psycopg2
import requests

from uspto.config import USPTOConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# PatentsView TSV files to load (name, S3 path, target table)
# Load patents first (others have FK to patents)
DATASETS_FULL = [
    ("g_patent", "g_patent.tsv.zip", "patents"),
    ("g_application", "g_application.tsv.zip", "applications"),
    ("g_inventor_disambiguated", "g_inventor_disambiguated.tsv.zip", "inventors"),
    ("g_assignee_disambiguated", "g_assignee_disambiguated.tsv.zip", "assignees"),
]
DATASETS_QUICK = [
    ("g_patent", "g_patent.tsv.zip", "patents"),
    ("g_application", "g_application.tsv.zip", "applications"),
]


def download_file(url: str, dest: Path) -> Path:
    """Download file with progress."""
    logger.info("Downloading %s...", url)
    r = requests.get(url, stream=True)
    r.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    logger.info("Saved to %s", dest)
    return dest


def parse_tsv_from_zip(zip_path: Path, filename: str):
    """Yield dict rows from TSV inside zip."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        with zf.open(filename) as f:
            text = io.TextIOWrapper(f, encoding="utf-8", errors="replace")
            reader = csv.DictReader(text, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
            for row in reader:
                yield row


def safe_date(val):
    """Parse date, return None if invalid."""
    if not val or val == "\\N":
        return None
    try:
        from datetime import datetime
        from dateutil import parser
        d = parser.parse(val)
        return d.date() if hasattr(d, "date") else d
    except Exception:
        return None


def safe_int(val):
    """Parse int, return None if invalid."""
    if val is None or val == "" or val == "\\N":
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def load_patents(conn, zip_path: Path, batch_size: int, max_rows: int = 0) -> int:
    """Load g_patent into patents table."""
    cur = conn.cursor()
    count = 0
    batch = []

    for row in parse_tsv_from_zip(zip_path, "g_patent.tsv"):
        if max_rows and count >= max_rows:
            break
        try:
            patent_id = row.get("patent_id", "").strip()
            if not patent_id:
                continue
            batch.append((
                patent_id[:20],
                (row.get("patent_type") or "")[:100],
                safe_date(row.get("patent_date")),
                (row.get("patent_title") or "")[:50000],
                (row.get("wipo_kind") or "")[:10],
                safe_int(row.get("num_claims")),
                safe_int(row.get("withdrawn")) or 0,
                (row.get("filename") or "")[:120],
            ))
            if len(batch) >= batch_size:
                cur.executemany(
                    """INSERT INTO patents (patent_id, patent_type, patent_date, patent_title, wipo_kind, num_claims, withdrawn, filename)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (patent_id) DO NOTHING""",
                    batch,
                )
                count += len(batch)
                conn.commit()
                batch = []
                logger.info("Loaded %d patents...", count)
        except Exception as e:
            logger.warning("Row error: %s", e)
            continue

    if batch:
        cur.executemany(
            """INSERT INTO patents (patent_id, patent_type, patent_date, patent_title, wipo_kind, num_claims, withdrawn, filename)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (patent_id) DO NOTHING""",
            batch,
        )
        count += len(batch)
        conn.commit()
    cur.close()
    return count


def load_applications(conn, zip_path: Path, batch_size: int, patent_ids: set, max_rows: int = 0) -> int:
    """Load g_application into applications table. Run after patents."""
    cur = conn.cursor()
    count = 0
    batch = []

    for row in parse_tsv_from_zip(zip_path, "g_application.tsv"):
        if max_rows and count >= max_rows:
            break
        try:
            app_id = (row.get("application_id") or "").strip()
            patent_id = (row.get("patent_id") or "").strip()
            if not app_id or not patent_id or patent_id not in patent_ids:
                continue
            batch.append((
                app_id[:36],
                patent_id[:20],
                (row.get("patent_application_type") or "")[:20],
                safe_date(row.get("filing_date")),
                (row.get("series_code") or "")[:20],
                safe_int(row.get("rule_47_flag")),
            ))
            if len(batch) >= batch_size:
                cur.executemany(
                    """INSERT INTO applications (application_id, patent_id, patent_application_type, filing_date, series_code, rule_47_flag)
                       VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (application_id) DO NOTHING""",
                    batch,
                )
                count += len(batch)
                conn.commit()
                batch = []
                logger.info("Loaded %d applications...", count)
        except Exception as e:
            logger.warning("Row error: %s", e)
            continue

    if batch:
        cur.executemany(
            """INSERT INTO applications (application_id, patent_id, patent_application_type, filing_date, series_code, rule_47_flag)
               VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (application_id) DO NOTHING""",
            batch,
        )
        count += len(batch)
        conn.commit()
    cur.close()
    return count


def load_inventors(conn, zip_path: Path, batch_size: int, patent_ids: set, max_rows: int = 0) -> int:
    """Load g_inventor_disambiguated into inventors and patent_inventors."""
    cur = conn.cursor()
    inv_count = 0
    link_count = 0
    inv_batch = []
    link_batch = []

    for row in parse_tsv_from_zip(zip_path, "g_inventor_disambiguated.tsv"):
        if max_rows and link_count >= max_rows:
            break
        try:
            patent_id = (row.get("patent_id") or "").strip()
            inventor_id = (row.get("inventor_id") or "").strip()
            if not patent_id or not inventor_id or patent_id not in patent_ids:
                continue
            seq = safe_int(row.get("inventor_sequence")) or 0
            inv_batch.append((
                inventor_id[:128],
                (row.get("disambig_inventor_name_first") or "")[:500],
                (row.get("disambig_inventor_name_last") or "")[:500],
                (row.get("gender_code") or "")[:1],
                (row.get("location_id") or "")[:128],
            ))
            link_batch.append((patent_id[:20], inventor_id[:128], seq))
            if len(inv_batch) >= batch_size:
                cur.executemany(
                    """INSERT INTO inventors (inventor_id, disambig_inventor_name_first, disambig_inventor_name_last, gender_code, location_id)
                       VALUES (%s, %s, %s, %s, %s) ON CONFLICT (inventor_id) DO NOTHING""",
                    inv_batch,
                )
                cur.executemany(
                    """INSERT INTO patent_inventors (patent_id, inventor_id, inventor_sequence)
                       VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                    link_batch,
                )
                inv_count += len(inv_batch)
                link_count += len(link_batch)
                conn.commit()
                inv_batch, link_batch = [], []
                logger.info("Loaded %d inventors, %d links...", inv_count, link_count)
        except Exception as e:
            logger.warning("Row error: %s", e)
            continue

    if inv_batch:
        cur.executemany(
            """INSERT INTO inventors (inventor_id, disambig_inventor_name_first, disambig_inventor_name_last, gender_code, location_id)
               VALUES (%s, %s, %s, %s, %s) ON CONFLICT (inventor_id) DO NOTHING""",
            inv_batch,
        )
        cur.executemany(
            """INSERT INTO patent_inventors (patent_id, inventor_id, inventor_sequence)
               VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
            link_batch,
        )
        inv_count += len(inv_batch)
        link_count += len(link_batch)
        conn.commit()
    cur.close()
    return inv_count


def load_assignees(conn, zip_path: Path, batch_size: int, patent_ids: set, max_rows: int = 0) -> int:
    """Load g_assignee_disambiguated into assignees and patent_assignees."""
    cur = conn.cursor()
    asn_count = 0
    link_count = 0
    asn_batch = []
    link_batch = []

    for row in parse_tsv_from_zip(zip_path, "g_assignee_disambiguated.tsv"):
        if max_rows and link_count >= max_rows:
            break
        try:
            patent_id = (row.get("patent_id") or "").strip()
            assignee_id = (row.get("assignee_id") or "").strip()
            if not patent_id or not assignee_id or patent_id not in patent_ids:
                continue
            seq = safe_int(row.get("assignee_sequence")) or 0
            asn_batch.append((
                assignee_id[:36],
                (row.get("disambig_assignee_individual_name_first") or "")[:96],
                (row.get("disambig_assignee_individual_name_last") or "")[:96],
                (row.get("disambig_assignee_organization") or "")[:256],
                safe_int(row.get("assignee_type")),
                (row.get("location_id") or "")[:128],
            ))
            link_batch.append((patent_id[:20], assignee_id[:36], seq))
            if len(asn_batch) >= batch_size:
                cur.executemany(
                    """INSERT INTO assignees (assignee_id, disambig_assignee_individual_name_first, disambig_assignee_individual_name_last,
                       disambig_assignee_organization, assignee_type, location_id)
                       VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (assignee_id) DO NOTHING""",
                    asn_batch,
                )
                cur.executemany(
                    """INSERT INTO patent_assignees (patent_id, assignee_id, assignee_sequence)
                       VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                    link_batch,
                )
                asn_count += len(asn_batch)
                link_count += len(link_batch)
                conn.commit()
                asn_batch, link_batch = [], []
                logger.info("Loaded %d assignees, %d links...", asn_count, link_count)
        except Exception as e:
            logger.warning("Row error: %s", e)
            continue

    if asn_batch:
        cur.executemany(
            """INSERT INTO assignees (assignee_id, disambig_assignee_individual_name_first, disambig_assignee_individual_name_last,
               disambig_assignee_organization, assignee_type, location_id)
               VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (assignee_id) DO NOTHING""",
            asn_batch,
        )
        cur.executemany(
            """INSERT INTO patent_assignees (patent_id, assignee_id, assignee_sequence)
               VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
            link_batch,
        )
        asn_count += len(asn_batch)
        link_count += len(link_batch)
        conn.commit()
    cur.close()
    return asn_count


LOADERS = {
    "patents": load_patents,
    "applications": load_applications,
    "inventors": load_inventors,
    "assignees": load_assignees,
}


def run_pipeline():
    """Main pipeline."""
    cfg = USPTOConfig()
    data_dir = Path(cfg.DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    max_patents = cfg.MAX_PATENTS or None
    max_inventors = cfg.MAX_INVENTORS or None
    max_assignees = cfg.MAX_ASSIGNEES or None
    datasets = DATASETS_QUICK if cfg.QUICK_MODE else DATASETS_FULL
    if cfg.QUICK_MODE:
        logger.info("QUICK MODE: patents + applications only (~10 min)")
    elif max_patents:
        logger.info("Limiting to %d patents, %d inventors, %d assignees (set USPTO_MAX_PATENTS=0 for full load)", max_patents, max_inventors or 0, max_assignees or 0)

    conn = psycopg2.connect(
        host=cfg.DB_HOST,
        port=cfg.DB_PORT,
        database=cfg.DB_NAME,
        user=cfg.DB_USER,
        password=cfg.DB_PASSWORD,
    )

    patent_ids = set()

    for name, filename, table in datasets:
        url = f"{cfg.PATENTSVIEW_BASE}/{filename}"
        zip_path = data_dir / filename
        try:
            if not zip_path.exists():
                download_file(url, zip_path)
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO uspto_ingestion_runs (started_at, source_url, table_name, status)
                   VALUES (NOW(), %s, %s, 'running') RETURNING run_id""",
                (url, table),
            )
            run_id = cur.fetchone()[0]
            conn.commit()
            cur.close()

            if table == "patents":
                rows = load_patents(conn, zip_path, cfg.BATCH_SIZE, max_rows=max_patents or 0)
                cur = conn.cursor()
                cur.execute("SELECT patent_id FROM patents")
                patent_ids = {r[0] for r in cur.fetchall()}
                cur.close()
            elif table == "applications":
                rows = load_applications(conn, zip_path, cfg.BATCH_SIZE, patent_ids, max_rows=max_patents or 0)
            elif table == "inventors":
                rows = load_inventors(conn, zip_path, cfg.BATCH_SIZE, patent_ids, max_rows=max_inventors or 0)
            elif table == "assignees":
                rows = load_assignees(conn, zip_path, cfg.BATCH_SIZE, patent_ids, max_rows=max_assignees or 0)
            else:
                rows = 0

            cur = conn.cursor()
            cur.execute(
                """UPDATE uspto_ingestion_runs SET finished_at = NOW(), rows_loaded = %s, status = 'success' WHERE run_id = %s""",
                (rows, run_id),
            )
            conn.commit()
            cur.close()
            logger.info("Completed %s: %d rows", table, rows)
        except Exception as e:
            logger.error("Failed %s: %s", table, e)
            raise

    conn.close()
    logger.info("Pipeline finished.")


if __name__ == "__main__":
    run_pipeline()
