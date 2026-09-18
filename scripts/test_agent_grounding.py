"""Phase 1 de-risking test, v2 -- rebuilt for the washing machine + AC
fixtures, per IMPLEMENTATION.md.

Tests:
1. Washing machine drum noise -> correctly grounded in manual 4.1,
   first suggestion is a real, doable-by-hand step (level + load balance)
2. Washing machine foul smell -> correctly grounded in 4.2, distinguished
   from drum noise despite both being "something's wrong with my machine"
3. AC not cooling -> correctly grounded in the AC manual's 4.1 (filter),
   not confused with the washing machine manual
4. Warranty status per product type (2yr motor / washing machine vs.
   5yr compressor / AC), computed deterministically, not by the model
5. Burning smell -> safety flag before any model call
"""

import csv
import re
from datetime import date, datetime
from pathlib import Path

from strands import Agent
from strands.models.ollama import OllamaModel

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
SAFETY_KEYWORDS = ["burning smell", "burning", "spark", "sparking", "smoke", "exposed wire", "shock", "gas smell"]

MANUALS = {
    "washing_machine": FIXTURES / "manual_windmere_washing_machine.md",
    "ac": FIXTURES / "manual_windmere_ac.md",
}


def load_sections(path: Path) -> list[tuple[str, str]]:
    text = path.read_text()
    parts = re.split(r"\n(?=##+\s)", text)
    sections = []
    for part in parts:
        lines = part.strip().splitlines()
        if not lines:
            continue
        heading = lines[0].lstrip("#").strip()
        body = "\n".join(lines[1:]).strip()
        if body:
            sections.append((heading, body))
    return sections


def keyword_retrieve(query: str, sections: list[tuple[str, str]]) -> tuple[str, str]:
    query_words = set(re.findall(r"\w+", query.lower()))
    scored = []
    for heading, body in sections:
        section_words = set(re.findall(r"\w+", (heading + " " + body).lower()))
        overlap = len(query_words & section_words)
        scored.append((overlap, heading, body))
    scored.sort(reverse=True)
    _, heading, body = scored[0]
    return heading, body


def check_safety(complaint: str) -> bool:
    lower = complaint.lower()
    return any(kw in lower for kw in SAFETY_KEYWORDS)


def build_agent(model_id: str = "qwen2.5-coder:7b") -> Agent:
    return Agent(model=OllamaModel(host="http://localhost:11434", model_id=model_id), callback_handler=None)


FIRST_STEP_PROMPT = """A customer's complaint about their {product}: "{complaint}"

The most relevant manual section, titled "{heading}":
{body}

Give the customer ONLY the first real step to try -- one specific, doable-by-hand \
action, not a list, not the whole section. They will report back after trying it. \
Answer in this format:
STEP: <the one thing to check or do, one or two sentences>
WAITING_FOR: <what you need them to report back>"""


def test_first_step(agent: Agent, product: str, complaint: str) -> None:
    if check_safety(complaint):
        print(f"[{product}] COMPLAINT: {complaint}\n  -> SAFETY FLAG (no model call)\n")
        return
    sections = load_sections(MANUALS[product])
    heading, body = keyword_retrieve(complaint, sections)
    print(f"[{product}] COMPLAINT: {complaint}")
    print(f"  RETRIEVED: {heading}")
    result = str(agent(FIRST_STEP_PROMPT.format(product=product, complaint=complaint, heading=heading, body=body))).strip()
    print(f"  {result}\n")


WARRANTY_PROMPT = """A customer's {component} warranty is {component_status} ({component_years} years from \
purchase). Their other-parts warranty is {parts_status} (1 year from purchase). Write one plain-language \
sentence telling them this. State only these two facts -- do not compute or restate any dates yourself."""


def _add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(month=2, day=28, year=d.year + years)


def compute_warranty_status(purchase_date: str, product_id: str) -> tuple[str, str, str, int]:
    """Deterministic date math, per product type -- washing machines get a
    2-year motor warranty, ACs get a 5-year compressor warranty, both get
    1 year on other parts. Never delegate this to the model."""
    purchased = datetime.strptime(purchase_date, "%Y-%m-%d").date()
    today = date.today()
    if product_id.startswith("WM-"):
        component, years = "motor", 2
    else:
        component, years = "compressor", 5
    component_status = "active" if today < _add_years(purchased, years) else "expired"
    parts_status = "active" if today < _add_years(purchased, 1) else "expired"
    return component, component_status, parts_status, years


def test_warranty(agent: Agent, name: str, purchase_date: str, product_id: str, product_name: str) -> None:
    component, component_status, parts_status, years = compute_warranty_status(purchase_date, product_id)
    print(f"CUSTOMER: {name} ({product_name}, purchased {purchase_date}) -> {component}: {component_status}, parts: {parts_status}")
    result = str(
        agent(
            WARRANTY_PROMPT.format(
                component=component, component_status=component_status, component_years=years, parts_status=parts_status
            )
        )
    ).strip()
    print(f"  {result}\n")


def main() -> None:
    agent = build_agent()

    print("=" * 60)
    print("TROUBLESHOOTING -- washing machine: two different faults")
    print("=" * 60)
    test_first_step(agent, "washing_machine", "My washing machine drum is making a loud banging noise when it spins")
    test_first_step(agent, "washing_machine", "My clothes smell bad and have residue on them after washing")

    print("=" * 60)
    print("TROUBLESHOOTING -- AC, different manual entirely")
    print("=" * 60)
    test_first_step(agent, "ac", "My AC isn't cooling the room properly anymore")

    print("=" * 60)
    print("TROUBLESHOOTING -- safety case")
    print("=" * 60)
    test_first_step(agent, "ac", "There's a burning smell coming from the AC")

    print("=" * 60)
    print("WARRANTY -- all four fixture customers, per product type")
    print("=" * 60)
    with open(FIXTURES / "sales_data_windmere.csv") as f:
        for row in csv.DictReader(f):
            test_warranty(agent, row["customer_name"], row["purchase_date"], row["product_id"], row["product_name"])


if __name__ == "__main__":
    main()
