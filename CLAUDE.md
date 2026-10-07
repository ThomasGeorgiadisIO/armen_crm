# Armen CRM — SQLite-backed Desktop CRM with LaTeX Document Export

## Context

The repo (`armen_crm`) is currently empty except LICENSE, a Python `.gitignore`, an existing `Customers.ods` spreadsheet (5 example customers), and 4 real Word/legacy-doc certificate templates at the root. The user wants a **very simple desktop CRM** for a gas-installation safety-certification business (engineer Κωνσταντίνος Άρμεν) that:

- Has a **graphical UI** (not CLI), running on **Windows** for the end user (development happens on this Linux/NixOS machine).
- Stores data relationally: **Customer → has many → Project → has many → Template** (a Template here means one generated document instance, e.g. one of the 4 certificate types produced for a given project on a given date).
- Lets the user select a customer, drill into a project, and generate/export the certificate documents for that project as PDFs into a per-customer/per-project `output/` folder.

**Pivot from the original plan**: the first draft of this roadmap used `Customers.ods` as the live data store. The user then asked for more objects with relationships (Customer/Project/Template), which a flat spreadsheet can't model well, and asked about PostgreSQL. Decision made with the user: **SQLite**, not PostgreSQL — PostgreSQL would require bundling a full server binary (~100-300MB), running `initdb`, and managing a background server process inside a single-user Windows desktop app, which is unjustified complexity here. SQLite is relational (tables, foreign keys, joins), ships in Python's standard library (`sqlite3`), needs no server process, and is a single file — ideal for this deployment shape. `Customers.ods` becomes a one-time migration source, not a live store.

No app code exists yet — this document is the roadmap for the implementation work ahead.

## Data model (SQLite)

```
customers
  id            INTEGER PRIMARY KEY
  name          TEXT NOT NULL        -- Πελάτης
  address       TEXT                 -- Διεύθυνση (customer's own address; a project may have a different installation address)
  phone         TEXT                 -- τηλ. (kept as TEXT — never INTEGER, to avoid leading-zero/precision issues)

projects                              -- one gas-installation job/application per customer
  id                        INTEGER PRIMARY KEY
  customer_id               INTEGER NOT NULL REFERENCES customers(id)
  name                      TEXT NOT NULL   -- lightweight label, e.g. "Αίτηση 6756"
  created_at                TEXT

templates                             -- one row per generated document instance (history + source of truth for PDF re-export)
  id                INTEGER PRIMARY KEY
  project_id        INTEGER NOT NULL REFERENCES projects(id)
  document_type     TEXT NOT NULL     -- one of: compliance | strength_tightness_test | maintenance_program | technical_report
  -- Installation/boiler/meter details -- these used to live on Project, but
  -- since they can change between visits/certificates for the same project
  -- (e.g. a boiler gets swapped, a re-test uses a different pressure), the
  -- user decided they should be entered fresh per document generation (via
  -- the export wizard) rather than stored once on Project. Project is now
  -- just a lightweight grouping label.
  application_no            TEXT      -- Αρ. Αίτησης / Κωδικός Πελάτη
  hkasp                     TEXT      -- ΗΚΑΣΠ, 14-digit code — TEXT, never INTEGER
  installation_address      TEXT      -- Διεύθυνση εγκατάστασης (may differ from customer address)
  access_street              TEXT      -- Οδός προσπέλασης
  property_use               TEXT      -- Χρήση ακινήτου (e.g. "κατοικία")
  gas_use                     TEXT      -- Χρήση αερίου (e.g. "θέρμανση & ζεστό νερό χρήσης")
  boiler_brand_model         TEXT      -- e.g. "Sime MIA HE 25"
  boiler_type                TEXT      -- e.g. "C13"
  power_kw                    TEXT
  flow_m3h                    TEXT
  technology                  TEXT      -- e.g. "Συμπύκνωσης"
  meter_type                  TEXT      -- e.g. "G4"
  meter_position               TEXT
  regulator_pressure_mbar     TEXT
  strength_test_design_pressure_mbar    TEXT   -- e.g. 1000
  tightness_test_design_pressure_mbar   TEXT   -- e.g. 110
  visit_date        TEXT              -- maintenance/inspection/test date entered at generation time
  test_start_time   TEXT              -- only relevant for document_type = strength_tightness_test
  test_end_time     TEXT
  pass_fail         TEXT              -- "pass" | "fail"
  next_maintenance_date          TEXT -- computed: visit_date + 1 year (used by maintenance_program doc)
  next_tightness_recheck_date    TEXT -- computed: visit_date + 4 years (used by maintenance_program doc)
  output_pdf_path    TEXT             -- where the rendered PDF was last written
  generated_at        TEXT
```

All text-like identifier fields (`phone`, `application_no`, `hkasp`, and all the *_mbar/_kw/_m3h fields) are stored as **TEXT**, never INTEGER/REAL — this was a hard-won lesson from inspecting the original `Customers.ods` XML directly: those same fields were stored there as `office:value-type="float"`, which risks scientific notation and precision/formatting corruption. SQLite's dynamic typing makes this an easy mistake to reintroduce (SQLite will happily let you insert a number into a TEXT column with no complaint if the Python layer doesn't explicitly cast to `str` first) — the data access layer must always pass Python `str` for these fields, never bare numeric literals.

### One-time migration from `Customers.ods`

A one-off script (`migrate_from_ods.py`, run once during development, not shipped as a runtime feature) imports the 5 existing rows:
- Reads `Customers.ods` via `odfpy` + `odf.teletype.extractText(cell)` (same safe-extraction approach validated earlier — handles the rich-text `address` field and the float-typed numeric-looking cells correctly).
- For each row: inserts one `customers` row (name, address, phone) and one seed `projects` row with just a `name` label (e.g. "Αίτηση 6756", derived from the old sheet's Αρ. Αίτησης) — Project no longer stores installation/boiler/meter details itself.
- The old sheet's Αρ. Αίτησης/ΗΚΑΣΠ and all installation/boiler/meter fields (not present in the old sheet) are **not** carried onto Project; they're entered later via the export wizard the first time a document is actually generated for that project (see "Projects become just a name" below).
- `odfpy` is therefore only a **one-time migration dependency** — not needed at runtime once the SQLite DB exists, and not bundled into the shipped `.exe`.

## Recommended stack

- **Python 3 + Tkinter** (stdlib, ships with the Windows python.org installer — no extra GUI dependency).
- **`sqlite3`** (stdlib) for the data layer — no ORM needed for a 3-table schema; a thin `data_store.py` with plain parameterized SQL (`?` placeholders, never string-interpolated values) is enough and keeps the dependency footprint at zero for the DB layer itself.
- **Jinja2 + `tectonic`** for PDF document generation (unchanged from the earlier Excel-era plan — this part of the design doesn't depend on where the field values are stored). See "Document export feature" below.
- **PyInstaller**, built on a **Windows CI runner** (GitHub Actions `windows-latest`) — PyInstaller cannot cross-compile a Windows executable from Linux. SQLite needs zero special packaging (it's stdlib + a single `.db` file shipped/created next to the exe); `tectonic.exe` + bundled fonts do need to be bundled as PyInstaller data files.
- **DB file location**: `customers.db` kept **next to the executable** (portable, easy to back up/inspect — matches the transparency the user had with the old Excel file) rather than hidden away in `%APPDATA%`.

## File/module layout

```
armen_crm/
├── CLAUDE.md                # this roadmap
├── customers.db             # SQLite database (created on first run if missing; pre-seeded copy shipped after migration)
├── migrate_from_ods.py      # one-off dev-time script: Customers.ods -> customers.db (not shipped as a runtime feature)
├── Customers.ods            # kept as historical reference / migration source only
├── requirements.txt         # Jinja2  (odfpy is a dev-only extra, only needed to run migrate_from_ods.py once)
├── main.py                  # entry point: Tk root, App(), mainloop, creates schema if customers.db is missing
├── schema.sql               # CREATE TABLE statements for customers/projects/templates
├── data_store.py            # sqlite3-based CRUD for Customer/Project/Template (no Tkinter imports)
├── gui.py                   # App class: Customers list -> Projects panel -> Templates/export panel
├── customer_dialog.py       # modal Add/Edit Toplevel form for a Customer
├── project_dialog.py        # modal Add/Edit Toplevel form for a Project (just a name)
├── business_info.py         # hardcoded constants: engineer/installer business details (name, TEE #, license #, expiry, address, phone)
├── documents.py             # render context + Jinja2 render + tectonic invoke + output/ placement
├── wizard.py                # Toplevel dialog collecting a new Template's per-generation fields (installation/boiler/meter details, visit date, test times, pass/fail)
├── templates/
│   ├── compliance.tex.j2
│   ├── strength_tightness_test.tex.j2
│   ├── maintenance_program.tex.j2
│   └── technical_report.tex.j2
├── assets/fonts/            # bundled Unicode Greek-supporting font for tectonic/fontspec
├── 1-ΠΙΣΤΟΠΟΙΗΤΙΚΟ-ΤΗΡΗΣΗΣ-ΑΠΑΙΤ-ΚΑΝΟΝΙΣΜΟΥ_38452.doc    # original templates, kept as reference for the .tex.j2 conversion
├── 2-ΠΙΣΤΟΠΟΙΗΤΙΚΟ-ΔΟΚΙΜΗΣ-ΑΝΤΟΧΗΣ-ΚΑΙ-ΣΤΕΓΑΝΟΤΗΤΑΣ_38452.doc
├── 3-ΠΡΟΓΡΑΜΜΑ-ΛΕΙΤΟΥΡΓΙΑΣ-ΣΥΝΤΗΡΗΣΗΣ_38452.docx
├── 4-ΤΕΧΝΙΚΗ ΕΚΘΕΣΗ 38452.docx
├── output/                  # generated PDFs: output/<customer_name>/<project_id>/<document_type>.pdf
├── tests/
│   └── test_data_store.py   # CRUD + cascade smoke tests against an in-memory/temp SQLite DB
└── .github/workflows/
    └── build-windows.yml    # PyInstaller build on windows-latest, uploads ArmenCRM.exe (bundles tectonic.exe + fonts)
```

## Key design decisions

1. **All identifier-like fields are Python `str` end-to-end**, in both the SQLite schema (TEXT columns) and the data access layer — never cast to int/float — carrying forward the exact lesson learned from the original `Customers.ods` float-corruption risk.
2. **Three-level GUI navigation**: Customers list (top) → select a customer to see their Projects → select a project to see/generate its Templates (documents). Each level is a `ttk.Treeview` panel; selecting a row in one panel filters the panel below it.
3. **Foreign keys enforced**: `PRAGMA foreign_keys = ON` at every connection open; deleting a customer cascades to delete their projects and templates (with a confirmation dialog warning how many projects/templates will be removed).
4. **Save strategy**: standard CRUD — each Add/Edit dialog commits immediately on OK (no separate explicit "Save" step needed once there's a real transactional DB underneath, unlike the old single-file-overwrite ODS design). Each write is a single committed SQL transaction.
5. **Document generation is itself a data-creating action**: clicking "Generate" in the wizard both (a) inserts a new `templates` row (so there's a durable history of every certificate ever produced for a project, including computed next-maintenance/next-recheck dates) and (b) renders the PDF via Jinja2 → tectonic.
6. **Business-constant fields** (engineer Κωνσταντίνος Άρμεν's name, TEE registration #165387, installer registration #2584, business address/phone, license expiry) are hardcoded in `business_info.py`, not stored per-customer/project — recommended default since this data essentially never changes; revisit only if the user later wants it editable without a code change.
7. **Windows packaging**: GitHub Actions `windows-latest` builds the `.exe` via PyInstaller (`--onefile --noconsole`), bundling `tectonic.exe` and the Greek-supporting font as data files; `customers.db` + `schema.sql` ship alongside (or the schema is created on first run if the DB file is missing).
8. **Projects become just a name**: installation/boiler/meter/pressure details (application_no, hkasp, installation_address, boiler specs, meter info, pressures) were originally stored once on `projects`. The user decided these can legitimately change between visits for the same project (boiler swapped, re-test at a different pressure, etc.), so they now live on `templates` instead and are re-entered via the export wizard **every time a document is generated** — Project is reduced to `id`/`customer_id`/`name`/`created_at`, a lightweight label for grouping a customer's certificates. This trades a bit of re-typing for correctness: each generated PDF is self-contained and historically accurate even if the installation changes later.

## Document export feature (4 real templates, LaTeX-based)

Four example templates already exist at the repo root, all for the same example customer ("Άλντο Μότσκα", application #6756/38452). Their text was inspected directly (`antiword` for the 2 legacy `.doc` files, `python-docx` for the 2 `.docx` files):

1. `1-ΠΙΣΤΟΠΟΙΗΤΙΚΟ-ΤΗΡΗΣΗΣ-ΑΠΑΙΤ-ΚΑΝΟΝΙΣΜΟΥ_38452.doc` — Compliance Certificate (`document_type = compliance`)
2. `2-ΠΙΣΤΟΠΟΙΗΤΙΚΟ-ΔΟΚΙΜΗΣ-ΑΝΤΟΧΗΣ-ΚΑΙ-ΣΤΕΓΑΝΟΤΗΤΑΣ_38452.doc` — Strength & Tightness Test Certificate (`strength_tightness_test`)
3. `3-ΠΡΟΓΡΑΜΜΑ-ΛΕΙΤΟΥΡΓΙΑΣ-ΣΥΝΤΗΡΗΣΗΣ_38452.docx` — Maintenance Operation Program (`maintenance_program`)
4. `4-ΤΕΧΝΙΚΗ ΕΚΘΕΣΗ 38452.docx` — Technical Report (`technical_report`)

Every variable in these documents maps to one of: a `customers` field, a `templates` (per-generation, including installation/boiler/meter details) field, or a `business_info.py` constant — see the Data model section above for the exact split. Notably:
- mmHg pressure readings in document 2 are **computed** at render time from the stored mbar design pressures (1 mbar ≈ 0.750062 mmHg) — not stored separately.
- `next_maintenance_date` (+1 year) and `next_tightness_recheck_date` (+4 years, per the regulation text in template 3) are **computed** from `visit_date` when a `templates` row is inserted, and stored (so the maintenance-program table doesn't need to recompute historical values later if the computation logic ever changes).

### Architecture

- **Convert each template to a LaTeX template** (`templates/*.tex.j2`) using **Jinja2 with LaTeX-safe custom delimiters** (`\VAR{...}` for variables, `\BLOCK{...}` for control flow) and a LaTeX-escaping autoescape filter for every substituted string (escape `& % $ # _ { } ~ ^ \`).
- **LaTeX engine: `tectonic`**, not MiKTeX — single self-contained binary (no multi-GB TeX Live/MiKTeX install), XeTeX-based so it has first-class Unicode support via `fontspec`, needed since all 4 templates are Greek text, and far easier to bundle alongside a PyInstaller `.exe`. Use `fontspec` + a bundled open Greek-supporting font (e.g. Noto Serif/DejaVu Serif) under `assets/fonts/` so rendering doesn't depend on fonts already present on the Windows machine.
- **`documents.py`**: builds the render context (joins the selected `Project`'s row + its parent `Customer` row + the new `Template` row just created by the wizard, which carries all installation/boiler/meter details + `business_info` constants + computed mmHg/date values), renders the matching `.tex.j2`, writes to a temp `.tex`, invokes `tectonic`, moves the result to `output/<customer_name>/<project_id>/<document_type>.pdf`, and records that path back onto the `templates` row.
- **`wizard.py`**: Tkinter `Toplevel` collecting all of the `templates` row's per-generation fields — installation/boiler/meter/pressure details, plus visit date, test start/end time if generating the test certificate, and pass/fail — before creating the `templates` row.
- **GUI integration**: with a project selected, an "Export Document" action opens a checklist of the 4 document types, then the wizard, then generates the selected PDFs.

## Ordered roadmap (what CLAUDE.md should list as milestones)

1. **Scaffolding** — `requirements.txt` (Jinja2; odfpy as a dev-only extra), dev shell notes (Tk-enabled Python on NixOS requires `pkgs.python311Full` or `pkgs.python311.withPackages (ps: [ps.tkinter])`), this `CLAUDE.md`.
2. **Schema + data layer** — `schema.sql` (customers/projects/templates, foreign keys), `data_store.py` CRUD functions, `PRAGMA foreign_keys = ON`, cascade-delete behavior; smoke tests against a temp DB file.
3. **Migration** — `migrate_from_ods.py`: import the 5 existing `Customers.ods` rows into `customers` + one seed `projects` row each; run once, commit the resulting `customers.db`.
4. **GUI skeleton** — `main.py` + `gui.py`: three-panel layout (Customers → Projects → Templates), populated read-only first (no wiring).
5. **CRUD wiring** — `customer_dialog.py`, `project_dialog.py` fully wired (Add/Edit/Delete with cascade-delete confirmation at the customer level).
6. **Document templates** — convert the 4 `.doc`/`.docx` files to `templates/*.tex.j2`; validate rendering with `tectonic` locally (via `nix-shell -p tectonic` on this dev machine) using the example customer's data, compare against the originals for fidelity (Greek text, layout).
7. **Document generation wiring** — `business_info.py` constants, `wizard.py`, `documents.py` end-to-end: select project → choose document(s) → fill wizard → generate → PDFs land in `output/...` → new `templates` rows recorded.
8. **Search** — live-filter across customers (and optionally projects).
9. **Polish & packaging** — README with run instructions; `.github/workflows/build-windows.yml` (PyInstaller, bundling `tectonic.exe` + fonts); manual end-to-end verification on an actual Windows machine.

## Verification (once implementation begins in a later session)

- Run the data-layer smoke tests (CRUD + cascade delete) against a temp SQLite file.
- Run `migrate_from_ods.py` against the real `Customers.ods` and confirm 5 customers + 5 seed projects (name-only) are created, with exact-string `phone` values (no `.0` suffix, no scientific notation).
- Launch `main.py` locally (Linux dev shell with Tk-enabled Python) and exercise the full GUI: add/edit/delete a customer, add/edit a project (name only), generate all 4 documents for the example project via the wizard (entering installation/boiler/meter details + visit date/test fields each time), confirm `output/Άλντο Μότσκα/<project_id>/` contains 4 correctly-rendered PDFs (Greek text renders cleanly, no missing glyphs/mojibake, values match the original templates) and `hkasp`/`application_no`/pressure fields remain exact-string on the `templates` row (no `.0` suffix, no scientific notation).
- After the Windows CI build, smoke-test the produced `.exe` on an actual Windows machine: app launches, DB creates/opens correctly next to the exe, document generation produces valid PDFs (tectonic + bundled fonts work without any pre-installed LaTeX distribution on the target machine).

## Status

Milestones 1-9 implemented and verified on Linux (dev shell):
- Schema/data layer: 5 passing tests (`tests/test_data_store.py`), including the
  float-corruption and cascade-delete guards.
- Migration: `migrate_from_ods.py` run once against the real `Customers.ods`;
  `customers.db` committed is pre-seeded with the 5 real customers + 5 seed
  projects (exact-string `phone`, verified).
- GUI: three-panel Customers -> Projects -> Templates app, full CRUD, live search
  on both Customers and Projects, all exercised via scripted Tkinter smoke tests
  (see conversation history) plus a real screenshot.
- Documents: all 4 templates converted to `templates/*.tex.j2`, rendered with
  Jinja2 + compiled with `tectonic`, verified end-to-end through the actual
  GUI/DB code path -- output lands at `output/<customer>/<project_id>/<type>.pdf`
  and a `templates` history row is recorded per generation.
- Packaging: `.github/workflows/build-windows.yml` written (PyInstaller +
  tectonic.exe v0.17.0 from the tectonic GitHub release + bundled fonts/templates).

**Schema change (2026-10-07):** Project was reduced to just `id`/`customer_id`/
`name`/`created_at`. All installation/boiler/meter/pressure fields
(application_no, hkasp, installation_address, boiler specs, meter info,
regulator/strength/tightness pressures) moved from `projects` onto `templates`,
since the user decided those can change between visits/certificates for the
same project and should be re-entered via the export wizard every generation
rather than stored once. `project_dialog.py` is now a single-field dialog;
`wizard.py` grew a grid of installation-field entries; all 4 `.tex.j2`
templates were updated to read these from `template.*` instead of `project.*`;
`customers.db` was regenerated from `migrate_from_ods.py` against the new
schema (seed projects are now named e.g. "Αίτηση 6756" instead of carrying
application_no/hkasp directly). Verified end-to-end: all 4 document types
render and compile to PDF successfully against the new schema, and the full
test suite passes.

**Not yet done / open risk:** the Windows CI build has not actually been run,
and nothing here has been tested on real Windows hardware. The last attempted
build produced no `.exe` artifact at all — `upload-artifact`'s default
`if-no-files-found: warn` let the job report green even though `dist/ArmenCRM.exe`
was apparently never produced; the actual PyInstaller failure log has not yet
been captured. The `BASE_DIR` vs
`app_dir()` distinction in `documents.py`/`paths.py` (bundled read-only
resources vs. the real .exe's directory) is believed correct for a PyInstaller
`--onefile` build but is unverified in practice -- treat that as the first
thing to check if the built `.exe` fails to find `tectonic.exe` or the fonts.
