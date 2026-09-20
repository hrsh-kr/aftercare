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
from src.errors import DependencyUnavailable
from src.layer1.retrieval import SYNONYM_GROUPS, load_sections

OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST", "http://localhost:9200")
INDEX_NAME = "aftercare-sections-v4"  # v2: english analyzer; v3: keyed by file name; v4: shared synonym filter

# Every document that might ever be retrieved from -- indexed once,
# up front, rather than lazily per-brand, so a fresh index always has
# the full catalog. Derived from catalog.py, not a separate hardcoded
# list, so a new brand only needs adding in one place.
ALL_DOCS = list(MANUAL_BY_PREFIX.values()) + list(TERMS_BY_PREFIX.values())

_client: OpenSearch | None = None
_indexed = False


def _get_client() -> OpenSearch:
    global _client
    if _client is None:
        _client = OpenSearch(hosts=[OPENSEARCH_HOST], timeout=3, max_retries=1, retry_on_timeout=False)
    return _client


def ensure_indexed(force: bool = False) -> None:
    """Create the sections index and load every manual/terms section. Called by
    scripts/bootstrap_local.py (and the demo reset), never on a request path."""
    client = _get_client()
    if client.indices.exists(index=INDEX_NAME):
        if not force:
            return
        client.indices.delete(index=INDEX_NAME)

    text = {"type": "text", "analyzer": "aftercare_english"}
    client.indices.create(
        index=INDEX_NAME,
        body={
            "settings": {"analysis": {
                "filter": {
                    "customer_synonyms": {"type": "synonym", "lenient": True, "synonyms": [", ".join(g) for g in SYNONYM_GROUPS]},
                    "english_stop": {"type": "stop", "stopwords": "_english_"},
                    "english_stemmer": {"type": "stemmer", "language": "english"},
                },
                # customers say "won't turn on", manuals say "won't start": one shared synonym list
                "analyzer": {"aftercare_english": {"tokenizer": "standard", "filter": ["lowercase", "customer_synonyms", "english_stop", "english_stemmer"]}},
            }},
            "mappings": {"properties": {"doc": {"type": "keyword"}, "heading": text, "body": text}},
        },
    )
    for doc_path in ALL_DOCS:
        for heading, body in load_sections(doc_path):
            client.index(index=INDEX_NAME, body={"doc": doc_path.name, "heading": heading, "body": body})
    client.indices.refresh(index=INDEX_NAME)


def retrieve(query: str, doc_path: Path) -> tuple[str, str, str]:
    """BM25 search scoped to one document's sections (a `term` filter on the source file's
    name -- not its absolute path, which differs between a laptop and a Lambda container).
    Returns (heading, body, "opensearch"). No fallback: if OpenSearch is unreachable or the
    index is missing, that is a DependencyUnavailable, not a quieter answer from something else."""
    try:
        resp = _get_client().search(
            index=INDEX_NAME,
            body={
                "query": {"bool": {
                    "filter": [{"term": {"doc": doc_path.name}}],
                    "must": [{"multi_match": {"query": query, "fields": ["heading^2", "body"]}}],
                }},
                "size": 1,
            },
        )
    except Exception as exc:  # opensearch-py raises several distinct types for "unreachable"
        raise DependencyUnavailable("OpenSearch", str(exc)[:160]) from exc
    hits = resp.get("hits", {}).get("hits", [])
    if not hits:
        raise DependencyUnavailable("OpenSearch", f"no indexed sections matched {doc_path.name}; run scripts/bootstrap_local.py")
    top = hits[0]["_source"]
    return top["heading"], top["body"], "opensearch"
