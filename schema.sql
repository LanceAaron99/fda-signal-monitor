CREATE TABLE IF NOT EXISTS reports (
    safetyreportid    TEXT PRIMARY KEY,
    report_version    INT,
    receive_date      DATE NOT NULL,
    serious           BOOLEAN,
    death             BOOLEAN,
    hospitalization   BOOLEAN,
    life_threatening  BOOLEAN,
    country           TEXT,
    reporter_type     SMALLINT,
    patient_age_years NUMERIC(5,1),
    patient_sex       TEXT,
    loaded_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS report_drugs (
    id             SERIAL PRIMARY KEY,
    safetyreportid TEXT REFERENCES reports(safetyreportid) ON DELETE CASCADE,
    product_name   TEXT,
    generic_name   TEXT,
    drug_role      SMALLINT
);

CREATE TABLE IF NOT EXISTS report_reactions (
    id             SERIAL PRIMARY KEY,
    safetyreportid TEXT REFERENCES reports(safetyreportid) ON DELETE CASCADE,
    reaction       TEXT,
    outcome        SMALLINT
);

CREATE TABLE IF NOT EXISTS etl_runs (
    run_id       SERIAL PRIMARY KEY,
    started_at   TIMESTAMPTZ DEFAULT NOW(),
    finished_at  TIMESTAMPTZ,
    date_from    DATE,
    date_to      DATE,
    rows_loaded  INT,
    status       TEXT,
    error_msg    TEXT
);

CREATE INDEX IF NOT EXISTS idx_reports_date    ON reports(receive_date);
CREATE INDEX IF NOT EXISTS idx_drugs_generic   ON report_drugs(generic_name);
CREATE INDEX IF NOT EXISTS idx_reactions_term  ON report_reactions(reaction);