"""CSV onboarding preview: brand sorting and honest row-level problems. No services needed."""
import os
os.environ["AFTERCARE_STORE"] = "file"
from src.webapp import api_core as core

HEADER = "customer_name,customer_phone,product_id,product_name,serial_number,purchase_date,retailer,purchase_price\n"


def test_fixture_file_is_clean_and_sorted_by_brand():
    from src.domain.registration import SALES_DATA
    out, status = core.ingest_preview(SALES_DATA.read_text())
    assert status == 200 and out["issues"] == [] and out["rejected"] == 0, out
    assert {b["brand"]: b["products"] for b in out["brands"]} == {"AquaSpin": 3, "ArcticAir": 2}


def test_a_messy_store_file_reports_each_problem_and_keeps_the_good_rows():
    out, _ = core.ingest_preview(HEADER + "\n".join([
        "A,+919800000001,WM-FC-700,W,S1,2025-01-01,X,1",
        "B,+919800000002,XX-999,Mystery,S2,2025-01-01,X,1",
        "C,+919800000003,AC-CB-15T,AC,S3,05/01/2025,X,1",
        "D,98000,AC-CB-15T,AC,S4,2025-01-01,X,1",
        "E,+919800000005,AC-CB-15T,AC,S1,2025-01-01,X,1",
    ]))
    assert out["rows"] == 5 and out["accepted"] == 1 and out["rejected"] == 4, out
    problems = " | ".join(i["problem"] for i in out["issues"])
    for expect in ("Unknown product code", "not YYYY-MM-DD", "Phone is not", "already appears on line 2"):
        assert expect in problems, (expect, problems)


def test_missing_columns_and_size_limit():
    assert core.ingest_preview("a,b\n1,2")[1] == 422
    assert core.ingest_preview(HEADER + "x" * 300_000)[1] == 413


if __name__ == "__main__":
    for n, f in sorted(globals().items()):
        if n.startswith("test_"):
            f(); print("PASS ", n)
