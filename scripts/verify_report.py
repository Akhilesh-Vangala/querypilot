"""Offline content/reconciliation check. A hash is not a signature or source attestation."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.agent.semantic import (
    ComparisonRequest,
    VERSION,
    receipt_digest,
    verify_comparison,
)


def verify_artifact(payload):
    if payload["format"] != "querypilot-report-v1":
        raise ValueError("Unsupported report format")
    result = payload["run"]["result"]
    evidence = result["evidence"]
    if evidence["version"] != VERSION:
        raise ValueError("Unsupported executable contract version")
    request = ComparisonRequest.model_validate(evidence["request"])
    digest = receipt_digest(request, evidence["columns"], evidence["rows"])
    if (
        digest != evidence["result_sha256"]
        or digest != result["validation"]["result_sha256"]
    ):
        raise ValueError("Evidence fingerprint mismatch")
    recomputed = verify_comparison(
        request, evidence["columns"], evidence["rows"], result["validation"]
    )
    if recomputed != result["comparison"]:
        raise ValueError("Report differs from independently recomputed accounting")
    return {
        "content_fingerprint": "matched",
        "accounting_recomputed": True,
        "comparison_verified": recomputed["verified"],
        "limitation": "Checks internal content consistency only. Unsigned report; source origin and natural-language intent are not authenticated.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    if args.report.stat().st_size > 2000000:
        parser.error("Report exceeds the 2 MB allowance")
    try:
        report = verify_artifact(json.loads(args.report.read_text()))
    except (ValueError, KeyError, TypeError) as error:
        raise SystemExit("Report verification failed: " + str(error)) from None
    print(json.dumps(report))


if __name__ == "__main__":
    main()
