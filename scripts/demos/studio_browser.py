"""Real route, responsive and accessibility rehearsal for both studio surfaces."""
import argparse
import json
import re
from pathlib import Path
from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--axe', required=True)
    parser.add_argument('--output', default='artifacts/generated/studio-browser')
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    axe = Path(args.axe).read_text()
    observations, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        page.on('pageerror', lambda error: errors.append(str(error)))

        def inspect(label):
            expect(page.get_by_role('heading', level=1)).to_be_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), label
            page.evaluate(axe)
            result = page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})")
            observations.append({'view': label, 'violations': result['violations'], 'passes': len(result['passes'])})
            (out / 'accessibility.json').write_text(json.dumps(observations, indent=2))
            page.screenshot(path=str(out / (label + '.png')), full_page=True)
            assert not result['violations'], [(v['id'], [n['target'] for n in v['nodes']]) for v in result['violations']]

        for width in (320, 390, 768, 1440):
            page.set_viewport_size({'width': width, 'height': 1000})
            page.goto(args.url + '/')
            expect(page.get_by_role('heading',level=1)).to_contain_text('Good questions.')
            inspect('home-' + str(width))
        page.get_by_role('link', name='Open workspace', exact=True).click()
        inspect('file-workspace')
        # Real navigation between the distinct file and warehouse workspaces.
        page.get_by_role('link', name='Investigation studio', exact=False).click()
        expect(page).to_have_url(re.compile(r'/(?:login|demo)$'))
        expect(page.get_by_role('heading',level=1)).not_to_contain_text('Make the definition')
        if page.get_by_role('button',name='Open analyst demo').is_visible():
            inspect('warehouse-login')
            page.get_by_role('button',name='Open analyst demo').click()
        expect(page.get_by_role('heading', level=1)).to_contain_text('Ask a better question')
        for route, label in [('/demo', 'warehouse-overview'), ('/new', 'warehouse-question'),
                             ('/compare', 'warehouse-comparison'), ('/history', 'warehouse-history'),
                             ('/metrics', 'warehouse-metrics'), ('/schema', 'warehouse-schema'),
                             ('/settings', 'warehouse-settings')]:
            page.goto(args.url + route)
            inspect(label)
        for width in (320, 390, 768):
            page.set_viewport_size({'width': width, 'height': 1000})
            page.goto(args.url + '/compare')
            inspect('comparison-' + str(width))
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.goto(args.url + '/demo')
        page.get_by_role('link',name='Use your own data',exact=False).click()
        expect(page.locator('#file')).to_be_attached()
        assert not errors, errors
        browser.close()
    report = {'passed': True, 'views': len(observations), 'page_errors': errors,
              'paid_model_calls': 0, 'navigation_between_studios': True,
              'mobile_home_and_comparison': [320,390,768], 'axe_violations': 0}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
