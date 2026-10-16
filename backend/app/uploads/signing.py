"""Authenticate a saved computed report; do not equate source rules with real-world truth."""
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import secrets

_ephemeral_key = secrets.token_bytes(64)


def key():
    value = os.getenv("QUERY_REPORT_SIGNING_KEY")
    if value:
        if len(value) < 48:
            raise ValueError("The report signing key must have at least 48 characters")
        return value.encode()
    return _ephemeral_key


def digest(report):
    payload = {k: v for k, v in report.items() if k != "attestation"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def attest(report):
    if not report.get("checks") or not all(v is True for v in report["checks"].values()):
        raise ValueError("A failed report cannot receive a verification attestation")
    result = {**report, "verified_at": datetime.now(timezone.utc).isoformat()}
    signature = hmac.new(key(), ("querypilot-upload-report-v1:"+digest(result)).encode(), hashlib.sha256).hexdigest()
    result["attestation"] = {"version": "v1", "signature": signature,
                             "scope": "Unmodified report produced by this deployment; correctness remains conditional on the declared source contract."}
    return result


def verify_report(report):
    receipt = report.get("attestation", {})
    if not isinstance(receipt, dict) or receipt.get("version") != "v1" or not isinstance(receipt.get("signature"), str):
        return False
    try:
        expected = hmac.new(key(), ("querypilot-upload-report-v1:"+digest(report)).encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(receipt["signature"], expected)
    except (TypeError, ValueError, OverflowError):
        return False
