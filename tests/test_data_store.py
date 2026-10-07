import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import data_store as ds


@pytest.fixture
def conn(tmp_path):
    db_path = tmp_path / "test.db"
    c = ds.connect(str(db_path))
    ds.init_db(c)
    yield c
    c.close()


def test_customer_crud(conn):
    cid = ds.create_customer(conn, "Άλντο Μότσκα", "Αδριανουπόλεως 37, 66100 Δράμα", "6941434801")
    customer = ds.get_customer(conn, cid)
    assert customer.name == "Άλντο Μότσκα"
    assert customer.phone == "6941434801"

    ds.update_customer(conn, cid, "Άλντο Μότσκα Updated", customer.address, customer.phone)
    assert ds.get_customer(conn, cid).name == "Άλντο Μότσκα Updated"

    assert len(ds.list_customers(conn)) == 1
    ds.delete_customer(conn, cid)
    assert ds.list_customers(conn) == []


def test_phone_and_hkasp_never_numeric(conn):
    """Guard against the float-corruption bug found in the original Customers.ods."""
    cid = ds.create_customer(conn, "Test", phone="30090000006756")
    customer = ds.get_customer(conn, cid)
    assert customer.phone == "30090000006756"
    assert isinstance(customer.phone, str)

    pid = ds.create_project(conn, cid, name="Αίτηση 6756")
    tid = ds.create_template(
        conn, pid, "compliance", visit_date="2026-09-12",
        hkasp="30090000006756", application_no="6756",
    )
    template = ds.get_template(conn, tid)
    assert template.hkasp == "30090000006756"
    assert template.application_no == "6756"
    assert isinstance(template.hkasp, str)
    assert isinstance(template.application_no, str)


def test_project_crud_and_cascade(conn):
    cid = ds.create_customer(conn, "Customer A")
    pid = ds.create_project(conn, cid, name="Αίτηση 123")
    project = ds.get_project(conn, pid)
    assert project.name == "Αίτηση 123"

    assert len(ds.list_projects_for_customer(conn, cid)) == 1

    tid = ds.create_template(
        conn, pid, "compliance", visit_date="2026-09-12",
        boiler_brand_model="Sime MIA HE 25",
    )
    template = ds.get_template(conn, tid)
    assert template.boiler_brand_model == "Sime MIA HE 25"
    assert template.next_maintenance_date == "2027-09-12"
    assert template.next_tightness_recheck_date == "2030-09-12"

    project_count, template_count = ds.count_descendants(conn, cid)
    assert project_count == 1
    assert template_count == 1

    # cascade delete: deleting the customer removes the project and template
    ds.delete_customer(conn, cid)
    assert ds.get_project(conn, pid) is None
    assert ds.get_template(conn, tid) is None


def test_add_years_handles_leap_day():
    assert ds.add_years("2024-02-29", 1) == "2025-02-28"
    assert ds.add_years("2026-09-12", 4) == "2030-09-12"


def test_set_template_output_path(conn):
    cid = ds.create_customer(conn, "Customer B")
    pid = ds.create_project(conn, cid, name="Project B")
    tid = ds.create_template(conn, pid, "technical_report", visit_date="2026-01-01")
    ds.set_template_output_path(conn, tid, "/output/Customer B/1/technical_report.pdf")
    template = ds.get_template(conn, tid)
    assert template.output_pdf_path == "/output/Customer B/1/technical_report.pdf"
