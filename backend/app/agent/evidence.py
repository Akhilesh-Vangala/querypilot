"""Offline evidence checks shared by the packaged app, CLI and tests."""

from .semantic import ComparisonRequest, VERSION, receipt_digest, verify_comparison


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
