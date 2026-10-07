"""SQLite-backed data access layer for Customer -> Project -> Template.

All identifier-like fields (phone, application_no, hkasp, the *_mbar/_kw/_m3h
fields, dates) are always passed through as Python str. Never pass a bare
int/float into these functions for those fields -- SQLite's dynamic typing
will happily store a number in a TEXT column, reintroducing the exact
float-corruption risk this schema was designed to avoid.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def _s(value) -> Optional[str]:
    """Coerce to str, preserving None. Use for every field written to the DB."""
    return None if value is None else str(value)


def add_years(iso_date: str, years: int) -> str:
    """Add `years` to an ISO date string (YYYY-MM-DD), clamping Feb 29 -> Feb 28."""
    d = date.fromisoformat(iso_date)
    try:
        return d.replace(year=d.year + years).isoformat()
    except ValueError:
        # Feb 29 on a non-leap target year
        return d.replace(year=d.year + years, day=28).isoformat()


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------

@dataclass
class Customer:
    id: Optional[int]
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None


def list_customers(conn: sqlite3.Connection) -> list[Customer]:
    rows = conn.execute("SELECT id, name, address, phone FROM customers ORDER BY name").fetchall()
    return [Customer(**dict(r)) for r in rows]


def get_customer(conn: sqlite3.Connection, customer_id: int) -> Optional[Customer]:
    row = conn.execute(
        "SELECT id, name, address, phone FROM customers WHERE id = ?", (customer_id,)
    ).fetchone()
    return Customer(**dict(row)) if row else None


def create_customer(conn: sqlite3.Connection, name: str, address: str = None, phone: str = None) -> int:
    cur = conn.execute(
        "INSERT INTO customers (name, address, phone) VALUES (?, ?, ?)",
        (_s(name), _s(address), _s(phone)),
    )
    conn.commit()
    return cur.lastrowid


def update_customer(conn: sqlite3.Connection, customer_id: int, name: str, address: str = None, phone: str = None) -> None:
    conn.execute(
        "UPDATE customers SET name = ?, address = ?, phone = ? WHERE id = ?",
        (_s(name), _s(address), _s(phone), customer_id),
    )
    conn.commit()


def delete_customer(conn: sqlite3.Connection, customer_id: int) -> None:
    """Cascades to delete the customer's projects and their templates (ON DELETE CASCADE)."""
    conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    conn.commit()


def count_descendants(conn: sqlite3.Connection, customer_id: int) -> tuple[int, int]:
    """Return (project_count, template_count) that would be cascade-deleted with this customer."""
    project_count = conn.execute(
        "SELECT COUNT(*) FROM projects WHERE customer_id = ?", (customer_id,)
    ).fetchone()[0]
    template_count = conn.execute(
        "SELECT COUNT(*) FROM templates WHERE project_id IN (SELECT id FROM projects WHERE customer_id = ?)",
        (customer_id,),
    ).fetchone()[0]
    return project_count, template_count


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

@dataclass
class Project:
    id: Optional[int]
    customer_id: int
    name: str
    created_at: Optional[str] = None


def list_projects_for_customer(conn: sqlite3.Connection, customer_id: int) -> list[Project]:
    rows = conn.execute(
        "SELECT * FROM projects WHERE customer_id = ? ORDER BY id", (customer_id,)
    ).fetchall()
    return [Project(**dict(r)) for r in rows]


def get_project(conn: sqlite3.Connection, project_id: int) -> Optional[Project]:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return Project(**dict(row)) if row else None


def create_project(conn: sqlite3.Connection, customer_id: int, name: str) -> int:
    cur = conn.execute(
        "INSERT INTO projects (customer_id, name) VALUES (?, ?)", (customer_id, _s(name))
    )
    conn.commit()
    return cur.lastrowid


def update_project(conn: sqlite3.Connection, project_id: int, name: str) -> None:
    conn.execute("UPDATE projects SET name = ? WHERE id = ?", (_s(name), project_id))
    conn.commit()


def delete_project(conn: sqlite3.Connection, project_id: int) -> None:
    """Cascades to delete the project's templates (ON DELETE CASCADE)."""
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Template (one generated document instance)
# ---------------------------------------------------------------------------

# Installation/boiler/meter details -- these used to live on Project, but
# since they can change between visits/certificates for the same project,
# they're entered per-generation (via the export wizard) and stored here.
INSTALLATION_FIELDS = [
    "application_no", "hkasp", "installation_address", "access_street",
    "property_use", "gas_use", "boiler_brand_model", "boiler_type",
    "power_kw", "flow_m3h", "technology", "meter_type", "meter_position",
    "regulator_pressure_mbar", "strength_test_design_pressure_mbar",
    "tightness_test_design_pressure_mbar",
]


@dataclass
class Template:
    id: Optional[int]
    project_id: int
    document_type: str
    application_no: Optional[str] = None
    hkasp: Optional[str] = None
    installation_address: Optional[str] = None
    access_street: Optional[str] = None
    property_use: Optional[str] = None
    gas_use: Optional[str] = None
    boiler_brand_model: Optional[str] = None
    boiler_type: Optional[str] = None
    power_kw: Optional[str] = None
    flow_m3h: Optional[str] = None
    technology: Optional[str] = None
    meter_type: Optional[str] = None
    meter_position: Optional[str] = None
    regulator_pressure_mbar: Optional[str] = None
    strength_test_design_pressure_mbar: Optional[str] = None
    tightness_test_design_pressure_mbar: Optional[str] = None
    visit_date: Optional[str] = None
    test_start_time: Optional[str] = None
    test_end_time: Optional[str] = None
    pass_fail: Optional[str] = None
    next_maintenance_date: Optional[str] = None
    next_tightness_recheck_date: Optional[str] = None
    output_pdf_path: Optional[str] = None
    generated_at: Optional[str] = None


def list_templates_for_project(conn: sqlite3.Connection, project_id: int) -> list[Template]:
    rows = conn.execute(
        "SELECT * FROM templates WHERE project_id = ? ORDER BY id", (project_id,)
    ).fetchall()
    return [Template(**dict(r)) for r in rows]


def get_template(conn: sqlite3.Connection, template_id: int) -> Optional[Template]:
    row = conn.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()
    return Template(**dict(row)) if row else None


def create_template(
    conn: sqlite3.Connection,
    project_id: int,
    document_type: str,
    visit_date: str,
    test_start_time: str = None,
    test_end_time: str = None,
    pass_fail: str = None,
    **installation_fields,
) -> int:
    """Insert a new generated-document record, computing the derived dates.

    installation_fields accepts any subset of INSTALLATION_FIELDS (the
    installation/boiler/meter details collected by the export wizard)."""
    next_maintenance_date = add_years(visit_date, 1)
    next_tightness_recheck_date = add_years(visit_date, 4)
    cols = (
        ["project_id", "document_type"] + INSTALLATION_FIELDS
        + ["visit_date", "test_start_time", "test_end_time", "pass_fail",
           "next_maintenance_date", "next_tightness_recheck_date"]
    )
    values = (
        [project_id, _s(document_type)]
        + [_s(installation_fields.get(f)) for f in INSTALLATION_FIELDS]
        + [_s(visit_date), _s(test_start_time), _s(test_end_time), _s(pass_fail),
           next_maintenance_date, next_tightness_recheck_date]
    )
    placeholders = ", ".join("?" for _ in cols)
    cur = conn.execute(
        f"INSERT INTO templates ({', '.join(cols)}) VALUES ({placeholders})", values
    )
    conn.commit()
    return cur.lastrowid


def set_template_output_path(conn: sqlite3.Connection, template_id: int, output_pdf_path: str) -> None:
    conn.execute(
        "UPDATE templates SET output_pdf_path = ? WHERE id = ?", (_s(output_pdf_path), template_id)
    )
    conn.commit()


def delete_template(conn: sqlite3.Connection, template_id: int) -> None:
    conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
    conn.commit()
