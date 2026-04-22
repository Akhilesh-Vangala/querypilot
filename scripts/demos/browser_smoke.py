"""Actual Chromium analyst journey, provenance dialog and mobile layout."""

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
from playwright.sync_api import expect

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:3007")
parser.add_argument("--screenshots", default="artifacts/generated/browser")
parser.add_argument("--record", action="store_true")
parser.add_argument(
    "--source-commit", help="Verified source commit of the deployment being captured"
)
parser.add_argument("--publish-assets", action="store_true")
args = parser.parse_args()
if args.publish_assets and not args.record:
    parser.error("Publishing recording assets requires --record")
output = Path(args.screenshots)
output.mkdir(parents=True, exist_ok=True)
frames = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    options = {"viewport": {"width": 1440, "height": 1000}}
    if args.record:
        options.update(
            viewport={"width": 1180, "height": 844},
            record_video_size={"width": 1180, "height": 844},
            record_video_dir=str(output / "raw-video"),
        )
    context = browser.new_context(**options)
    page = context.new_page()
    decoder = browser.new_page()

    def capture(stage):
        if not args.record:
            return
        page.evaluate("document.activeElement?.blur()")
        page.wait_for_timeout(200)
        path = output / (str(len(frames)).zfill(2) + "-" + stage + ".png")
        pixels = page.screenshot(path=str(path))
        rgba = decoder.evaluate(
            """async source => {const image=new Image();image.src='data:image/png;base64,'+source;await image.decode();const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;canvas.getContext('2d').drawImage(image,0,0);const data=canvas.getContext('2d').getImageData(0,0,image.width,image.height).data;let value='';for(let i=0;i<data.length;i+=8192)value+=String.fromCharCode(...data.subarray(i,i+8192));return btoa(value);} """,
            base64.b64encode(pixels).decode(),
        )
        (output / (str(len(frames)).zfill(2) + ".rgba")).write_bytes(
            base64.b64decode(rgba)
        )
        frames.append(
            {
                "stage": stage,
                "path": path.name,
                "sha256": hashlib.sha256(pixels).hexdigest(),
            }
        )
        page.wait_for_timeout(1100)

    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(args.url + "/login")
    page.get_by_role("button", name="Open analyst demo").click()
    page.get_by_role("heading", name="Ask a better question.").wait_for()
    page.screenshot(path=str(output / "home.png"), full_page=True)
    capture("overview")
    page.get_by_role("link", name="New investigation").first.click()
    page.get_by_label("Question", exact=True).fill("Claims paid by specialty")
    page.get_by_role("button", name="Investigate question").click()
    page.get_by_role("heading", name="Claims paid by specialty", exact=True).wait_for()
    page.get_by_role("button", name="Inspect record").wait_for(timeout=60000)
    assert page.locator("tbody tr").count() == 5
    page.screenshot(path=str(output / "investigation.png"), full_page=True)
    capture("executed-investigation")
    page.get_by_role("button", name="Executed SQL").click()
    assert "SELECT" in page.locator(".result-card pre").inner_text()
    capture("guarded-sql")
    page.get_by_role("button", name="Plan + assumptions").click()
    assert "latest" in page.locator(".result-card").inner_text().lower()
    page.get_by_role("button", name="Inspect record").click()
    page.get_by_role("dialog").wait_for()
    assert "result_sha256" in page.get_by_role("dialog").inner_text()
    page.keyboard.press("Escape")
    assert page.get_by_role("dialog").count() == 0
    expect(page.get_by_role("button", name="Inspect record")).to_be_focused()
    page.get_by_role("link", name="Investigations", exact=True).first.click()
    page.get_by_role("link", name="Claims paid by specialty").first.click()
    page.get_by_role("button", name="Inspect record").wait_for()
    page.reload()
    page.get_by_role("button", name="Inspect record").wait_for()
    page.get_by_role("link", name="Compare periods", exact=True).click()
    page.get_by_role("heading", name="Understand what changed.").wait_for()
    page.get_by_role("button", name="Investigate change").click()
    page.get_by_role("heading", name="Contributions by specialty").wait_for(
        timeout=60000
    )
    expect(page.locator(".contribution-row")).to_have_count(5)
    expect(page.locator(".factor-grid > div")).to_have_count(3)
    page.screenshot(path=str(output / "comparison.png"), full_page=True)
    capture("reconciled-periods")
    page.get_by_role("button", name="Verification", exact=True).click()
    expect(page.locator(".check-row")).to_have_count(15)
    assert "REVIEW" not in page.locator(".check-list").inner_text()
    capture("independent-checks")
    with page.expect_download() as download_info:
        page.get_by_role("button", name="Export evidence JSON").click()
    download_path = output / "comparison-export.json"
    download_info.value.save_as(str(download_path))
    exported = json.loads(download_path.read_text())
    assert exported["format"] == "querypilot-report-v1"
    assert exported["run"]["result"]["comparison"]["verified"]
    assert exported["run"]["result"]["evidence"]["result_sha256"]
    subprocess.run(
        [sys.executable, "scripts/evaluation/verify_report.py", str(download_path)], check=True
    )
    page.get_by_role("button", name="Result", exact=True).click()
    capture("exported-evidence")
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(output / "mobile.png"), full_page=True)
    page.get_by_role("link", name="Compare periods", exact=True).click()
    page.get_by_label("Comparison start", exact=True).fill("2027-04-01")
    page.get_by_label("Comparison end · exclusive", exact=True).fill("2027-07-01")
    page.get_by_role("button", name="Investigate change").click()
    page.get_by_role("heading", name="Comparison withheld:").wait_for(timeout=60000)
    assert page.locator(".comparison-totals").count() == 0
    assert page.locator(".factor-grid").count() == 0
    page.get_by_role("link", name="Metric catalog").click()
    page.get_by_role("heading", name="Start with a definition.").wait_for()
    expect(page.locator(".metric-grid article")).to_have_count(5, timeout=15000)
    # The recording is an actual static frontend asset in both the standalone
    # Nginx image and the cohosted Vercel app.
    player = browser.new_page()
    player.on("pageerror", lambda e: errors.append(str(e)))
    player.goto(args.url + "/recordings/")
    player.locator("video").wait_for()
    player.wait_for_function("() => document.querySelector('video')?.readyState >= 1")
    assert player.locator("video").evaluate("video => video.duration > 0")
    player.close()
    assert not errors, errors
    if args.record:
        video = page.video
        context.close()
        shutil.copyfile(video.path(), output / "continuous-walkthrough.webm")
        if args.publish_assets:
            media = Path("frontend/public/recordings")
            media.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(
                output / "continuous-walkthrough.webm", media / "querypilot.webm"
            )
            shutil.copyfile(output / frames[3]["path"], media / "poster.png")
    browser.close()
report = json.dumps(
    {
        "browser": "Chromium",
        "analyst_journey": True,
        "rows": 5,
        "sql": True,
        "plan": True,
        "dialog_escape": True,
        "reload_history": True,
        "mobile_overflow": False,
        "metric_contracts": 5,
        "compiled_comparison": True,
        "contribution_segments": 5,
        "shapley_factors": 3,
        "deterministic_comparison_checks": 15,
        "evidence_export": True,
        "offline_report_recheck": True,
        "future_period_withheld": True,
        "page_errors": errors,
        "paid_model_calls": 0,
        "recording_player": True,
    }
)

Path("artifacts/generated/browser-report.json").write_text(report + "\n")
if args.record:
    recording = {
        **json.loads(report),
        "url": args.url,
        "frames": frames,
        "video_sha256": hashlib.sha256(
            (output / "continuous-walkthrough.webm").read_bytes()
        ).hexdigest(),
        "recording": "Continuous actual Chromium capture; guided synthetic data, automated interactions, no live model inference",
        "captured_deployment_source": args.source_commit,
        "source_sha256": {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [
                Path("frontend/src/app/App.tsx"),
                *sorted(Path("frontend/src/features").rglob("*.tsx")),
                *sorted(Path("backend/app").rglob("*.py")),
            ]
        },
    }
    (output / "recording.json").write_text(json.dumps(recording, indent=2) + "\n")
print(report)
