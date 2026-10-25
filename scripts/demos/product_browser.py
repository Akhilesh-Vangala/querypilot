"""Actual product browser rehearsal; fixtures are not customer feedback or live AI.

Optionally retain a continuous readable browser recording and pinned axe audits.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import time
import httpx
from playwright.sync_api import expect, sync_playwright

RELAY_SOURCE = 'order_id,ordered_units,received_units,invoiced_units,available_units,unit_price,delivery_confirmed,inventory_pool\nCLIENT-17,14,9,14,7,4.20,true,SKU-9\nCLIENT-18,8,3,8,7,4.20,true,SKU-9\n'
QUERY_SOURCE = 'region,amount,status\nNorth,0.10,done\nNorth,0.20,done\nSouth,5.00,pending\n'
STORE = """async ({name,action,id})=>{const db=await new Promise((resolve,reject)=>{const r=indexedDB.open(name,1);r.onsuccess=()=>resolve(r.result);r.onerror=reject});const result=await new Promise((resolve,reject)=>{const tx=db.transaction('investigations',action==='tamper'?'readwrite':'readonly'),store=tx.objectStore('investigations'),req=action==='tamper'?store.get(id):store.getAll();let result;req.onsuccess=()=>{result=req.result;if(action==='tamper'){result.report.summary.source_rows=99999;store.put(result)}};tx.oncomplete=()=>resolve(action==='tamper'?true:result);tx.onerror=reject});db.close();return result}"""


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url');parser.add_argument('--output',default='artifacts/generated/product-browser')
    parser.add_argument('--record',action='store_true');parser.add_argument('--axe')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    relay=(root/'backend/src/relayops').is_dir();brand='RelayOps' if relay else 'QueryPilot'
    source=RELAY_SOURCE if relay else QUERY_SOURCE
    namespace='relayops-workspace-v1' if relay else 'querypilot-workspace-v1'
    noun='investigation' if relay else 'analysis';plural='investigations' if relay else 'analyses'
    output=root/args.output;output.mkdir(parents=True,exist_ok=True)
    server=log=None;url=args.url;checks=[];errors=[];audits=[];frames=[]
    if not url:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        url=f'http://127.0.0.1:{port}'
        prefix='RELAY' if relay else 'QUERY'
        env=dict(os.environ,RELAY_ALLOW_LIVE='0',ALLOW_LIVE_AI='false',ANTHROPIC_API_KEY='',OPENAI_API_KEY='')
        env.update({prefix+'_REPORT_SIGNING_KEY':secrets.token_urlsafe(64),prefix+'_SUPABASE_URL':'',prefix+'_SUPABASE_PUBLISHABLE_KEY':''})
        env['RELAY_DEMO_SECRET']=secrets.token_urlsafe(64)
        log=(output/'server.log').open('w')
        server=subprocess.Popen([sys.executable,'-m','uvicorn','app:app' if relay else 'index:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=root,env=env,stdout=log,stderr=log)
        for _ in range(200):
            try:
                if httpx.get(url+'/api/uploads/capabilities',timeout=1).status_code==200:break
            except httpx.HTTPError:pass
            time.sleep(.1)
        else:raise RuntimeError('Product server not ready')
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            opts=dict(viewport={'width':1440,'height':1000},reduced_motion='reduce')
            if args.record:opts.update(record_video_dir=str(output/'video'),record_video_size={'width':1440,'height':1000})
            context=browser.new_context(**opts);page=context.new_page()
            page.on('pageerror',lambda e:errors.append(str(e)))
            def capture(name):
                page.evaluate('document.activeElement?.blur();window.scrollTo(0,0)');page.screenshot(path=str(output/(name+'.png')),full_page=True);frames.append(name+'.png')
                if args.axe:
                    page.evaluate(Path(args.axe).read_text())
                    result=page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})")
                    audits.append({'view':name,'violations':result['violations'],'passes':len(result['passes']),'incomplete':len(result['incomplete'])})
                    (output/'accessibility.json').write_text(json.dumps(audits,indent=2))
                    assert not result['violations'],[(v['id'],[n['target'] for n in v['nodes']]) for v in result['violations']]
                if args.record:page.wait_for_timeout(1300)
            def choose(text=source):
                page.locator('#file').set_input_files({'name':'customer-export.csv','mimeType':'text/csv','buffer':text.encode()})
                expect(page.locator('#review-rules')).to_be_enabled()
            def rules():
                page.locator('#review-rules').click()
                if not relay:
                    # Suggestions are optional and can arrive after profile on a
                    # cold serverless start. Review the intended contract explicitly.
                    page.locator('#mapping-measure').select_option('c1');page.locator('#mapping-group').select_option('c0')
                    page.locator('#mapping-filter').select_option('c2');page.locator('#filter-value').fill('done')
            def run():
                rules();page.locator('#review-definition').click();expect(page.locator('#analyze')).to_be_disabled()
                page.locator('#confirm-rules').check();page.locator('#analyze').click()
            def evidence():return json.loads(page.locator('#evidence pre').text_content())
            def save():
                previous=page.url;page.get_by_role('button',name='Save '+noun,exact=True).click()
                expect(page.locator('#confirm-save')).to_be_disabled();expect(page.locator('#save-destination option[value=cloud]')).to_have_attribute('disabled','')
                page.locator('#save-consent').check();page.locator('#confirm-save').click()
                expect(page).not_to_have_url(previous);expect(page).to_have_url(re.compile('/workspace/'+plural+'/'))
                expect(page.locator('#output')).to_be_visible();return page.url
            def stored():return page.evaluate(STORE,{'name':namespace,'action':'list'})
            page.goto(url+'/');expect(page.get_by_role('heading',level=1)).to_contain_text('Resolve exceptions' if relay else 'Good questions.')
            capture('01-home');page.get_by_role('link',name='Open workspace',exact=True).click()
            expect(page.get_by_role('heading',name='Your first '+noun+' starts here.')).to_be_visible();capture('02-empty-workspace')
            checks.append('real-empty-workspace-no-invented-metrics')
            page.get_by_role('link',name='Projects',exact=True).click();page.get_by_role('button',name='Create project',exact=True).click()
            page.locator('#project-name').fill('October review');page.locator('#project-consent').check()
            page.get_by_role('dialog').get_by_role('button',name='Create project',exact=True).click()
            expect(page.get_by_role('dialog')).not_to_be_visible()
            page.get_by_role('link',name='Overview',exact=True).click();page.get_by_role('link',name=re.compile('^New '+noun)).click()
            choose();page.locator('#investigation-title' if relay else '#analysis-title').fill('Customer export review')
            page.locator('#project-select').select_option(label='October review · This device');capture('03-source-preview')
            assert stored()==[]
            rules();capture('04-business-rules');page.locator('#review-definition').click()
            expect(page.locator('#analyze')).to_be_disabled();capture('05-reviewed-contract')
            page.locator('#confirm-rules').check();page.locator('#analyze').click()
            expect(page.locator('#output')).to_be_visible(timeout=30000);expect(page.locator('#verification')).to_have_text('Independent checks passed')
            result=evidence();assert result['live_ai'] is False
            if relay:
                assert result['summary']['resolvable']==1 and result['summary']['needs_information']==1
                assert result['results'][0]['plan']['actions'][0]['amount']==2100
                expect(page.locator('#download-csv')).to_be_disabled()
                page.locator('#consent').check();page.locator('#approve').click();expect(page.locator('#download-csv')).to_be_enabled(timeout=30000)
                result=evidence();assert result['summary']['approved_export'] and len(result['results'][0]['receipts'])==4
                checks.append('separate-visitor-source-plan-bound-approval-and-four-checked-receipts')
            else:
                assert result['summary']['overall_value']=='0.30' and result['summary']['included_rows']==2 and result['summary']['excluded_rows']==1
                assert result['results'][0]['segment']=='North'
            if not relay:
                provenance=page.get_by_role('region',name='Execution provenance')
                expect(provenance).to_contain_text('No model calls')
                provenance.get_by_text('Inspect run identity',exact=True).click()
                expect(provenance).to_contain_text(result['run_record']['run_id'])
                expect(provenance).to_contain_text(result['run_record']['contract_sha256'])
                provenance.get_by_text('Inspect run identity',exact=True).click()
            capture('06-verified-report')
            page.get_by_role('tab').first.focus();page.keyboard.press('ArrowRight')
            expect(page.get_by_role('tab').nth(1)).to_be_focused();expect(page.get_by_role('tab').nth(1)).to_have_attribute('aria-selected','true');capture('07-quality-or-stock')
            page.get_by_role('tab').nth(2).click();capture('08-execution-checks')
            for kind in ('json','csv'):
                with page.expect_download() as value:page.locator('#download-'+kind).click()
                value.value.save_as(output/('result.'+kind));assert (output/('result.'+kind)).stat().st_size>20
            saved_url=save();capture('09-saved-report');page.reload();expect(page.locator('#verification')).to_have_text('Independent checks passed')
            if relay:expect(page.locator('#download-csv')).to_be_enabled()
            checks+=['real-source-defined-result-and-downloads','keyboard-tabs-and-explicit-save-consent','signed-immutable-device-save-and-reload']
            page.get_by_role('link',name='Investigations' if relay else 'Analyses',exact=True).click()
            expect(page.get_by_role('link',name='Customer export review',exact=True)).to_be_visible();capture('10-saved-history')
            page.get_by_role('link',name='Settings',exact=True).click()
            with page.expect_download() as backup:page.get_by_role('button',name='Export device backup',exact=True).click()
            backup.value.save_as(output/'device-backup.json');video=page.video;context.close()
            if args.record:video.save_as(str(output/'continuous-walkthrough.webm'))
            context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(url+'/uploads');choose(source.replace(',true,',',maybe,') if relay else source.replace('0.10','bad'));run()
            expect(page.locator('#error')).to_be_visible();expect(page.locator('#output')).not_to_be_visible()
            page.get_by_role('button',name='Inspect affected records',exact=True).click();expect(page.locator('#preview-content')).to_contain_text('maybe' if relay else 'bad');capture('11-error-recovery')
            choose();page.route('**/api/uploads/analyze-stream',lambda route:route.abort('failed'));run()
            expect(page.locator('#error')).to_contain_text('Connection interrupted');page.unroute('**/api/uploads/analyze-stream')
            page.locator('#review-definition').click();page.locator('#confirm-rules').check();page.locator('#analyze').click();expect(page.locator('#output')).to_be_visible()
            first=save();original_id=first.split('/'+plural+'/')[1].split('?')[0]
            if relay:
                expect(page.locator('#approve')).not_to_be_visible();page.get_by_role('button',name='Reassess before approval',exact=True).click()
            else:
                page.get_by_role('button',name='Edit rules & rerun',exact=True).first.click();page.locator('#operation').select_option('average')
            page.locator('#review-definition').click();page.locator('#confirm-rules').check();page.locator('#analyze').click();expect(page.locator('#output')).to_be_visible()
            if not relay:assert evidence()['summary']['overall_value']=='0.15'
            second=save();assert first!=second and len(stored())==2
            checks+=['structured-invalid-cell-inspection-and-network-retry','rerun-creates-new-snapshot-preserving-original']
            page.evaluate(STORE,{'name':namespace,'action':'tamper','id':original_id});page.goto(first)
            expect(page.locator('#error')).to_contain_text('could not be authenticated');expect(page.locator('#output')).not_to_be_visible()
            checks.append('tampered-report-refused-on-reopen')
            page.locator('#clear').click();page.locator('#confirm-clear').click();choose();run();expect(page.locator('#output')).to_be_visible()
            for width in (320,390,768,1440):
                page.set_viewport_size({'width':width,'height':900});page.screenshot(path=str(output/('debug-'+str(width)+'.png')),full_page=True);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
                page.screenshot(path=str(output/('report-'+str(width)+'.png')),full_page=True)
            checks.append('responsive-results-320-390-768-1440')
            page.set_viewport_size({'width':1440,'height':1000});page.keyboard.press('Control+k');expect(page.get_by_role('dialog')).to_be_visible();page.keyboard.press('Escape');expect(page.get_by_role('dialog')).not_to_be_visible()
            page.locator('#clear').click();page.locator('#confirm-clear').click();page.get_by_role('link',name='Sign in',exact=True).click()
            expect(page.get_by_role('heading',name='Cloud accounts aren’t connected yet.')).to_be_visible();capture('12-account-status')
            page.get_by_role('link',name='Settings',exact=True).click();capture('13-storage-settings');page.get_by_role('link',name='Quick guide',exact=True).click();capture('14-quick-guide')
            checks.append('command-dialog-and-truthful-unconfigured-account-state');context.close()
            context=browser.new_context(viewport={'width':1440,'height':1000});page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(url+'/workspace/settings');page.locator('#backup-file').set_input_files(output/'device-backup.json')
            expect(page.locator('#confirm-restore')).to_be_disabled();page.locator('#restore-consent').check();page.locator('#confirm-restore').click()
            expect(page).to_have_url(re.compile('/workspace/history'));page.get_by_role('link',name='Customer export review',exact=True).click()
            expect(page.locator('#verification')).to_have_text('Independent checks passed');assert page.url!=saved_url
            checks.append('consented-portable-backup-source-and-signature-revalidation')
            storage_source=(root/'frontend/src/features/product/lib/storage.js').read_text()
            # Test the exact owned source module in Chromium's real IndexedDB.
            # Same-origin test interception preserves the application's strict CSP;
            # no test globals or test-only routes are added to shipped code.
            page.route('**/__product_storage_rehearsal__.js',lambda route:route.fulfill(body=storage_source,content_type='text/javascript'))
            quota=page.evaluate("""async()=>{const {saved}=await import('/__product_storage_rehearsal__.js');const original=(await saved.list())[0];const results=await Promise.allSettled(Array.from({length:53},()=>saved.put({...original,id:crypto.randomUUID()},true)));const projects=await Promise.allSettled(Array.from({length:25},(_,i)=>saved.project({id:crypto.randomUUID(),name:'Quota '+i,storage:'device'})));return {count:(await saved.list()).length,saved:results.filter(r=>r.status==='fulfilled').length,rejected:results.filter(r=>r.status==='rejected').length,projects:(await saved.projects()).length,project_rejected:projects.filter(r=>r.status==='rejected').length}}""")
            assert quota=={'count':50,'saved':49,'rejected':4,'projects':20,'project_rejected':6},quota
            checks.append('actual-IndexedDB-competing-snapshot-and-project-quota-transactions')
            context.close();browser.close()
        assert not errors,errors
        sources=[root/('app.py' if relay else 'index.py')]
        for directory in ('backend/src/relayops','frontend/apps/product') if relay else ('backend/app','frontend/src'):
            sources += [f for f in sorted((root/directory).rglob('*')) if f.suffix in ('.py','.js','.css','.html','.tsx','.ts')]
        if not relay:
            sources += [root/f for f in ('frontend/index.html','frontend/package.json','frontend/package-lock.json','frontend/vite.config.ts')]
            sources += [f for f in sorted((root/'frontend/public').rglob('*')) if f.suffix in ('.html','.css','.js')]
            sources += list(sorted((root/'scripts/demos').glob('*.py')))
        build_hashes={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((root/'frontend/dist/assets').glob('*')) if f.suffix in ('.js','.css')} if not relay else {}
        report=dict(build_sha256=build_hashes,project=brand,passed=True,url=url,paid_model_calls=0,actual_user_feedback=False,checks=checks,page_errors=errors,frames=frames,automated_accessibility_views=len(audits),source_sha256={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources})
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','frames')}))
    finally:
        if server:
            server.terminate()
            try:server.wait(timeout=10)
            except subprocess.TimeoutExpired:server.kill();server.wait()
        if log:log.close()

if __name__=='__main__':main()
