"""One-off migration: import the legacy Customers.ods rows into customers.db.

Run once during development (not shipped as a runtime feature of the app):

    python migrate_from_ods.py [Customers.ods] [customers.db]

Requires odfpy (dev-only dependency -- see requirements-dev.txt).

Reads every cell via odf.teletype.extractText(), never cell.value, because
the ΗΚΑΣΠ/Αρ. Αίτησης/τηλ. columns are stored as office:value-type="float"
in the source file and the Διεύθυνση column uses split text:span runs --
both confirmed by inspecting the raw ODS XML directly. extractText() reads
the cell's rendered text regardless of value-type or span structure, which
sidesteps both problems at the source.
"""
from __future__ import annotations

import sys
from pathlib import Path

from odf.opendocument import load
from odf.table import Table, TableRow, TableCell
from odf.teletype import extractText

import data_store as ds

NS_TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"


def read_customers_from_ods(ods_path: str) -> list[dict]:
    doc = load(ods_path)
    tables = doc.getElementsByType(Table)
    rows = tables[0].getElementsByType(TableRow)

    customers = []
    for row in rows[1:]:  # skip header row
        cells = row.getElementsByType(TableCell)
        values = [extractText(c).strip() for c in cells]
        # pad in case a row has fewer populated cells than the header
        values += [""] * (6 - len(values))
        _, name, address, application_no, hkasp, phone = values[:6]
        if not any([name, address, application_no, hkasp, phone]):
            continue  # trailing blank row
        customers.append(
            {
                "name": name,
                "address": address,
                "phone": phone,
                "application_no": application_no,
                "hkasp": hkasp,
            }
        )
    return customers


def migrate(ods_path: str, db_path: str) -> int:
    customers = read_customers_from_ods(ods_path)

    conn = ds.connect(db_path)
    ds.init_db(conn)
    try:
        for row in customers:
            customer_id = ds.create_customer(
                conn, name=row["name"], address=row["address"], phone=row["phone"]
            )
            ds.create_project(
                conn,
                customer_id,
                application_no=row["application_no"],
                hkasp=row["hkasp"],
            )
        return len(customers)
    finally:
        conn.close()


if __name__ == "__main__":
    ods_path = sys.argv[1] if len(sys.argv) > 1 else "Customers.ods"
    db_path = sys.argv[2] if len(sys.argv) > 2 else "customers.db"

    if not Path(ods_path).exists():
        sys.exit(f"Source file not found: {ods_path}")
    if Path(db_path).exists():
        sys.exit(f"{db_path} already exists -- refusing to overwrite. Delete it first if you want to re-migrate.")

    count = migrate(ods_path, db_path)
    print(f"Migrated {count} customers (+ 1 seed project each) from {ods_path} into {db_path}")
