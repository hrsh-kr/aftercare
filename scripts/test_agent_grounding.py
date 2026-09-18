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
import sys
from pathlib import Path

from strands import Agent
from strands.models.ollama import OllamaModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.layer1.registration import compute_warranty_status  # noqa: E402 -- canonical impl, Phase 2
from src.layer1.retrieval import load_sections, keyword_retrieve  # noqa: E402 -- canonical impl, Phase 3

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
SAFETY_KEYWORDS = ["burning smell", "burning", "spark", "sparking", "smoke", "exposed wire", "shock", "gas smell"]

MANUALS = {
    "washing_machine": FIXTURES / "manual_aquaspin.md",
    "ac": FIXTURES / "manual_arcticair.md",
}


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


def test_warranty(agent: Agent, name: str, purchase_date: str, product_id: str, product_name: str) -> None:
    component, years, component_status, parts_status = compute_warranty_status(purchase_date, product_id)
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
    with open(FIXTURES / "sales_data.csv") as f:
        for row in csv.DictReader(f):
            test_warranty(agent, row["customer_name"], row["purchase_date"], row["product_id"], row["product_name"])


if __name__ == "__main__":
    main()
