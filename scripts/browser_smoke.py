"""Actual Chromium analyst journey, provenance dialog and mobile layout."""

import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:3007")
parser.add_argument("--screenshots", default="artifacts/generated/browser")
args = parser.parse_args()
output = Path(args.screenshots)
output.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(args.url + "/login")
    page.get_by_role("button", name="Open analyst demo").click()
    page.get_by_role("heading", name="Ask a better question.").wait_for()
    page.screenshot(path=str(output / "home.png"), full_page=True)
    page.get_by_role("link", name="New investigation").first.click()
    page.get_by_label("Question", exact=True).fill("Claims paid by specialty")
    page.get_by_role("button", name="Investigate question").click()
    page.get_by_role("heading", name="Claims paid by specialty", exact=True).wait_for()
    page.get_by_role("button", name="Inspect record").wait_for(timeout=60000)
    assert page.locator("tbody tr").count() == 5
    page.screenshot(path=str(output / "investigation.png"), full_page=True)
    page.get_by_role("button", name="Executed SQL").click()
    assert "SELECT" in page.locator(".result-card pre").inner_text()
    page.get_by_role("button", name="Plan + assumptions").click()
    assert "latest" in page.locator(".result-card").inner_text().lower()
    page.get_by_role("button", name="Inspect record").click()
    page.get_by_role("dialog").wait_for()
    assert "result_sha256" in page.get_by_role("dialog").inner_text()
    page.keyboard.press("Escape")
    assert page.get_by_role("dialog").count() == 0
    page.get_by_role("link", name="Investigations", exact=True).first.click()
    page.get_by_role("link", name="Claims paid by specialty").first.click()
    page.get_by_role("button", name="Inspect record").wait_for()
    page.reload()
    page.get_by_role("button", name="Inspect record").wait_for()
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.screenshot(path=str(output / "mobile.png"), full_page=True)
    page.get_by_role("link", name="Metric catalog").click()
    page.get_by_role("heading", name="Start with a definition.").wait_for()
    assert page.locator(".metric-grid article").count() == 5
    assert not errors, errors
    browser.close()
print(
    json.dumps(
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
            "page_errors": errors,
            "paid_model_calls": 0,
        }
    )
)
