"""Real prompt/auth/trace/follow-up journey. No model request is enabled here."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--axe', required=True)
    parser.add_argument('--output', default='artifacts/generated/agent-desk-browser')
    args = parser.parse_args()
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    axe = Path(args.axe).read_text(); audits = []; errors = []; checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':1440,'height':1000}, reduced_motion='reduce')
        page.on('pageerror',lambda e:errors.append(str(e)))
        def capture(name):
            page.evaluate('document.activeElement?.blur();window.scrollTo(0,0)')
            page.screenshot(path=str(out/(name+'.png')),full_page=True)
            page.evaluate(axe)
            a=page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})")
            audits.append({'view':name,'violations':a['violations'],'passes':len(a['passes'])})
            (out/'accessibility.json').write_text(json.dumps(audits,indent=2))
            assert not a['violations'],[(v['id'],[n['target'] for n in v['nodes']]) for v in a['violations']]
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),name
        page.goto(args.url+'/')
        composer=page.get_by_role('region',name='Warehouse question composer')
        expect(composer.get_by_role('button',name='Review question')).to_be_disabled()
        composer.get_by_role('button',name='Explore spend',exact=False).click()
        question='Claims paid by specialty'
        expect(composer.get_by_label('Ask the warehouse')).to_have_value(question)
        capture('01-landing-composer')
        composer.get_by_role('button',name='Review question',exact=False).click()
        expect(page).to_have_url(re.compile('/login$'))
        page.get_by_role('button',name='Open analyst demo',exact=False).click()
        expect(page).to_have_url(re.compile(r'/new\?question='))
        expect(page.get_by_label('Question',exact=True)).to_have_value(question)
        expect(page.locator('#mode')).to_have_value('baseline')
        capture('02-investigation-brief')
        with page.expect_response(lambda r:urlparse(r.url).path=='/api/analyses' and r.request.method=='POST') as response:
            page.locator('#question').press('Control+Enter')
        assert response.value.ok
        expect(page.get_by_role('button',name='Inspect record',exact=True)).to_be_visible(timeout=60000)
        first_url=page.url
        trace=page.get_by_role('region',name='Agent execution trace')
        expect(trace).to_contain_text('Guided baseline');expect(trace).to_contain_text('Not used')
        with page.expect_download() as dl:page.get_by_role('button',name='Export evidence JSON',exact=False).click()
        dl.value.save_as(out/'executed-report.json')
        result=json.loads((out/'executed-report.json').read_text())['run']['result'];events=result['events']
        assert len(events)>0
        expect(trace.locator('.agent-event')).to_have_count(len(events))
        assert result['rows'] and result['sql']
        capture('03-observed-execution')
        trace.get_by_label('Execution event filter').select_option('tools')
        expected=[e for e in events if e.get('tool') or e['stage'] in ('execute_query','execute_comparison','compile_metric_contract')]
        expect(trace.locator('.agent-event')).to_have_count(len(expected));assert expected
        trace.locator('.agent-event').first.click();trace.get_by_text('Inspect event JSON',exact=True).click()
        selected=json.loads(trace.locator('.agent-event-detail pre').inner_text());assert selected==expected[0]
        capture('04-actual-tool-payload')
        trace.get_by_label('Execution event filter').select_option('checks')
        checked=[e for e in events if re.search('reconcil|check|validat',e['stage'])]
        expect(trace.locator('.agent-event')).to_have_count(len(checked));assert checked
        capture('05-verification-events')
        trace.get_by_role('button',name='Open analysis plan',exact=False).click()
        expect(page.locator('.result-card')).to_contain_text(result['plan']['objective'])
        checks+=['prompt-review-and-sign-in-preserve-question-without-auto-execution','keyboard-submission-produces-real-guarded-result','trace-events-and-filtered-payload-equal-exported-backend-evidence','plan-link-selects-actual-published-plan']
        page.get_by_role('link',name='Refine this question',exact=False).click()
        expect(page.locator('#question')).to_have_value(question)
        expect(page.get_by_role('link',name=first_url.rsplit('/',1)[-1][:8],exact=False)).to_have_attribute('href',urlparse(first_url).path)
        capture('06-independent-followup')
        page.goto(first_url)
        page.get_by_role('link',name='Compare a reviewed metric',exact=False).click()
        expect(page.locator('#metric')).to_have_value('claims_paid')
        capture('07-reviewed-comparison')
        # Query parameter changes on the same component must follow browser history.
        page.goto(args.url+'/compare?metric=declined_referral_rate&dimension=specialty')
        expect(page.locator('#metric')).to_have_value('declined_referral_rate')
        page.goto(first_url)
        page.get_by_role('link',name='New investigation',exact=True).click()
        page.get_by_role('button',name='Explain a change',exact=False).click()
        page.get_by_role('button',name='Investigate question',exact=False).click()
        expect(page.get_by_role('button',name='Inspect record',exact=True)).to_be_visible(timeout=60000)
        trace=page.get_by_role('region',name='Agent execution trace');trace.get_by_label('Execution event filter').select_option('checks')
        expect(trace).to_contain_text('reconcile metric evidence')
        capture('08-comparison-execution')
        for width,name in ((320,'09-mobile-trace'),):
            page.set_viewport_size({'width':width,'height':1000});capture(name)
        page.get_by_role('link',name='Refine this question',exact=False).click()
        page.set_viewport_size({'width':390,'height':1000});capture('10-mobile-brief')
        checks+=['followup-links-preserve-question-reference-and-reviewed-metric','comparison-inspector-shows-real-reconciliation-events','mobile-trace-and-brief-without-overflow']
        page.set_viewport_size({'width':1440,'height':1000})
        page.goto(args.url+'/demo');page.get_by_role('button',name='Sign out',exact=True).click()
        expect(page).to_have_url(re.compile('/login$'))
        # Exercise the exact shipped return-path guard without navigating to an external host.
        for target in ('https://invalid.example/','//invalid.example/','/api/auth/logout','/new\\evil'):
            page.evaluate("value=>history.replaceState({...history.state,usr:{from:value}},'',location.href)",target)
            page.reload();page.get_by_role('button',name='Open analyst demo',exact=False).click()
            expect(page).to_have_url(args.url+'/demo')
            page.get_by_role('button',name='Sign out',exact=True).click();expect(page).to_have_url(re.compile('/login$'))
        checks.append('sign-in-return-rejects-external-api-and-backslash-destinations')
        assert not errors,errors
        browser.close()
    report={'passed':True,'url':args.url,'checks':checks,'accessibility_views':len(audits),'axe_violations':0,'page_errors':errors,'paid_model_calls':0,'actual_user_feedback':False}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
