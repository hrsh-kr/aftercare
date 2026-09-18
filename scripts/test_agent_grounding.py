"""Phase 1 de-risking test, per IMPLEMENTATION.md.

Tests, against the real fixtures, not synthetic examples:
1. Grinding noise -> correctly grounded in manual section 5.1 (mechanical/bracket, not motor)
2. Clicking noise -> correctly grounded in section 5.2 (balancing) -- the real test,
   since grinding and clicking read similarly to a naive keyword match but have
   different root causes in the manual
3. Warranty status for each of the 4 fixture customers, grounded in terms_windmere.md
4. Burning smell -> safety flag BEFORE any model call, no troubleshooting attempt
"""

import csv
import re
from datetime import date, datetime
from pathlib import Path

from strands import Agent
from strands.models.ollama import OllamaModel

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
SAFETY_KEYWORDS = ["burning smell", "burning", "spark", "sparking", "smoke", "exposed wire", "shock"]


def load_sections(path: Path) -> list[tuple[str, str]]:
    """Split a markdown fixture into (heading, body) sections."""
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
    """Simplest possible retrieval: score by shared words, return the best section."""
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


TROUBLESHOOT_PROMPT = """A customer's fan complaint: "{complaint}"

The most relevant manual section, titled "{heading}":
{body}

Based only on this section, answer in this exact format:
ROOT_CAUSE: <one short phrase>
COVERED: <yes/no, per this section>
ANSWER: <one or two sentences to the customer, citing what the section actually says>"""


def test_troubleshooting(agent: Agent, sections: list[tuple[str, str]], complaint: str) -> None:
    if check_safety(complaint):
        print(f"COMPLAINT: {complaint}\n  -> SAFETY FLAG (no model call, no troubleshooting attempt)\n")
        return
    heading, body = keyword_retrieve(complaint, sections)
    print(f"COMPLAINT: {complaint}")
    print(f"  RETRIEVED SECTION: {heading}")
    result = str(agent(TROUBLESHOOT_PROMPT.format(complaint=complaint, heading=heading, body=body))).strip()
    print(f"  {result}\n")


WARRANTY_PROMPT = """A customer's motor warranty is {motor_status} (covers 3 years from purchase). \
Their parts warranty is {parts_status} (covers 1 year from purchase). Write one plain-language \
sentence telling them this. State only these two facts -- do not compute or restate any dates yourself."""


def _add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # Feb 29 on a non-leap target year
        return d.replace(month=2, day=28, year=d.year + years)


def compute_warranty_status(purchase_date: str) -> tuple[str, str]:
    """Deterministic date math -- the one thing the model must not be asked to do.
    Real bug found running this test the first time: the model got motor/parts
    status backwards or wrong on 2 of 4 fixture customers when asked to compute
    it directly. Moved the arithmetic here; the model's only job now is phrasing
    an answer from numbers it's simply handed, per DESIGN.md's honesty rules."""
    purchased = datetime.strptime(purchase_date, "%Y-%m-%d").date()
    today = date.today()
    motor_status = "active" if today < _add_years(purchased, 3) else "expired"
    parts_status = "active" if today < _add_years(purchased, 1) else "expired"
    return motor_status, parts_status


def test_warranty(agent: Agent, name: str, purchase_date: str) -> None:
    motor_status, parts_status = compute_warranty_status(purchase_date)
    print(f"CUSTOMER: {name} (purchased {purchase_date}) -> motor: {motor_status}, parts: {parts_status}")
    result = str(agent(WARRANTY_PROMPT.format(motor_status=motor_status, parts_status=parts_status))).strip()
    print(f"  {result}\n")


def main() -> None:
    manual_sections = load_sections(FIXTURES / "manual_windmere_cyclone1200.md")
    terms_sections = load_sections(FIXTURES / "terms_windmere.md")
    agent = build_agent()

    print("=" * 60)
    print("TROUBLESHOOTING -- grinding vs. clicking (the real test)")
    print("=" * 60)
    test_troubleshooting(agent, manual_sections, "My fan is making a grinding noise, especially at high speed")
    test_troubleshooting(agent, manual_sections, "There's a clicking sound that happens every time the blade goes around")

    print("=" * 60)
    print("TROUBLESHOOTING -- safety case")
    print("=" * 60)
    test_troubleshooting(agent, manual_sections, "I smell something burning and saw a small spark near the fan")

    print("=" * 60)
    print("WARRANTY -- all four fixture customers")
    print("=" * 60)
    with open(FIXTURES / "sales_data_windmere.csv") as f:
        for row in csv.DictReader(f):
            test_warranty(agent, row["customer_name"], row["purchase_date"])


if __name__ == "__main__":
    main()
