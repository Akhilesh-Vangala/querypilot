"""Public synthetic availability check. No keys, customer data or model calls."""
import argparse
import base64
import copy
import csv
from datetime import datetime, timezone
import hashlib
from http.cookiejar import CookieJar
import io
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import build_opener, HTTPCookieProcessor, HTTPRedirectHandler, Request
import zipfile
from xml.sax.saxutils import escape

PROJECT = "QueryPilot"
CANONICAL = "https://querypilot-five.vercel.app"


class ProbeFailed(ValueError):
    pass


def require(condition, step):
    if not condition:
        raise ProbeFailed(step)


def terminal_result(text):
    events=[]
    for frame in text.replace('\r\n','\n').split('\n\n'):
        fields={}
        for line in frame.splitlines():
            if line.startswith(('event:','data:')):
                key,value=line.split(':',1);fields[key]=value.strip()
        if 'event' in fields:
            events.append((fields['event'],json.loads(fields.get('data','null'))))
    terminals=[v for kind,v in events if kind in ('result','problem')]
    require(len(terminals)==1 and events[-1][0]=='result','stream-terminal-result')
    require(any(kind=='stage' for kind,_ in events),'stream-observed-progress')
    return terminals[0]


def workbook(rows):
    sheet=[]
    for i,row in enumerate(rows,1):
        cells=''.join(f'<c r="{chr(65+j)}{i}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>' for j,value in enumerate(row))
        sheet.append(f'<row r="{i}">{cells}</row>')
    files={
      '[Content_Types].xml':'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
      '_rels/.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
      'xl/workbook.xml':'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Data" sheetId="1" r:id="rId1"/></sheets></workbook>',
      'xl/_rels/workbook.xml.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
      'xl/worksheets/sheet1.xml':'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join(sheet)+'</sheetData></worksheet>'}
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,body in files.items():archive.writestr(name,body)
    return output.getvalue()


def fixture():
    if PROJECT=='VerifyOps':
        return ('id,amount,group,status\na,0.10,A,completed\na,0.10,A,completed\nb,0.20,A,completed\n',
            {'key':'c0','amount':'c1','group':'c2','status':'c3'},
            {'unit':'dollars','eligible_status':'completed','reported_total':'0.40'})
    if PROJECT=='RelayOps':
        return ('order_id,ordered,received,invoiced,available,unit_price,confirmed,pool\nP-1,5,3,5,2,1.25,true,SKU-A\n',
            dict(zip(('order_id','ordered','received','invoiced','available','unit_price','confirmed','pool'),('c'+str(n) for n in range(8)))),{'unit':'dollars'})
    return ('region,amount,status\nA,0.10,done\nA,0.20,done\nA,9.99,pending\n',
            {'group':'c0','measure':'c1','filter':'c2'},{'operation':'sum','filter_value':'done'})


def validate_result(result):
    require(isinstance(result,dict) and result.get('project')==PROJECT and result.get('live_ai') is False,'result-scope')
    checks=result.get('checks',{})
    require(bool(checks) and all(v is True for v in checks.values()),'independent-checks')
    summary=result.get('summary',{})
    if PROJECT=='VerifyOps':
        require(summary.get('verified_total_cents')==30 and summary.get('duplicate_deliveries')==1,'exact-cents-and-duplicates')
    elif PROJECT=='RelayOps':
        require(summary.get('resolvable')==1 and summary.get('proposed_hold_cents')==250,'workflow-plan-and-amount')
        require(not summary.get('approved_export') and not result['results'][0]['receipts'],'approval-before-effects')
    else:
        require(summary.get('overall_value')=='0.30' and summary.get('included_rows')==2,'exact-decimals-and-filter')


class SameOrigin(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require(urlsplit(req.full_url).netloc==urlsplit(newurl).netloc,'unexpected-redirect')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


class Probe:
    def __init__(self, base):
        parts=urlsplit(base)
        require(parts.scheme=='https' and parts.hostname.endswith('.vercel.app') or parts.scheme=='http' and parts.hostname in ('127.0.0.1','localhost'),'allowed-probe-origin')
        require(not parts.username and not parts.password and parts.path in ('','/') and not parts.query and not parts.fragment,'plain-probe-origin')
        self.base=base.rstrip('/');self.started=time.monotonic();self.opener=build_opener(SameOrigin(),HTTPCookieProcessor(CookieJar()));self.checks=[];self.last_step='initialization'

    def request(self,path,body=None,expected=200,headers=None):
        self.last_step=path
        remaining=90-(time.monotonic()-self.started);require(remaining>0,'probe-total-deadline')
        encoded=None if body is None else json.dumps(body).encode()
        request=Request(self.base+path,data=encoded,headers={'User-Agent':'PublicSyntheticHealth/1.0',**({'Content-Type':'application/json'} if body is not None else {}),**(headers or {})})
        started=time.monotonic()
        try:response=self.opener.open(request,timeout=min(12,remaining))
        except HTTPError as error:response=error
        with response:
            status=response.code;content=response.read(2_000_001);metadata={k.lower():v for k,v in response.headers.items()}
        require(status==expected,path+'-status');require(len(content)<=2_000_000,path+'-response-bound')
        self.checks.append({'route':path,'status':status,'latency_ms':round((time.monotonic()-started)*1000)})
        return content,metadata

    def json(self,path,body=None,expected=200,headers=None):
        content,_=self.request(path,body,expected,headers)
        return json.loads(content)

    def run(self):
        home,_=self.request('/');require(PROJECT.lower().encode() in home.lower(),'home-brand')
        # Check the actually referenced application script, not only the HTML shell.
        script=re.search(r'<script[^>]+src="([^"\s]+)"',home.decode())
        require(script is not None,'home-script-reference')
        asset=urlsplit(urljoin(self.base+'/',script.group(1)))
        require(asset.netloc==urlsplit(self.base).netloc,'same-origin-asset')
        js,_=self.request(asset.path);require(len(js)>100,'application-script')
        caps=self.json('/api/uploads/capabilities')
        require(caps.get('project')==PROJECT and caps.get('live_ai') is False and set(caps.get('formats',[]))=={'csv','tsv','xlsx','json','jsonl'},'honest-capabilities')
        source,mapping,options=fixture();rows=list(csv.reader(io.StringIO(source)));objects=[dict(zip(rows[0],row)) for row in rows[1:]]
        tsv=io.StringIO();csv.writer(tsv,delimiter='\t').writerows(rows)
        formats={'csv':source.encode(),'tsv':tsv.getvalue().encode(),'xlsx':workbook(rows),'json':json.dumps(objects).encode(),'jsonl':'\n'.join(json.dumps(row) for row in objects).encode()}
        final=None;upload=None
        for extension,data in formats.items():
            imported=self.json('/api/uploads/import',{'filename':'synthetic-health.'+extension,'content_base64':base64.b64encode(data).decode()})
            require(imported.get('needs_sheet') is not True and isinstance(imported.get('csv'),str),'normalized-import-'+extension)
            upload={'csv':imported['csv'],'mapping':mapping,'options':options}
            body,headers=self.request('/api/uploads/analyze-stream',upload)
            require('text/event-stream' in headers.get('content-type',''),'sse-content-type')
            final=terminal_result(body.decode());validate_result(final)
            require(final.get('source_sha256')==hashlib.sha256(upload['csv'].encode()).hexdigest(),'source-bound-result')
        require(self.json('/api/uploads/check-report',{'report':final}).get('verified') is True,'authentic-result')
        changed=copy.deepcopy(final);changed['summary']['synthetic_tamper']=True
        require(self.json('/api/uploads/check-report',{'report':changed}).get('verified') is False,'tamper-refusal')
        self.json('/api/uploads/import',{'filename':'bad.json','content_base64':base64.b64encode(b'[{"id":1,"id":2}]').decode()},expected=422)
        self.request('/api/uploads/analyze',upload,expected=403,headers={'Origin':'https://cross-origin.invalid'})
        if PROJECT=='RelayOps':
            require(isinstance(final.get('review'),str),'source-bound-approval-token')
            approved=self.json('/api/uploads/approve',{**upload,'review':final['review']})
            require(approved['summary']['approved_export'] is True and len(approved['results'][0]['receipts'])==4,'approved-sandbox-receipts')
        video='/recordings/querypilot.webm' if PROJECT=='QueryPilot' else '/demo-assets/walkthrough.webm'
        partial,_=self.request(video,expected=206,headers={'Range':'bytes=0-1023'})
        require(len(partial)==1024,'recording-range')
        return {'passed':True,'project':PROJECT,'origin':self.base,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'synthetic_only':True,'live_model_calls':0,'external_business_writes':0,'formats_verified':list(formats),'checks':self.checks,'elapsed_ms':round((time.monotonic()-self.started)*1000)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base-url',default=CANONICAL);parser.add_argument('--output',type=Path,default=Path('artifacts/generated/public-health.json'));args=parser.parse_args()
    probe=None
    try:probe=Probe(args.base_url);report=probe.run()
    except Exception as error:
        report={'passed':False,'project':PROJECT,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'failed_step':getattr(probe,'last_step','initialization'),'error_kind':type(error).__name__,'synthetic_only':True,'live_model_calls':0,'checks':getattr(probe,'checks',[])}
        if isinstance(error,ProbeFailed):report['failure_code']=str(error)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));raise SystemExit(0 if report['passed'] else 1)

if __name__=='__main__':main()
