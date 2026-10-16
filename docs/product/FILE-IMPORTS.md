# QueryPilot: supported file imports

The public product accepts **CSV, TSV, Excel `.xlsx`, JSON and JSONL**. Select one file using the chooser or drop zone. It is parsed and profiled before the existing reviewed business rules run. File extension changes do not bypass the original result/approval checks.

| Format | Contract |
| --- | --- |
| CSV | UTF-8, one named header row. Original text, including BOM and CRLF, is retained for compatibility with saved source fingerprints. |
| TSV | UTF-8 tab-separated text with one header row; quoted tabs/newlines follow CSV quoting rules. |
| Excel `.xlsx` | Values in a rectangular table beginning at row1. Choose one visible worksheet when several exist; sheets are never combined automatically. Numeric cells use stored values, not displayed rounding or formatting. Text IDs retain leading zeros; numeric cells with a visual zero-padding format do not become text IDs. Dates/times become ISO text without inventing a timezone. |
| JSON | A non-empty array of flat record objects. Every object must have the same field set; use null for a missing value. The first record fixes column order. Numeric lexemes use Decimal rather than a binary-float intermediate. |
| JSONL | One flat object per line, same field requirements; blank record lines are refused. |

TSV/JSON/JSONL/Excel normalize to an inspectable CSV table. The browser records format, selected sheet, original-file SHA256 and normalized-table SHA256. Import metadata describes conversion; it does not authenticate a business document or establish real-world truth. Checked report receipts authenticate the computed report and its normalized source contract, as before. Device snapshots and portable backups retain the normalized table/rules/report; they do not archive the original binary workbook. Cloud saves remain unavailable until a real provider is configured.

## Limits and rejection behavior

Each source file and the normalized table must be at most400,000UTF8/raw bytes. Existing limits remain: 5,000 data records,60columns,120characters per header and2,048per cell. Body transport uses bounded base64 inside JSON, remains below the existing1MB actual streamed-body ceiling and15second receive deadline, and never writes user filenames to disk. Record numbers in preview/errors refer to the normalized table with header as record1.

Excel uses pinned openpyxl read-only loading plus defusedxml. Before loading, ZIP metadata/XML are bounded:200members,8MB total expansion,4MB per member,150:1 compression ratio and no duplicate/traversing/encrypted entries. DTD/entities, formulas, merged cells, macros, external-workbook links, embeddings and ActiveX are refused. Dimensions cannot hide additional source cells; actual rows/cells are independently bounded. Formula evaluation, macro execution, external content fetching and original formatting are not part of import. Export a values-only table when prompted.

PDFs, images, legacy `.xls`, `.xlsm`, arbitrary ZIPs, Parquet, documents and arbitrary SQL/code are **unsupported**. They need a separately specified extraction/processing contract; their extension is never accepted as evidence of support.

Errors return structured client-safe guidance without raw cell values or parser traces. Invalid/ambiguous JSON, ragged records, unsupported types and oversized/unsafe workbooks withhold results. Cancelling worksheet selection commits no partial source. Original rules still determine duplicate handling, eligibility, exact totals, stock allocation, independent checks and human approval.

## Implementation and observed checks

`POST /api/uploads/import` accepts `filename`, `content_base64` and optional `sheet`. A multi-sheet response returns `needs_sheet` and visible names without selecting a dataset. A completed response returns the normalized table, profile and import metadata. Existing analysis/preview/save APIs keep their source/contract checks. `GET /api/uploads/capabilities` lists supported formats.

- `backend/tests/api/test_imports.py` exercises actual conversions, exact decimals/IDs/BOM identity, malformed JSON, workbook formulas/merged cells/entities/ZIP bounds, lying dimensions, transport limits and equal results through the existing domain engine for all five formats.
- `scripts/demos/import_browser.py` uses actual file selection through all five real domain results, explicit accessible worksheet choice/cancellation, invalid-file recovery and supported-layout checks. Relay also requires separate approval and actual checked receipts for each format.
- Existing product/save/restore/accessibility and original guided workflows remain required. Actual source-bound CI and canonical production evidence determine publication status, not prepared files.

Parser references: [openpyxl security](https://openpyxl.readthedocs.io/en/stable/#security), [read-only loading and worksheet dimensions](https://openpyxl.readthedocs.io/en/stable/optimized.html).
