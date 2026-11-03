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

DEFAULT_START = date(2025, 1, 1)

def last_loaded_date(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(receive_date) FROM reports")
        return cur.fetchone()[0]

def start_run(conn, d_from, d_to):
    with conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO etl_runs (date_from, date_to, status)
                       VALUES (%s, %s, 'running') RETURNING run_id""", (d_from, d_to))
        return cur.fetchone()[0]

def finish_run(conn, run_id, rows, status, error=None):
    with conn, conn.cursor() as cur:
        cur.execute("""UPDATE etl_runs SET finished_at = NOW(), rows_loaded = %s,
                       status = %s, error_msg = %s WHERE run_id = %s""",
                    (rows, status, error, run_id))

def db_size(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        return cur.fetchone()[0]

def run(conn, d_from, d_to):
    run_id = start_run(conn, d_from, d_to)
    log.info(f"Run {run_id}: loading {d_from} to {d_to}")
    total, day = 0, d_from
    try:
        while day <= d_to:
            raw = fetch_day(day.strftime("%Y%m%d"))
            if raw:
                reps, drgs, rxns = transform(raw)
                total += load(conn, reps, drgs, rxns)
                log.info(f"{day}: {len(reps)} reports, {len(drgs)} drugs, {len(rxns)} reactions")
            else:
                log.info(f"{day}: no data")
            day += timedelta(days=1)
        finish_run(conn, run_id, total, "success")
        log.info(f"Run {run_id} done ✅ {total} reports loaded | DB size: {db_size(conn)}")
    except Exception as e:
        log.exception(f"Run {run_id} failed ❌")
        finish_run(conn, run_id, total, "failed", str(e)[:500])
        raise

def parse(s):
    return datetime.strptime(s, "%Y-%m-%d").date()

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="FDA adverse event ETL")
    p.add_argument("--start", help="YYYY-MM-DD (default: day after last loaded)")
    p.add_argument("--end", help="YYYY-MM-DD (default: today)")
    args = p.parse_args()

    conn = get_conn()
    try:
        if args.start:
            d_from = parse(args.start)
        else:
            last = last_loaded_date(conn)
            d_from = last + timedelta(days=1) if last else DEFAULT_START
        d_to = parse(args.end) if args.end else date.today()
        run(conn, d_from, d_to)
    finally:
        conn.close()