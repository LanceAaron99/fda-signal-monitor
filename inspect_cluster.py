from load import get_conn

SQL = """
WITH ids AS (
    SELECT DISTINCT d.safetyreportid
    FROM report_drugs d
    JOIN report_reactions r USING (safetyreportid)
    WHERE d.generic_name = 'DESOXIMETASONE'
      AND r.reaction = 'DUODENAL ULCER PERFORATION'
)
SELECT r.country, r.patient_sex, r.patient_age_years, r.reporter_type,
       (SELECT COUNT(*) FROM report_drugs x
         WHERE x.safetyreportid = r.safetyreportid)     AS n_drugs,
       (SELECT COUNT(*) FROM report_reactions x
         WHERE x.safetyreportid = r.safetyreportid)     AS n_reactions,
       COUNT(*)                                          AS reports,
       MIN(r.receive_date), MAX(r.receive_date)
FROM reports r JOIN ids USING (safetyreportid)
GROUP BY 1, 2, 3, 4, 5, 6
ORDER BY reports DESC
LIMIT 15
"""

conn = get_conn()
with conn.cursor() as cur:
    cur.execute(SQL)
    print("country | sex | age | reporter | drugs | reactions | reports | first | last")
    for row in cur.fetchall():
        print(" | ".join(str(x) for x in row))
conn.close()