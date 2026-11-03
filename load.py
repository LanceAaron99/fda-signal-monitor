import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

REPORT_COLS = ["safetyreportid", "report_version", "receive_date", "serious",
               "death", "hospitalization", "life_threatening", "country",
               "reporter_type", "patient_age_years", "patient_sex"]
DRUG_COLS = ["safetyreportid", "product_name", "generic_name", "drug_role"]
RX_COLS = ["safetyreportid", "reaction", "outcome"]

def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def to_rows(dicts, cols):
    return [tuple(d[c] for c in cols) for d in dicts]

def insert(cur, table, cols, dicts):
    if dicts:
        execute_values(cur, f"INSERT INTO {table} ({', '.join(cols)}) VALUES %s",
                       to_rows(dicts, cols), page_size=1000)

def load(conn, reports, drugs, reactions):
    """Replace these reports in ONE transaction: all or nothing."""
    ids = [r["safetyreportid"] for r in reports]
    with conn:                      # commit if OK, roll back if error
        with conn.cursor() as cur:
            # Deleting a report also deletes its drugs/reactions (CASCADE)
            cur.execute("DELETE FROM reports WHERE safetyreportid = ANY(%s)", (ids,))
            insert(cur, "reports", REPORT_COLS, reports)
            insert(cur, "report_drugs", DRUG_COLS, drugs)
            insert(cur, "report_reactions", RX_COLS, reactions)
    return len(reports)

def count_rows(conn):
    with conn.cursor() as cur:
        out = {}
        for t in ["reports", "report_drugs", "report_reactions"]:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            out[t] = cur.fetchone()[0]
    return out

if __name__ == "__main__":
    from extract import fetch_day
    from transform import transform

    reps, drgs, rxns = transform(fetch_day("20250115"))
    conn = get_conn()

    load(conn, reps, drgs, rxns)
    print("After 1st load:", count_rows(conn))

    load(conn, reps, drgs, rxns)        # run again on purpose
    print("After 2nd load:", count_rows(conn), "(should be the same ✅)")
    conn.close()