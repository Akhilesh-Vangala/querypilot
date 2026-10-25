# Actual browser demonstrations

[Open QueryPilot](https://querypilot-five.vercel.app/) · [File analysis video](https://querypilot-five.vercel.app/uploads/recording.html) · [Warehouse investigation video](https://querypilot-five.vercel.app/recordings/)

Both videos are continuous Chromium recordings of real interactions and server results using authored fixture data. They contain no generated UI frames, inserted performance scores or live-model inference.

| Recording | Captured execution | Provenance |
| --- | --- | --- |
| File workspace | Upload, source preview, reviewed rules, independently checked result, actual run identity, downloads, explicit device save and history | [Source/media manifest](demos/uploads-recording.json), [WebM](../frontend/public/uploads/walkthrough.webm) |
| Warehouse studio | Prompt-led investigation, actual tool payload, executed SQL, public plan, period comparison, independent checks and exported evidence | [Source/media manifest](demos/interactive-recording.json), [WebM](../frontend/public/recordings/querypilot.webm) |

The [six-frame colour preview](assets/demos/querypilot-demo.gif) is quantized from the actual captured browser pixels. Continuous videos remain the full interaction record. Manifests hash application source, styles, static players and capture scripts; each video has a SHA-256 digest. Older capture manifests are retained under `demos/history/`.

## Reproduce

```sh
python scripts/demos/product_browser.py --record --output artifacts/generated/product-recording --axe /path/to/axe.min.js
python scripts/demos/browser_smoke.py --url http://127.0.0.1:3007 --record --publish-assets --screenshots artifacts/generated/guided-recording
python scripts/demos/studio_browser.py --url http://127.0.0.1:3007 --axe /path/to/axe.min.js
```

Capture against the matching built frontend and backend. A deployment SHA is only attributable after independently checking deployment metadata. The scripts do not authenticate a supplied source label. Raw screenshots and test exports remain ignored; published videos/manifests identify the exercised source.

[Architecture](architecture/OVERVIEW.md) · [Evaluation](evaluation/README.md) · [Technical report](TECHNICAL-REPORT.md).
