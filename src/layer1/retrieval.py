"""Section loading + keyword retrieval. Moved here from the test script
once it became shared logic, same reasoning as registration.py.

Keyword overlap, not embeddings -- validated in Phase 1
(IMPLEMENTATION.md): grinding vs. clicking, lexically similar but
different root causes, both retrieved correctly on the first try.
`load_sections()` is still used directly (opensearch_retrieval.py
indexes with it); `keyword_retrieve()` is a test double only (unit tests
stand it in for OpenSearch); the app has no fallback -- see
opensearch_retrieval.py's retrieve().
"""

import re
from pathlib import Path

# Words that carry no diagnostic signal. Shared by the keyword fallback here
# and by the agent's "can we diagnose this at all?" gate (layer2/agent.py), so
# both judge a complaint the same way.
_STOP = set(
    "a an the and or but if then so of to in on at for from by with without into onto out up down over under "
    "it its this that these those my me our your we you i is are was were be been being am do does did done "
    "has have had not no nor can cant cannot could would should will wont just very too also as than there here "
    "what which who whom how when where why all any some each every more most other such only own same again "
    "still anymore now already even ever keeps keep got get gets getting im ive isn doesn don didn won couldn "
    "wouldn shouldn hasn haven aren wasn weren ain please help need want like really quite".split()
)
_GENERIC = set(
    "machine washing washer wash ac air conditioner conditioning unit product appliance working work issue "
    "problem broken stopped stop something thing".split()
)


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "ly", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def content_words(text: str) -> set[str]:
    """Stemmed words that actually say something ("bangs" and "banging" both
    become "bang"; "when", "it", "machine" are dropped)."""
    return {
        _stem(w)
        for w in re.findall(r"[a-z]+", text.lower())
        if len(w) > 2 and w not in _STOP and w not in _GENERIC
    }


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
    """Test-double retrieval (not used at runtime): score sections by shared *content* words (stemmed,
    filler dropped), a heading match counting double. Ties keep manual order --
    not alphabetical, which is what the old raw-word scorer did by accident."""
    q = content_words(query)
    best_score, best = -1, sections[0]
    for heading, body in sections:
        score = 2 * len(q & content_words(heading)) + len(q & content_words(body))
        if score > best_score:  # strict: the earliest section wins a tie
            best_score, best = score, (heading, body)
    return best
