# QueryPilot current implementation status

Updated October21,2026 — pre-live run contracts. This page is the current scoped implementation description; dated project history remains preserved. Final publication evidence is recorded separately after protected CI and deployment checks. Local native regressions and actual product/guided browser rehearsals pass; required remote checks are not yet assumed complete.

## Implemented in this increment

Guided upload reports carry a strict run-v1 provenance record: unique correlation ID, input and contract hashes, result fingerprint, producer versions, verification scope/count and explicit billing origin. Source contents, SQL and credentials do not enter that metadata. SSE progress and its final report share an ID; the synchronous endpoint exposes X-Run-ID. Existing report signatures cover the record and reject its modification. Older signed reports remain supported without inventing missing provenance.

Private investigation events and reports now correlate with the queue job ID. General SQL provenance is explicitly execution-only; it does not certify business semantics or a durable source snapshot. Existing PostgreSQL admission/rate controls remain; global dollar admission and inner-graph checkpoint recovery are still deferred.

## Scope and remaining gates

Public workflows remain deterministic and report live_ai=false. No real provider request, hosted identity configuration, durable cloud tenant deployment, real ERP write or actual-user evaluation is established by these changes. Existing file formats, approvals, independent numerical checks, consented history and original demonstrations are preserved.

The first preparation increment begins with VerifyOps. Broader connector/dbt/semantic features, full cross-app budget policies and remote storage/checkpoint work are separate staged increments. A controlled actual-model run remains the next evidence gate after private credentials and a concrete evaluation budget.

[Repository layout](../../development/LAYOUT.md) · [Availability and monitoring limits](../../operations/AVAILABILITY.md).
