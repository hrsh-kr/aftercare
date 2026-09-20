"""The website's pages, rendered inside the Lambda (Jinja2). No web framework: API Gateway hands
the request to the function, the function returns HTML. Static files (CSS/JS) are served by
API Gateway locally via `sam local start-api --static-dir`; in an account they would sit in S3
behind CloudFront."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.layer1.catalog import BRAND_SLUGS, brand_for
from src.layer1.registration import load_registrations
from src.webapp import api_core as core

_env = Environment(
    loader=FileSystemLoader(str(Path(__file__).resolve().parent / "webapp" / "templates")),
    autoescape=select_autoescape(["html"]),
)


def landing() -> str:
    """Step 0 renders the real fixture rows (phones masked), the brand each product code maps to
    (catalog.py) and real per-brand counts -- nothing invented."""
    regs = load_registrations()
    rows = [
        {"customer": r.customer_name, "phone": core.mask_phone(r.customer_phone), "product": r.product_name,
         "serial": r.serial_number, "purchased": r.purchase_date, "brand": brand_for(r.product_id)}
        for r in regs
    ]
    by_brand: dict[str, dict] = {}
    for r in regs:
        name = brand_for(r.product_id)
        entry = by_brand.setdefault(name, {"name": name, "slug": name.lower(), "products": 0, "phones": set()})
        entry["products"] += 1
        entry["phones"].add(r.customer_phone)
    brand_stats = [{"name": e["name"], "slug": e["slug"], "products": e["products"], "customers": len(e["phones"])}
                   for e in sorted(by_brand.values(), key=lambda e: e["name"])]
    stats = {"products": len(regs), "customers": len({r.customer_phone for r in regs}), "brands": len(brand_stats)}
    return _env.get_template("landing.html").render(rows=rows, stats=stats, brand_stats=brand_stats)


def demo() -> str:
    return _env.get_template("demo.html").render()


def dashboard_login() -> str:
    from src.authz import session
    return _env.get_template("dashboard_login.html").render(staff=session.staff_directory(), brands=BRAND_SLUGS)


def dashboard(brand: str) -> str | None:
    brand = brand.strip().lower()
    if brand not in BRAND_SLUGS:
        return None
    others = [(k, v) for k, v in BRAND_SLUGS.items() if k != brand]
    return _env.get_template("dashboard.html").render(brand=brand, brand_display=BRAND_SLUGS[brand], others=others)


def sandbox() -> str:
    return _env.get_template("sandbox.html").render()
