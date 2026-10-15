# Execution evidence and model quality

The original 12 development questions are preserved. Their deterministic compiler is separate from evaluator SQL, and original regression tests detect identical predicted/gold strings. Matching results on those known synthetic cases measures regression behavior, not general model accuracy.

The new graph is independently executed over real PostgreSQL using those 12 cases. Four workers claim persisted work; authority-denial, cross-user isolation, idempotency and lease-fencing checks run against actual roles/database transactions. Native SDK transport tests use HTTP mock transport and strict function response shapes; they make zero paid calls. Additional safety tests cover quoted identities, CTE laundering, application tables, catalog tables, unsafe functions, writes, recursive queries, locking and raw fact fan-out. Browser tests exercise the actual frontend and persistent API.

```sh
python scripts/benchmark.py --mode baseline --suite regression --case-limit 12
# Paid opt-in, only after private local provider configuration:
python scripts/benchmark.py --mode live --suite heldout --case-limit 3 --ack-live-spend
```

The separate held-out suite contains 30 specialty × employer × year filtered questions plus four authority/refusal cases. Their full questions/expected SQL are not in the deterministic intent compiler or model prompt. “Held out” describes that separation; this is a public developer-authored suite, not an independently curated confidential test set. A live run can start with three cases, then expand to all 34 after reviewing behavior and costs. No silent deterministic fallback is permitted for a requested live evaluation.

Reports retain suite/mode, per-case execution accuracy, errors, rounds/SQL attempts, usage, latency and source hashes. Optional per-million input/output prices supplied by the operator compute a rough cost estimate; cached-token discounts are not modeled. No model quality number or cost estimate is invented before a run. Each case creates a fresh investigator to avoid cross-case context contamination. Gold SQL exists only in the evaluator, never in agent context.

Remaining evaluation: independently curated held-out data distributions, semantic perturbations, robustness to hostile table text, prompt/plan ablations, provider/model comparisons, streaming/cancellation behavior, high concurrency/cost load and actual user feedback. The token cap is response-accounting based, not a provider-enforced spend limit. No live benchmark has been completed in this work.

## Executable comparison increment

See [semantic investigations](../architecture/SEMANTIC-INVESTIGATIONS.md) for the independent unequal-data oracle suite, five metric families, weighted-contribution semantics, Shapley counterexamples and quality/coverage withholding checks. `python scripts/comparison_benchmark.py --mode baseline` runs ten reviewed metric/dimension comparisons against independent quarterly SQL. This is known-case regression; do not combine it with or present it as held-out model understanding. Real Postgres rehearsals now execute 12 legacy plus 10 comparison cases through four claimants in two batches while preserving the 16-run admission cap. Browser CI downloads and offline-verifies the report and tests missing future coverage. Actual scoped results and remote run links are recorded after observation in EVIDENCE/PROGRESS.
