# Delivery protocol

Work is scoped to an executable system contract, implemented on a short-lived branch and published through the [protected branch workflow](../development/BRANCHING.md).

1. Define inputs, outputs, authority and independently checkable behavior.
2. Implement within the [owned frontend/backend boundaries](../development/LAYOUT.md).
3. Run relevant native, browser, accessibility and database checks.
4. Capture continuous demonstrations from the final application source.
5. Require all exact-head CI jobs and source-bound preview checks.
6. Squash merge the tested tree, verify the canonical deployment and record observed evidence.

[Technical system contract](../TECHNICAL-REPORT.md) · [Measured evidence](../evaluation/EVIDENCE.md). Historical planning snapshots are retained under `history/`.
