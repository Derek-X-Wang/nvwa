"""Bounded unauthenticated HTTP transport. Importing this module performs no I/O.

The immutable request log, original bodies and Git object joins are the evidence.
Running another acquisition requires a new output directory and task authorization.
"""
import datetime,hashlib,json,urllib.request,urllib.error
from pathlib import Path

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None

class Transport:
    def __init__(self,output,requests):
        self.output=Path(output);self.requests=requests
        self.opener=urllib.request.build_opener(NoRedirect)
    def fetch(self,url,name):
        if len(self.requests)>=20:raise ValueError('20 total HTTP requests exhausted')
        if not url.startswith(('https://api.github.com/repos/','https://raw.githubusercontent.com/')):raise ValueError('unsupported primary host')
        if Path(name).name!=name:raise ValueError('unsafe response filename')
        now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
        sha=lambda b:hashlib.sha256(b).hexdigest()
        record={'ordinal':len(self.requests)+1,'url':url,'started_utc':now(),'timeout_seconds':10,'limit_bytes':262144,'authentication':'none','redirect_policy':'no follow','body_path':'http/'+name};self.requests.append(record)
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'Nvwa-bounded-three-package-notice-source','Accept':'text/plain'})
            with self.opener.open(request,timeout=10) as response:
                record.update(status=response.status,headers=dict(response.headers.items()),final_url=response.url)
                data=response.read(262145)
                if len(data)>262144:
                    prefix=data[:262144];(self.output/('http/'+name+'.bounded-prefix')).write_bytes(prefix);record['bounded_prefix_sha256']=sha(prefix);raise ValueError('response exceeds256KiB; stop package')
                (self.output/record['body_path']).write_bytes(data);record.update(sha256=sha(data),bytes=len(data));return data
        except Exception as error:
            record['error']=str(error)
            if isinstance(error,urllib.error.HTTPError):
                data=error.read(262145);prefix=data[:262144];record.update(status=error.code,headers=dict(error.headers.items()),error_body_path='http/'+name+'.error-body',error_body_sha256=sha(prefix),error_body_bytes=len(prefix),error_body_truncated=len(data)>262144);(self.output/record['error_body_path']).write_bytes(prefix)
            return None
        finally:
            record['completed_utc']=now();(self.output/'requests.json').write_text(json.dumps(self.requests,indent=2)+'\n')
