"""Layer 1: registration + lookup. Loads the fixture sales data,
looks a customer up by phone, computes warranty status.

Warranty math lives here, not in the agent (Layer 2) and not
duplicated in a test script -- moved here from
scripts/test_agent_grounding.py once it became the real module,
per DESIGN.md's honesty rule: the model must never compute this.
"""

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

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
    """Deterministic date math, per product type. Washing machines
    (product_id starts WM-) get a 2-year motor warranty; ACs (AC-)
    get a 5-year compressor warranty. Both get 1 year on other parts.
    Returns (component, component_years, component_status, parts_status)."""
    purchased = datetime.strptime(purchase_date, "%Y-%m-%d").date()
    today = date.today()
    if product_id.startswith("WM-"):
        component, years = "motor", 2
    else:
        component, years = "compressor", 5
    component_status = "active" if today < _add_years(purchased, years) else "expired"
    parts_status = "active" if today < _add_years(purchased, 1) else "expired"
    return component, years, component_status, parts_status


def load_registrations(path: Path = SALES_DATA) -> list[Registration]:
    registrations = []
    with open(path) as f:
        for row in csv.DictReader(f):
            component, years, component_status, parts_status = compute_warranty_status(
                row["purchase_date"], row["product_id"]
            )
            registrations.append(
                Registration(
                    customer_name=row["customer_name"],
                    customer_phone=row["customer_phone"],
                    product_id=row["product_id"],
                    product_name=row["product_name"],
                    serial_number=row["serial_number"],
                    purchase_date=row["purchase_date"],
                    retailer=row["retailer"],
                    purchase_price=int(row["purchase_price"]),
                    warranty_component=component,
                    warranty_component_years=years,
                    warranty_component_status=component_status,
                    warranty_parts_status=parts_status,
                )
            )
    return registrations


def lookup_by_phone(phone: str, registrations: list[Registration] | None = None) -> list[Registration]:
    """All products a customer has registered, by phone number --
    this is the moment Aftercare actually delivers on: the customer
    messages, and we already know what they bought."""
    registrations = registrations if registrations is not None else load_registrations()
    return [r for r in registrations if r.customer_phone == phone]
