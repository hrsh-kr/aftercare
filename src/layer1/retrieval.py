"""Section loading + keyword retrieval, shared by Layer 1's claim
checks and Layer 2's agent. Moved here from the test script once it
became shared logic, same reasoning as registration.py.

Keyword overlap, not embeddings -- validated in Phase 1
(IMPLEMENTATION.md): grinding vs. clicking, lexically similar but
different root causes, both retrieved correctly on the first try.
"""

import re
from pathlib import Path


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
