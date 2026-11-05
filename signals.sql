DROP MATERIALIZED VIEW IF EXISTS drug_reaction_counts;
DROP MATERIALIZED VIEW IF EXISTS kept_reports;

-- Step A: remove duplicates and mega-reports (more than 15 suspect drugs)
CREATE MATERIALIZED VIEW kept_reports AS
WITH drug_sets AS (
    SELECT safetyreportid,
           STRING_AGG(DISTINCT COALESCE(generic_name, product_name), ','
                      ORDER BY COALESCE(generic_name, product_name)) AS drugs,
           COUNT(DISTINCT COALESCE(generic_name, product_name)) AS n_drugs
    FROM report_drugs GROUP BY safetyreportid
),
rx_sets AS (
    SELECT safetyreportid,
           STRING_AGG(DISTINCT reaction, ',' ORDER BY reaction) AS reactions,
           COUNT(DISTINCT reaction) AS n_rx
    FROM report_reactions GROUP BY safetyreportid
),
fp AS (
    SELECT r.safetyreportid,
           COALESCE(ds.n_drugs, 0) AS n_drugs,
           (r.patient_age_years IS NOT NULL AND r.patient_sex IS NOT NULL
            AND COALESCE(ds.n_drugs, 0) + COALESCE(rs.n_rx, 0) >= 4) AS detailed,
           CONCAT_WS('|', r.patient_age_years, r.patient_sex, r.country,
                     ds.drugs, rs.reactions) AS fingerprint
    FROM reports r
    LEFT JOIN drug_sets ds USING (safetyreportid)
    LEFT JOIN rx_sets rs USING (safetyreportid)
)
SELECT safetyreportid FROM fp
WHERE NOT detailed AND n_drugs <= 15                  -- keep sparse reports
UNION ALL
(SELECT DISTINCT ON (fingerprint) safetyreportid      -- 1 per detailed fingerprint
 FROM fp WHERE detailed AND n_drugs <= 15
 ORDER BY fingerprint, safetyreportid);

CREATE UNIQUE INDEX ON kept_reports (safetyreportid);

-- Step B: 2x2 counts for every drug-reaction pair
CREATE MATERIALIZED VIEW drug_reaction_counts AS
WITH drug_reports AS (      -- each kept report's suspect drugs
    SELECT DISTINCT d.safetyreportid, d.generic_name AS drug
    FROM report_drugs d
    JOIN kept_reports k USING (safetyreportid)
    WHERE d.drug_role = 1 AND d.generic_name IS NOT NULL
),
rx_reports AS (             -- each report's reactions (noise removed)
    SELECT DISTINCT safetyreportid, reaction
    FROM report_reactions
    WHERE reaction !~ '(DOSE|EXPOSURE|ADMINISTERED|ADMINISTRATION|MEDICATION ERROR|OFF LABEL|DEVICE|WRONG |THERAPY|THERAPEUTIC|INAPPROPRIATE|ERROR|ADVERSE DRUG REACTION|ADVERSE EVENT)'
),
base AS (
    SELECT DISTINCT safetyreportid FROM drug_reports
),
pairs AS (
    SELECT d.drug, r.reaction, COUNT(*) AS a
    FROM drug_reports d
    JOIN rx_reports r USING (safetyreportid)
    GROUP BY d.drug, r.reaction
),
drug_totals AS (
    SELECT drug, COUNT(*) AS n_drug FROM drug_reports GROUP BY drug
),
rx_totals AS (
    SELECT reaction, COUNT(*) AS n_rx
    FROM rx_reports JOIN base USING (safetyreportid)
    GROUP BY reaction
),
total AS (SELECT COUNT(*) AS n FROM base)
SELECT p.drug, p.reaction,
       p.a,
       dt.n_drug - p.a                     AS b,
       rt.n_rx - p.a                       AS c,
       t.n - dt.n_drug - rt.n_rx + p.a     AS d
FROM pairs p
JOIN drug_totals dt USING (drug)
JOIN rx_totals rt USING (reaction)
CROSS JOIN total t
WHERE p.a >= 3;

CREATE INDEX ON drug_reaction_counts (drug);