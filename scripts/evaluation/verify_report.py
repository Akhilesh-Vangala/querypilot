"""Offline content/reconciliation check. A hash is not a signature or source attestation."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.analytics.evidence import verify_artifact


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
