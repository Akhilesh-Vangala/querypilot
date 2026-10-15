# QueryPilot progress and evidence

## October 15 — Repository organization and demo refresh

Implemented explicit frontend/backend ownership, a curated technical documentation index, current README/evidence scope and original actual browser recordings. Native regression suites pass; protected remote checks and post-promotion public verification are the publication gates for this increment. Current paths and source ownership are documented in [layout](../development/LAYOUT.md).

| Existing evidence baseline | Scope |
| --- | --- |
| [CI38656672511](https://github.com/Akhilesh-Vangala/querypilot/actions/runs/38656672511) | Passed 137-case suite, reviewed comparisons, PostgreSQL workers, browser/export and restart before this reorganization. |
| Public application | Synthetic guarded SQL and reviewed period comparisons with evidence export. |
| New recording | Actual continuous Chromium capture and a separate six-frame GIF preview. [Provenance](../DEMO.md). |

Do not interpret the older source baseline as a test of new path changes. The required PR workflow verifies the new tree before merge; final publication evidence is linked in the merged PR and current Actions page.

No paid model calls or actual-user validation. Live-model quality and customer-production gates remain open.

[Full prior progress history](history/PRE-ORGANIZATION-PROGRESS.md).
