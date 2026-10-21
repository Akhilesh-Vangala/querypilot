"""Real file-picker imports and domain results; never model/customer quality evidence."""
import argparse,base64,csv,hashlib,io,json,os,secrets,socket,subprocess,sys,time
from pathlib import Path
import httpx
from openpyxl import Workbook
from playwright.sync_api import sync_playwright,expect


def main():
 p=argparse.ArgumentParser();p.add_argument('--url');p.add_argument('--output',default='artifacts/generated/import-browser');p.add_argument('--axe');args=p.parse_args()
 root=Path(__file__).resolve().parents[2];relay=(root/'backend/src/relayops').is_dir();verify=(root/'backend/src/vdir').is_dir();brand='RelayOps' if relay else 'VerifyOps' if verify else 'QueryPilot'
 out=root/args.output;out.mkdir(parents=True,exist_ok=True);server=log=None;url=args.url
 if not url:
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  url=f'http://127.0.0.1:{port}';prefix='RELAY' if relay else 'VDIR' if verify else 'QUERY'
  env=dict(os.environ,VDIR_LOAD_DOTENV='0',RELAY_ALLOW_LIVE='0',ALLOW_LIVE_AI='false',ANTHROPIC_API_KEY='',OPENAI_API_KEY='')
  env.update({prefix+'_DEMO_SECRET':secrets.token_urlsafe(64),prefix+'_REPORT_SIGNING_KEY':secrets.token_urlsafe(64),prefix+'_SUPABASE_URL':'',prefix+'_SUPABASE_PUBLISHABLE_KEY':''})
  log=(out/'server.log').open('w');server=subprocess.Popen([sys.executable,'-m','uvicorn','app:app' if relay or verify else 'index:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=root,env=env,stdout=log,stderr=log)
  for _ in range(200):
   try:
    if httpx.get(url+'/api/uploads/capabilities',timeout=1).status_code==200:break
   except httpx.HTTPError:pass
   time.sleep(.1)
  else:raise RuntimeError('Import rehearsal server failed to start')
 errors=[];checks=[];audits=[]
 try:
  if relay:source='order_id,ordered_units,received_units,invoiced_units,available_units,unit_price,delivery_confirmed,inventory_pool\nA,10,7,10,5,1.25,true,P\nB,10,7,10,5,1.25,true,P\n'
  elif verify:source='event_id,amount,category,status\nA,12.34,X,completed\nA,12.34,X,completed\nB,5.00,Y,pending\n'
  else:source='region,amount,status\nNorth,0.10,done\nNorth,0.20,done\nSouth,5.00,pending\n'
  headers,*rows=list(csv.reader(io.StringIO(source)));objects=[dict(zip(headers,row)) for row in rows]
  tsv=io.StringIO();writer=csv.writer(tsv,delimiter='\t',lineterminator='\n');writer.writerow(headers);writer.writerows(rows)
  book=Workbook();sheet=book.active;sheet.title='Business data';sheet.append(headers)
  for row in rows:sheet.append(row)
  other=book.create_sheet('Other data');other.append(['id','value']);other.append(['other',99]);buffer=io.BytesIO();book.save(buffer);book.close()
  fixtures={'csv':source.encode(),'tsv':tsv.getvalue().encode(),'json':json.dumps(objects).encode(),'jsonl':'\n'.join(json.dumps(o) for o in objects).encode(),'xlsx':buffer.getvalue()}
  with sync_playwright() as p:
   browser=p.chromium.launch();context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(url+'/uploads');page.locator('#file').wait_for()
   def audit(label):
    if args.axe:
     page.evaluate(Path(args.axe).read_text());result=page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})")
     audits.append({'view':label,'violations':result['violations']});assert not result['violations'],[(v['id'],[n['target'] for n in v['nodes']]) for v in result['violations']]
   for extension,data in fixtures.items():
    page.locator('#file').set_input_files({'name':'business-export.'+extension,'mimeType':'application/octet-stream','buffer':data})
    if extension=='xlsx':
     expect(page.locator('#import-sheet-dialog')).to_be_visible();audit('worksheet-choice');page.locator('#import-sheet').select_option('Business data');page.locator('#confirm-sheet').click();expect(page.locator('#import-sheet-dialog')).not_to_be_visible()
    expect(page.locator('#file-info')).to_contain_text('business-export.'+extension);page.locator('#review-rules').click()
    if relay:
     for i,key in enumerate(('order_id','ordered','received','invoiced','available','unit_price','confirmed','pool')):page.locator('#mapping-'+key).select_option('c'+str(i))
    elif verify:
     for i,key in enumerate(('key','amount','group','status')):page.locator('#mapping-'+key).select_option('c'+str(i))
     page.locator('#eligible-status').fill('completed') if page.locator('#eligible-status').count() else None
    else:
     page.locator('#mapping-measure').select_option('c1');page.locator('#mapping-group').select_option('c0');page.locator('#mapping-filter').select_option('c2');page.locator('#filter-value').fill('done')
    page.locator('#review-definition').click();page.locator('#confirm-rules').check();page.locator('#analyze').click();expect(page.locator('#output')).to_be_visible(timeout=30000)
    expect(page.locator('#verification')).to_have_text('Independent checks passed');report=json.loads(page.locator('#evidence pre').text_content())
    assert report['live_ai'] is False
    if relay:
     assert report['summary']['resolvable']==1 and report['summary']['needs_information']==1
     page.locator('#consent').check();page.locator('#approve').click();expect(page.locator('#download-csv')).to_be_enabled(timeout=30000)
     report=json.loads(page.locator('#evidence pre').text_content());assert len(report['results'][0]['receipts'])==4 and report['results'][0]['plan']['actions'][0]['amount']==375
    elif verify:assert report['summary']['verified_total_cents']==1234
    else:assert report['summary']['overall_value']=='0.30' and report['summary']['included_rows']==2
    checks.append(extension+'-file-picker-through-actual-domain-result')
    if extension=='xlsx':audit('excel-verified-report');page.screenshot(path=str(out/'excel-result.png'),full_page=True)
    page.locator('#clear').click();page.locator('#confirm-clear').click();expect(page.locator('#file')).to_be_visible()
   # Cancelling a replacement must keep the already inspected source intact.
   page.locator('#file').set_input_files({'name':'preserved.csv','mimeType':'text/csv','buffer':source.encode()});expect(page.locator('#review-rules')).to_be_enabled()
   page.locator('#file').set_input_files({'name':'cancel.xlsx','mimeType':'application/octet-stream','buffer':buffer.getvalue()});expect(page.locator('#import-sheet-dialog')).to_be_visible();page.keyboard.press('Escape');expect(page.locator('#import-sheet-dialog')).not_to_be_visible();expect(page.locator('#output')).not_to_be_visible();expect(page.locator('#review-rules')).to_be_enabled();expect(page.locator('#file-info')).to_contain_text('preserved.csv');checks.append('worksheet-Escape-cancel-preserves-previous-source')
   page.locator('#file').set_input_files({'name':'invalid.json','mimeType':'application/json','buffer':b'[{"id":1,"id":2}]'});expect(page.locator('#error')).to_contain_text('Duplicate JSON');expect(page.locator('#output')).not_to_be_visible();checks.append('ambiguous-JSON-withholds-results')
   page.locator('#file').set_input_files({'name':'unsupported.pdf','mimeType':'application/pdf','buffer':b'%PDF-invalid'});expect(page.locator('#error')).to_contain_text('CSV');checks.append('unsupported-type-guidance')
   for width in (320,390,768,1440):
    page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
   context.close();browser.close()
  import runpy
  monitor=runpy.run_path(str(root/'scripts/checks/public_health.py'))
  public_health=monitor['Probe'](url).run()
  (out/'public-health.json').write_text(json.dumps(public_health,indent=2)+'\n')
  assert public_health['passed'] and public_health['live_model_calls']==0
  assert not errors,errors
  result=dict(project=brand,passed=True,url=url,checks=checks,page_errors=errors,accessibility=audits,paid_model_calls=0,actual_user_feedback=False)
  (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='accessibility'}))
 finally:
  if server:
   server.terminate()
   try:server.wait(timeout=10)
   except subprocess.TimeoutExpired:server.kill();server.wait()
  if log:log.close()
if __name__=='__main__':main()
