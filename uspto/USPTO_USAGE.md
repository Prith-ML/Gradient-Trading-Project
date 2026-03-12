# USPTO Data – Exploration & Updates

## 1. Is the data in the DB?

Yes. The pipeline loads into PostgreSQL (`uspto_data`). Verify with:

```sql
SELECT 'patents' AS tbl, COUNT(*) FROM patents
UNION ALL SELECT 'applications', COUNT(*) FROM applications
UNION ALL SELECT 'inventors', COUNT(*) FROM inventors
UNION ALL SELECT 'assignees', COUNT(*) FROM assignees;
```

---

## 2. Exploring the data

### Basic counts and samples
```sql
-- Sample patents with titles
SELECT patent_id, patent_title, patent_date, patent_type
FROM patents
ORDER BY patent_date DESC NULLS LAST
LIMIT 20;

-- Patents by year
SELECT EXTRACT(YEAR FROM patent_date) AS year, COUNT(*) AS cnt
FROM patents
WHERE patent_date IS NOT NULL
GROUP BY 1
ORDER BY 1 DESC
LIMIT 15;

-- Patents by type
SELECT patent_type, COUNT(*) AS cnt
FROM patents
GROUP BY patent_type
ORDER BY cnt DESC;
```

### Patents with inventors
```sql
SELECT p.patent_id, p.patent_title, p.patent_date,
       i.disambig_inventor_name_first, i.disambig_inventor_name_last
FROM patents p
JOIN patent_inventors pi ON p.patent_id = pi.patent_id
JOIN inventors i ON pi.inventor_id = i.inventor_id
ORDER BY p.patent_date DESC NULLS LAST
LIMIT 30;
```

### Patents with assignees (companies)
```sql
SELECT p.patent_id, p.patent_title,
       a.disambig_assignee_organization, a.disambig_assignee_individual_name_last
FROM patents p
JOIN patent_assignees pa ON p.patent_id = pa.patent_id
JOIN assignees a ON pa.assignee_id = a.assignee_id
WHERE a.disambig_assignee_organization IS NOT NULL
LIMIT 30;
```

### Top assignees by patent count
```sql
SELECT a.disambig_assignee_organization AS company, COUNT(*) AS patent_count
FROM assignees a
JOIN patent_assignees pa ON a.assignee_id = pa.assignee_id
WHERE a.disambig_assignee_organization IS NOT NULL
GROUP BY a.disambig_assignee_organization
ORDER BY patent_count DESC
LIMIT 20;
```

### Recent ingestion runs
```sql
SELECT run_id, table_name, started_at, finished_at, rows_loaded, status
FROM uspto_ingestion_runs
ORDER BY started_at DESC
LIMIT 10;
```

---

## 3. Keeping the DB updated when PatentsView publishes new data

PatentsView updates bulk files periodically (e.g. weekly). The update script re-downloads those files and inserts only new records.

### One-off update
```bash
python scripts/run_uspto_update.py
```

### Scheduled updates (recommended)

**Windows Task Scheduler**

1. Open Task Scheduler.
2. Create Basic Task → name it "USPTO Patent Update".
3. Trigger: Weekly (e.g. Sunday 2:00 AM).
4. Action: Start a program.
5. Program: `python`
6. Arguments: `c:\Users\prith\Gradient-Trading-Code--main\scripts\run_uspto_update.py`
7. Start in: `c:\Users\prith\Gradient-Trading-Code--main`

**Or run the scheduler daemon** (leave it running):
```bash
python scripts/schedule_uspto_updates.py
```
Runs the update every Sunday at 2:00 AM.

---

## 4. How the update works

- `run_uspto_update.py` sets `USPTO_FORCE_REFRESH=1` so the latest bulk files are re-downloaded.
- The pipeline loads data with `ON CONFLICT DO NOTHING`, so existing rows are skipped and only new patents are inserted.
- The DB is updated each time you run the update script (or when the scheduled task runs).
