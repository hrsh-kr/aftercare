"""Finished conversations ("cases") and tickets, indexed in OpenSearch.

Why this exists: recurrence ("same product, same problem, seen before") and the
brand's insights ("why do customers escalate?") are *search and aggregation*
questions, which is what OpenSearch is for -- not something to answer by
re-reading a directory of JSON files on every request.

Two indices:
  aftercare-cases-v1    one doc per finished conversation (resolved or escalated)
  aftercare-tickets-v1  one doc per ticket, text-searchable for the dashboard

Runtime functions raise DependencyUnavailable if OpenSearch is unreachable or the indices
are missing (scripts/bootstrap_local.py creates them). There is no fallback path.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import functools

from src.errors import DependencyUnavailable
from src.layer1.catalog import brand_for
from src.layer1.opensearch_retrieval import _get_client

CASES = "aftercare-cases-v1"
TICKETS = "aftercare-tickets-v1"
SEED = Path(__file__).resolve().parent.parent.parent / "fixtures" / "history_seed.json"

_MAPPINGS = {
    CASES: {"properties": {
        "conversation_id": {"type": "keyword"}, "brand": {"type": "keyword"}, "serial_number": {"type": "keyword"},
        "product_id": {"type": "keyword"}, "section_heading": {"type": "keyword"}, "source": {"type": "keyword"},
        "outcome": {"type": "keyword"}, "reason_code": {"type": "keyword"}, "origin": {"type": "keyword"},
        "complaint": {"type": "text", "analyzer": "english"}, "created_at": {"type": "date"},
    }},
    TICKETS: {"properties": {
        "ticket_id": {"type": "keyword"}, "brand": {"type": "keyword"}, "reason_code": {"type": "keyword"},
        "serial_number": {"type": "keyword"}, "safety_flag": {"type": "boolean"},
        "customer_name": {"type": "text"}, "product_name": {"type": "text"},
        "issue_summary": {"type": "text", "analyzer": "english"}, "created_at": {"type": "date"},
    }},
}


def _guard(fn):
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except DependencyUnavailable:
            raise
        except Exception as exc:
            raise DependencyUnavailable("OpenSearch", str(exc)[:160]) from exc
    return wrapper


def ensure() -> None:
    """Create the indices and seed history. For bootstrap and reset only."""
    c = _get_client()
    for name, mapping in _MAPPINGS.items():
        if not c.indices.exists(index=name):
            c.indices.create(index=name, body={"mappings": mapping})
            if name == CASES:
                _seed(c)


def _seed(c) -> None:
    """Earlier cases a brand's ticketing system would already hold on day one.
    Ages are relative so the demo scenario stays inside the recurrence window."""
    for i, e in enumerate(json.loads(SEED.read_text())):
        c.index(index=CASES, id=f"seed-{i}", refresh=True, body={
            "conversation_id": f"seed-{i}", "brand": brand_for(e["product_id"]).lower(),
            "serial_number": e["serial_number"], "product_id": e["product_id"],
            "section_heading": e["section_heading"], "source": "manual", "outcome": e["outcome"],
            "reason_code": "", "origin": "seed", "complaint": e.get("note", ""),
            "created_at": (datetime.now() - timedelta(days=e["days_ago"])).isoformat(),
        })


def reset() -> None:
    c = _get_client()
    for name in _MAPPINGS:
        if c.indices.exists(index=name):
            c.indices.delete(index=name)
    ensure()


@_guard
def record(conv_id: str, conv) -> None:
    """Index a finished conversation and its ticket. Idempotent: the doc id is the
    conversation / ticket id, so re-recording overwrites rather than duplicates."""
    c = _get_client()
    reg = conv.registration
    brand = brand_for(reg.product_id).lower()
    c.index(index=CASES, id=conv_id, refresh=True, body={
        "conversation_id": conv_id, "brand": brand, "serial_number": reg.serial_number,
        "product_id": reg.product_id, "section_heading": conv.section_heading,
        "source": "safety" if conv.safety_flag else conv.source,
        "outcome": "resolved" if conv.resolved else "answered" if getattr(conv, "answered", False) else "escalated",
        "reason_code": conv.escalation_code,
        "origin": "live", "complaint": conv.complaint, "created_at": conv.created_at,
    })
    if conv.ticket:
        t = conv.ticket
        c.index(index=TICKETS, id=t.ticket_id, refresh=True, body={
            "ticket_id": t.ticket_id, "brand": brand, "reason_code": t.reason_code,
            "serial_number": t.serial_number, "safety_flag": t.safety_flag,
            "customer_name": t.customer_name, "product_name": t.product_name,
            "issue_summary": t.issue_summary, "created_at": t.created_at,
        })


@_guard
def prior_cases(serial: str, days: int) -> list[dict]:
    """Cases for one serial inside the window, manual-sourced only (a safety case or a
    warranty question is not 'the same problem')."""
    r = _get_client().search(index=CASES, body={
        "size": 50, "sort": [{"created_at": "desc"}],
        "query": {"bool": {"filter": [
            {"term": {"serial_number": serial}}, {"term": {"source": "manual"}},
            {"range": {"created_at": {"gte": f"now-{days}d"}}},
        ]}},
    })
    return [h["_source"] for h in r["hits"]["hits"]]


@_guard
def insights(brand: str) -> dict:
    """What a brand learns from its own cases: how conversations end, why they escalate,
    and which manual sections send people to a human. Live cases only (seeds excluded)."""
    r = _get_client().search(index=CASES, body={
        "size": 0,
        "query": {"bool": {"filter": [{"term": {"brand": brand}}], "must_not": [{"term": {"origin": "seed"}}]}},
        "aggs": {
            "outcome": {"terms": {"field": "outcome"}},
            "reason": {"terms": {"field": "reason_code", "size": 10}},
            "sections": {"terms": {"field": "section_heading", "size": 5},
                         "aggs": {"escalated": {"filter": {"term": {"outcome": "escalated"}}}}},
        },
    })
    a = r["aggregations"]
    outcome = {b["key"]: b["doc_count"] for b in a["outcome"]["buckets"]}
    return {
        "engine": "opensearch",
        "resolved": outcome.get("resolved", 0), "answered": outcome.get("answered", 0), "escalated": outcome.get("escalated", 0),
        "by_reason": [{"code": b["key"], "count": b["doc_count"]} for b in a["reason"]["buckets"] if b["key"]],
        "top_sections": [{"heading": b["key"], "count": b["doc_count"], "escalated": b["escalated"]["doc_count"]}
                         for b in a["sections"]["buckets"] if b["key"]],
    }


@_guard
def search_tickets(brand: str, q: str) -> list[str]:
    """Ticket ids for a brand matching free text (customer, product, issue)."""
    r = _get_client().search(index=TICKETS, body={
        "size": 100, "query": {"bool": {"filter": [{"term": {"brand": brand}}],
                                        "must": [{"multi_match": {"query": q, "fields": ["issue_summary", "customer_name", "product_name"]}}]}},
    })
    return [h["_source"]["ticket_id"] for h in r["hits"]["hits"]]
