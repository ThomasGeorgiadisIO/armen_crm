-- Armen CRM schema: Customer -> Project -> Template (generated document instance)
-- All identifier-like fields are TEXT, never INTEGER/REAL, to avoid the
-- float-corruption/scientific-notation risk discovered in the original
-- Customers.ods export (leading zeros, 14-digit codes, etc.).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customers (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    address TEXT,
    phone   TEXT
);

CREATE TABLE IF NOT EXISTS projects (
    id                                   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id                          INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    name                                  TEXT NOT NULL,
    created_at                           TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Installation/boiler/meter details used to live on projects, but since they
-- can change between visits/certificates for the same project, they're
-- entered per-generation (via the export wizard) and stored here instead.
CREATE TABLE IF NOT EXISTS templates (
    id                                   INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id                           INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    document_type                        TEXT NOT NULL,
    application_no                       TEXT,
    hkasp                                TEXT,
    installation_address                 TEXT,
    access_street                        TEXT,
    property_use                         TEXT,
    gas_use                              TEXT,
    boiler_brand_model                   TEXT,
    boiler_type                          TEXT,
    power_kw                             TEXT,
    flow_m3h                             TEXT,
    technology                           TEXT,
    meter_type                           TEXT,
    meter_position                       TEXT,
    regulator_pressure_mbar              TEXT,
    strength_test_design_pressure_mbar   TEXT,
    tightness_test_design_pressure_mbar  TEXT,
    visit_date                           TEXT,
    test_start_time                      TEXT,
    test_end_time                        TEXT,
    pass_fail                            TEXT,
    next_maintenance_date                TEXT,
    next_tightness_recheck_date          TEXT,
    output_pdf_path                      TEXT,
    generated_at                         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_projects_customer_id ON projects(customer_id);
CREATE INDEX IF NOT EXISTS idx_templates_project_id ON templates(project_id);
