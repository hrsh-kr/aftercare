"""OpenSearch-backed retrieval -- real BM25 search over the manual/terms
sections that keyword_retrieve() (retrieval.py) used to score by hand.

Phase 1 (IMPLEMENTATION.md) validated that word-overlap scoring was
*good enough* to ground a suggestion correctly, including the hard
grinding-vs-clicking case. This module doesn't relitigate that claim --
it swaps the scoring mechanism for a real search engine's, and falls
back to the original scorer, honestly, if OpenSearch isn't reachable.
Never silently returns nothing, never pretends OpenSearch ran when it
didn't (see retrieve()'s returned `method`).
"""

import os
from pathlib import Path

from opensearchpy import OpenSearch

from src.layer1.catalog import MANUAL_BY_PREFIX, TERMS_BY_PREFIX
from src.layer1.retrieval import keyword_retrieve, load_sections

OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST", "http://localhost:9200")
INDEX_NAME = "aftercare-sections"

# Every document that might ever be retrieved from -- indexed once,
# up front, rather than lazily per-brand, so a fresh index always has
# the full catalog. Derived from catalog.py, not a separate hardcoded
# list, so a new brand only needs adding in one place.
ALL_DOCS = list(MANUAL_BY_PREFIX.values()) + list(TERMS_BY_PREFIX.values())

_client: OpenSearch | None = None
_indexed = False


class OpenSearchUnavailable(RuntimeError):
    pass


def _get_client() -> OpenSearch:
    global _client
    if _client is None:
        _client = OpenSearch(hosts=[OPENSEARCH_HOST], timeout=3, max_retries=1, retry_on_timeout=False)
    return _client


def ensure_indexed(force: bool = False) -> None:
    """Index every fixture's sections once per process. A no-op on
    later calls unless force=True -- cheap to call before every
    retrieval rather than tracking indexing state some other way."""
    global _indexed
    if _indexed and not force:
        return

    client = _get_client()
    if client.indices.exists(index=INDEX_NAME):
        if not force:
            _indexed = True
            return
        client.indices.delete(index=INDEX_NAME)

    client.indices.create(
        index=INDEX_NAME,
        body={"mappings": {"properties": {"path": {"type": "keyword"}, "heading": {"type": "text"}, "body": {"type": "text"}}}},
    )
    for doc_path in ALL_DOCS:
        for heading, body in load_sections(doc_path):
            client.index(index=INDEX_NAME, body={"path": str(doc_path), "heading": heading, "body": body})
    client.indices.refresh(index=INDEX_NAME)
    _indexed = True


def opensearch_retrieve(query: str, doc_path: Path) -> tuple[str, str]:
    """BM25 search scoped to one document's sections (a `term` filter
    on the exact source path, same document boundary keyword_retrieve()
    respected). Raises OpenSearchUnavailable on any connection/query
    failure -- the caller decides whether to fall back."""
    try:
        ensure_indexed()
        resp = _get_client().search(
            index=INDEX_NAME,
            body={
                "query": {
                    "bool": {
                        "filter": [{"term": {"path": str(doc_path)}}],
                        "must": [{"multi_match": {"query": query, "fields": ["heading^2", "body"]}}],
                    }
                },
                "size": 1,
            },
        )
    except Exception as exc:  # opensearch-py raises several distinct exception types for "unreachable" -- treat them all the same way
        raise OpenSearchUnavailable(str(exc)) from exc

    hits = resp.get("hits", {}).get("hits", [])
    if not hits:
        raise OpenSearchUnavailable(f"no indexed sections matched for {doc_path}")
    top = hits[0]["_source"]
    return top["heading"], top["body"]


def retrieve(query: str, doc_path: Path) -> tuple[str, str, str]:
    """Try OpenSearch first; fall back to the original keyword-overlap
    scorer if it's unreachable. Returns (heading, body, method) so
    callers can honestly report which one actually answered."""
    try:
        heading, body = opensearch_retrieve(query, doc_path)
        return heading, body, "opensearch"
    except OpenSearchUnavailable:
        sections = load_sections(doc_path)
        heading, body = keyword_retrieve(query, sections)
        return heading, body, "keyword_fallback"
