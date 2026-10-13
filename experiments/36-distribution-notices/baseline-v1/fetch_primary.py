#!/usr/bin/env python3
"""Bounded public, exact-commit license retrieval; never authenticate or install."""
import argparse, hashlib, json, urllib.request, urllib.error
from pathlib import Path

parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);a=parser.parse_args();a.output.mkdir(parents=True,exist_ok=False)
requests=[];entries=[];cap=256*1024

def fetch(url,name):
    if len(requests)>=12:raise RuntimeError('12-request bound')
    record={'url':url,'name':name,'timeout_seconds':10,'limit_bytes':cap};requests.append(record)
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Nvwa-bounded-license-audit','Accept':'application/vnd.github+json' if 'api.github.com' in url else 'text/plain'}),timeout=10) as response:
            data=response.read(cap+1);record['http_status']=response.status
            if len(data)>cap:raise ValueError('response exceeds bound')
            record['sha256']=hashlib.sha256(data).hexdigest();record['bytes']=len(data)
            (a.output/name).write_bytes(data);return data
    except Exception as e:
        record['error']=str(e)
        if isinstance(e,urllib.error.HTTPError):
            data=e.read(cap+1)[:cap];record['http_status']=e.code;record['response_sha256']=hashlib.sha256(data).hexdigest();(a.output/(name+'.error-body')).write_bytes(data)
        return None
    finally:(a.output/'requests.json').write_text(json.dumps(requests,indent=2)+'\n')

def license(repo,commit,path):
    name=repo.replace('/','__')+'__'+commit+'__'+path.replace('/','__');url='https://raw.githubusercontent.com/'+repo+'/'+commit+'/'+path
    data=fetch(url,name)
    if data is not None:entries.append({'repository':'https://github.com/'+repo,'commit':commit,'path':path,'file':str((a.output/name).resolve()),'sha256':hashlib.sha256(data).hexdigest(),'url':url,'kind':'pinned-public-primary-exact-bytes'})

license('emilk/egui','49682f8baa058bf49e011035cfbd6e825f88a5ef','LICENSE-MIT')
license('emilk/egui','49682f8baa058bf49e011035cfbd6e825f88a5ef','LICENSE-APACHE')
for commit in ['a55d3e1a18bb9ef0e4bccc9083fb13c3e0ad8969','c88605b96d04431f9c3c792464a0f2f253480e94','1bbcf100942bac96c2c3a4a91cb67b0b20201a24']:
    for name in ['LICENSE-MIT','LICENSE-APACHE']:license('AccessKit/accesskit',commit,name)
repo='madsmtm/objc2';commit='7b1abfd750a2cacaea71d6a56ecfb83cb7de560b'
data=fetch('https://api.github.com/repos/'+repo+'/git/trees/'+commit,'objc2-root-tree.json')
if data is not None:
    paths=[p['path'] for p in json.loads(data)['tree'] if p['type']=='blob' and p['path'].upper().startswith(('LICENSE','COPYING','NOTICE'))]
    for path in paths[:3]:license(repo,commit,path)
(a.output/'supplements.json').write_text(json.dumps(entries,indent=2)+'\n')
print(json.dumps({'requests':len(requests),'successful_license_files':len(entries),'failures':sum('error' in r for r in requests)}))
