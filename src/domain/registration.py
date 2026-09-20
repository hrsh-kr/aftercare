"""Layer 1: registration + lookup. Loads the fixture sales data,
looks a customer up by phone, computes warranty status.

Warranty math lives here, not in the agent (Layer 2) and not
duplicated in a test script -- moved here from
scripts/test_agent_grounding.py once it became the real module,
honesty rule: the model must never compute this.
"""

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from src.domain.catalog import warranty_component_for

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures"
SALES_DATA = FIXTURES / "sales_data.csv"


@dataclass
class Registration:
    customer_name: str
    customer_phone: str
    product_id: str
    product_name: str
    serial_number: str
    purchase_date: str
    retailer: str
    purchase_price: int
    warranty_component: str  # "motor" or "compressor", per product type
    warranty_component_years: int
    warranty_component_status: str  # active / expired
    warranty_parts_status: str  # active / expired


def _add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # Feb 29 on a non-leap target year
        return d.replace(month=2, day=28, year=d.year + years)


def compute_warranty_status(purchase_date: str, product_id: str) -> tuple[str, int, str, str]:
    """Deterministic date math, per product type (see catalog.py's
    WARRANTY_BY_PREFIX -- e.g. washing machines get a 2-year motor
    warranty, ACs a 5-year compressor warranty). Every product also
    gets a flat 1-year parts warranty. Returns (component,
    component_years, component_status, parts_status)."""
    purchased = datetime.strptime(purchase_date, "%Y-%m-%d").date()
    today = date.today()
    component, years = warranty_component_for(product_id)
    component_status = "active" if today < _add_years(purchased, years) else "expired"
    parts_status = "active" if today < _add_years(purchased, 1) else "expired"
    return component, years, component_status, parts_status


def registration_from_row(row: dict) -> Registration:
    """A stored or CSV row -> Registration. Warranty status is computed here, at read time, from the
    purchase date and today's date, so it is never stale and never stored."""
    component, years, component_status, parts_status = compute_warranty_status(row["purchase_date"], row["product_id"])
    return Registration(
        customer_name=row["customer_name"], customer_phone=row["customer_phone"], product_id=row["product_id"],
        product_name=row["product_name"], serial_number=row["serial_number"], purchase_date=row["purchase_date"],
        retailer=row["retailer"], purchase_price=int(row["purchase_price"]), warranty_component=component,
        warranty_component_years=years, warranty_component_status=component_status, warranty_parts_status=parts_status,
    )


def load_registrations(path: Path = SALES_DATA) -> list[Registration]:
    """Read a sales CSV from disk. Used by bootstrap (to load the baseline registry into DynamoDB) and by
    the landing page's Step 0 table. The running app reads registrations from the registry, not from here."""
    with open(path) as f:
        return [registration_from_row(row) for row in csv.DictReader(f)]


def warranty_details(reg: Registration, today: date | None = None) -> dict:
    """Everything a warranty answer needs, computed here (never by the model): purchase date, the
    component warranty and the flat 1-year parts warranty, each with its end date, status and days left."""
    today = today or date.today()
    purchased = datetime.strptime(reg.purchase_date, "%Y-%m-%d").date()

    def one(label: str, years: int) -> dict:
        end = _add_years(purchased, years)
        return {"label": label, "years": years, "ends": end.isoformat(), "active": today < end, "days_left": (end - today).days}

    return {"purchased": purchased.isoformat(), "coverage": [one(reg.warranty_component, reg.warranty_component_years), one("other parts", 1)]}


def mask_phone(phone: str) -> str:
    """+919876543210 -> '+91 98765 \u00b7\u00b7\u00b7\u00b7\u00b7'"""
    digits = phone.lstrip("+")
    if len(digits) == 12 and digits.startswith("91"):
        return f"+91 {digits[2:7]} \u00b7\u00b7\u00b7\u00b7\u00b7"
    return phone[:4] + " \u00b7\u00b7\u00b7\u00b7\u00b7"
