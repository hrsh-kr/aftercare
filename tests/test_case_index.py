"""OpenSearch-backed cases: recurrence window and insights aggregations.
Needs the local OpenSearch container; skips (exit 0, says so) if it isn't up.
Run: .venv/bin/python -m tests.test_case_index"""
import sys
from types import SimpleNamespace

from src.domain.registration import load_registrations
from src.records import case_index


def _conv(reg, resolved, code="", section="4.1 Drum wobbling or banging noise during spin", days_ago=0):
    from datetime import datetime, timedelta
    return SimpleNamespace(
        registration=reg, resolved=resolved, ticket=None, escalation_code=code, section_heading=section,
        safety_flag=False, source="manual", complaint="bangs loudly",
        created_at=(datetime.now() - timedelta(days=days_ago)).isoformat(),
    )


def main() -> int:
    try:
        case_index.reset()
    except Exception as exc:
        print(f"SKIP (OpenSearch not reachable: {str(exc)[:60]})")
        return 0
    reg = next(r for r in load_registrations() if r.serial_number == "WM-FC-78234")

    assert [c["origin"] for c in case_index.prior_cases("WM-FC-79345", 90)] == ["seed"], "seeded history is found"
    assert case_index.prior_cases("WM-FC-78234", 90) == [], "no history for a fresh serial"

    case_index.record("t-old", _conv(reg, True, days_ago=120))
    assert case_index.prior_cases("WM-FC-78234", 90) == [], "a 120-day-old case is outside the window"
    case_index.record("t-new", _conv(reg, True, days_ago=5))
    assert len(case_index.prior_cases("WM-FC-78234", 90)) == 1, "a 5-day-old case is inside it"

    case_index.record("t-esc", _conv(reg, False, code="unmatched", section=""))
    ins = case_index.insights("aquaspin")
    assert (ins["resolved"], ins["escalated"]) == (2, 1), ins
    assert ins["by_reason"] == [{"code": "unmatched", "count": 1}], ins
    assert ins["top_sections"][0]["count"] == 2 and ins["top_sections"][0]["escalated"] == 0, ins
    assert case_index.insights("arcticair")["resolved"] == 0, "brand-scoped"

    case_index.record("t-new", _conv(reg, True, days_ago=5))
    assert case_index.insights("aquaspin")["resolved"] == 2, "recording twice does not duplicate"
    case_index.reset()
    print("PASS  case_index: window, seeds, brand scope, aggregations, idempotent record")
    return 0


if __name__ == "__main__":
    sys.exit(main())
