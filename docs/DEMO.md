# Current product recording

The [upload walkthrough](demos/uploads-recording.json) now records the complete product journey: real file selection, source preview, reviewed definition, executed independently checked results, exports, explicit device save and saved history. [Product result screenshot](assets/demos/product-report.png). This is one continuous Chromium capture using authored test data, with readable pauses; it is not customer feedback or live-model inference. The original guided sample recording remains distinct below. Previous capture manifests are retained under `docs/demos/history/`.

# QueryPilot recorded demonstration

[Open the working app](https://querypilot-five.vercel.app) · [Watch the continuous recording](https://querypilot-five.vercel.app/recordings/) · [Download the WebM](../frontend/public/recordings/querypilot.webm) · [Capture/source manifest](demos/interactive-recording.json)

![Actual guided browser journey](assets/demos/querypilot-demo.gif)

The GIF is a six-frame preview. The WebM is a continuous Playwright screen recording of real browser interactions and server results; no generated UI, invented scores, model reasoning transcript or customer feedback is inserted. All data is original synthetic development data and no live model inference occurs.

| Stage | Actual captured behavior |
| --- | --- |
| 1 | overview |
| 2 | executed investigation |
| 3 | guarded sql |
| 4 | reconciled periods |
| 5 | independent checks |
| 6 | exported evidence |

## Scope and provenance

Video SHA256: `8a0bb720a8efa40cf1b73a768ac80aca258451aeafbedca89085e9aded6fb3c0`. The [manifest](demos/interactive-recording.json) contains frame hashes, source hashes, browser checks and capture scope. This capture runs the actual built React frontend and reorganized FastAPI backend in an isolated local guided rehearsal. The same native recording-player/static routing is exercised. Source hashes identify the captured working tree; no deployed-commit attribution is claimed for this local capture. The earlier public capture remains in the dated manifest history.

## Reproduce

```sh
python scripts/demos/browser_smoke.py --url https://querypilot-five.vercel.app --record --publish-assets --source-commit <verified-deployment-sha> --screenshots artifacts/generated/demo-capture
```

Check the source commit of the URL before attributing a remote capture. The optional source-commit value is provenance supplied by the operator, not independently authenticated by the recording script. Raw captures and downloaded reports stay ignored.

The independent evidence download/recalculation, future-period withholding, reload and mobile checks run during the captured journey.

[Current system layout](development/LAYOUT.md) · [Private/public architecture](architecture/OVERVIEW.md) · [Evaluation limits](evaluation/README.md).
