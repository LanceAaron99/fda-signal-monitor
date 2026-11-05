from load import get_conn

SQL = """
WITH drug_sets AS (
    SELECT safetyreportid,
           STRING_AGG(DISTINCT COALESCE(generic_name, product_name), ','
                      ORDER BY COALESCE(generic_name, product_name)) AS drugs
    FROM report_drugs GROUP BY safetyreportid
),
rx_sets AS (
    SELECT safetyreportid,
           STRING_AGG(DISTINCT reaction, ',' ORDER BY reaction) AS reactions
    FROM report_reactions GROUP BY safetyreportid
),
fp AS (
    SELECT r.safetyreportid,
           CONCAT_WS('|', r.patient_age_years, r.patient_sex, r.country,
                     ds.drugs, rs.reactions) AS fingerprint
    FROM reports r
    JOIN drug_sets ds USING (safetyreportid)
    JOIN rx_sets rs USING (safetyreportid)
)
SELECT fingerprint, COUNT(*) AS copies
FROM fp GROUP BY fingerprint
ORDER BY copies DESC
"""

conn = get_conn()
with conn.cursor() as cur:
    cur.execute(SQL)
    rows = cur.fetchall()
conn.close()

total = sum(c for _, c in rows)
dupes = sum(c - 1 for _, c in rows if c > 1)
print(f"Reports checked: {total:,} | Unique fingerprints: {len(rows):,}")
print(f"Likely duplicates: {dupes:,} ({100 * dupes / total:.1f}%)\n")
print("Most-copied fingerprints:")
for fp, copies in rows[:10]:
    print(f"  {copies:>5} copies | {fp[:110]}")