import time
from load import get_conn

with open("signals.sql") as f:
    sql = f.read()

conn = get_conn()
with conn, conn.cursor() as cur:
    t = time.time()
    cur.execute(sql)
    print(f"Built counts in {time.time() - t:.0f}s ✅")

    cur.execute("SELECT (SELECT COUNT(*) FROM reports), (SELECT COUNT(*) FROM kept_reports)")
    total, kept = cur.fetchone()
    print(f"Reports removed (duplicates + mega-reports): {total - kept:,} of {total:,} ({100 * (total - kept) / total:.1f}%)")

    cur.execute("SELECT COUNT(*) FROM drug_reaction_counts")
    print("Drug-reaction pairs (3+ reports):", cur.fetchone()[0])

    cur.execute("""SELECT ROUND(100.0 * AVG((generic_name IS NOT NULL)::int), 1)
                   FROM report_drugs WHERE drug_role = 1""")
    print("Suspect drugs with a generic name:", cur.fetchone()[0], "%")

    cur.execute("""SELECT drug, reaction, a, b, c, d
                   FROM drug_reaction_counts ORDER BY a DESC LIMIT 10""")
    print("\nTop 10 pairs by report count:")
    for row in cur.fetchall():
        print(" ", row)
conn.close()