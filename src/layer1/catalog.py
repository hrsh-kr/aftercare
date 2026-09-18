"""The product catalog: which brand owns which product-id prefix, where
its manual/terms live, and its warranty terms. One source of truth --
this used to be defined three different ways in three different files
(agent.py's own copy, cedar_authz.py's KNOWN_BRANDS, opensearch_retrieval
.py's ALL_DOCS), found during a full audit and consolidated here so a
third brand only ever needs to be added in one place.

Layering: this lives in layer1 (no dependency on the agent) so both
layer1 modules (opensearch_retrieval.py) and layer2 (agent.py) can
import it without a cycle -- agent.py already depends on layer1, never
the other way around.
"""

from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures"

MANUAL_BY_PREFIX = {
    "WM-": FIXTURES / "manual_aquaspin.md",
    "AC-": FIXTURES / "manual_arcticair.md",
}
TERMS_BY_PREFIX = {
    "WM-": FIXTURES / "terms_aquaspin.md",
    "AC-": FIXTURES / "terms_arcticair.md",
}
BRAND_BY_PREFIX = {
    "WM-": "AquaSpin",
    "AC-": "ArcticAir",
}
BRAND_SLUGS = {name.lower(): name for name in BRAND_BY_PREFIX.values()}  # "arcticair" -> "ArcticAir"
WARRANTY_BY_PREFIX = {
    "WM-": {"component": "motor", "years": 2},
    "AC-": {"component": "compressor", "years": 5},
}


def _by_prefix(product_id: str, mapping: dict, label: str):
    for prefix, value in mapping.items():
        if product_id.startswith(prefix):
            return value
    raise ValueError(f"No {label} mapped for product_id {product_id}")


def manual_for(product_id: str) -> Path:
    return _by_prefix(product_id, MANUAL_BY_PREFIX, "manual")


def terms_for(product_id: str) -> Path:
    return _by_prefix(product_id, TERMS_BY_PREFIX, "terms")


def brand_for(product_id: str) -> str:
    """ArcticAir and AquaSpin are two independent brands, each with
    their own manual, terms, and support line -- there is no shared
    parent company in this demo."""
    return _by_prefix(product_id, BRAND_BY_PREFIX, "brand")


def warranty_component_for(product_id: str) -> tuple[str, int]:
    """Returns (component_name, warranty_years) -- e.g. ("motor", 2).
    Every product also gets a flat 1-year parts warranty; that part
    isn't per-product, so it isn't in this table."""
    info = _by_prefix(product_id, WARRANTY_BY_PREFIX, "warranty component")
    return info["component"], info["years"]
