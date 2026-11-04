import argparse, logging
from datetime import date, datetime, timedelta
from extract import fetch_day
from transform import transform
from load import get_conn, load

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler("pipeline.log", encoding="utf-8"), logging.StreamHandler()])
log = logging.getLogger("pipeline")

DEFAULT_START = date(2026, 1, 1)
RETENTION_MONTHS = 9

def execute(sql, params=None, fetch=False):
    """Open a fresh connection, run one statement, commit, close."""
    conn = get_conn()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone() if fetch else cur.rowcount
    finally:
        conn.close()

def last_loaded_date():
    return execute("SELECT MAX(receive_date) FROM reports", fetch=True)[0]

def start_run(d_from, d_to):
    return execute("""INSERT INTO etl_runs (date_from, date_to, status)
                      VALUES (%s, %s, 'running') RETURNING run_id""",
                   (d_from, d_to), fetch=True)[0]

def finish_run(run_id, rows, status, error=None):
    execute("""UPDATE etl_runs SET finished_at = NOW(), rows_loaded = %s,
               status = %s, error_msg = %s WHERE run_id = %s""",
            (rows, status, error, run_id))

def db_size():
    return execute("SELECT pg_size_pretty(pg_database_size(current_database()))",
                   fetch=True)[0]

def apply_retention():
    removed = execute("""DELETE FROM reports
                         WHERE receive_date < (SELECT MAX(receive_date) FROM reports)
                                              - %s * INTERVAL '1 month'""",
                      (RETENTION_MONTHS,))
    log.info(f"Retention: removed {removed} old reports")

def load_day(reps, drgs, rxns):
    conn = get_conn()   # fresh connection each day (Neon closes idle ones)
    try:
        return load(conn, reps, drgs, rxns)
    finally:
        conn.close()

def run(d_from, d_to):
    run_id = start_run(d_from, d_to)
    log.info(f"Run {run_id}: loading {d_from} to {d_to}")
    total, day = 0, d_from
    try:
        while day <= d_to:
            raw = fetch_day(day.strftime("%Y%m%d"))
            if raw:
                reps, drgs, rxns = transform(raw)
                total += load_day(reps, drgs, rxns)
                log.info(f"{day}: {len(reps)} reports, {len(drgs)} drugs, {len(rxns)} reactions")
            else:
                log.info(f"{day}: no data")
            day += timedelta(days=1)
        apply_retention()
        finish_run(run_id, total, "success")
        log.info(f"Run {run_id} done ✅ {total} reports loaded | DB size: {db_size()}")
    except Exception as e:
        log.exception(f"Run {run_id} failed ❌")
        try:
            finish_run(run_id, total, "failed", str(e)[:500])
        except Exception:
            log.error("Could not record the failure in etl_runs")
        raise

def parse(s):
    return datetime.strptime(s, "%Y-%m-%d").date()

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="FDA adverse event ETL")
    p.add_argument("--start", help="YYYY-MM-DD (default: day after last loaded)")
    p.add_argument("--end", help="YYYY-MM-DD (default: today)")
    args = p.parse_args()

    if args.start:
        d_from = parse(args.start)
    else:
        last = last_loaded_date()
        d_from = last + timedelta(days=1) if last else DEFAULT_START
    d_to = parse(args.end) if args.end else date.today()
    run(d_from, d_to)