#!/usr/bin/env python3
"""Actual retained-byte mutations through the production verifier; no HTTP."""
import argparse,copy,hashlib,json,shutil,subprocess,sys
from pathlib import Path,PurePosixPath
from protocol import git_object
p=argparse.ArgumentParser();p.add_argument('--scratch',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();a.scratch.mkdir(parents=True,exist_ok=False);a.evidence.mkdir(parents=True,exist_ok=False);packet=Path(__file__).resolve().parent;rows=[]

def run(name,where,red=False,contains=None):
 argv=[sys.executable,'-B',str(packet/'verify.py'),str(where)];r=subprocess.run(argv,capture_output=True);(a.evidence/(name+'.stdout.json')).write_bytes(r.stdout);(a.evidence/(name+'.stderr.log')).write_bytes(r.stderr);d=json.loads(r.stdout);ok=r.returncode==(1 if red else 0) and (contains is None or contains in r.stdout.decode());rows.append({'name':name,'argv':argv,'exit_code':r.returncode,'expected':'red' if red else 'green','expected_error':contains,'passed':ok,'stdout_sha256':hashlib.sha256(r.stdout).hexdigest()});assert ok,(name,d,r.stderr)

def create(name):
 dest=a.scratch/name;dest.mkdir()
 for directory in ['inputs','http']:shutil.copytree(packet/directory,dest/directory)
 for file in ['capture.json','requests.json']:shutil.copyfile(packet/file,dest/file)
 return dest,json.loads((dest/'capture.json').read_text())

def encode(data):return (json.dumps(data,indent=2,sort_keys=True)+'\n').encode()
def response(where,c,ordinal,data,url=None):
 r=c['requests'][ordinal-1];(where/r['body_path']).write_bytes(data);r.update(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
 if url is not None:r['url']=url;r['final_url']=url

def synchronize(where,c):
 (where/'requests.json').write_bytes(encode(c['requests']))
 for name,record in c['inventory'].items():
  if (where/name).is_file():
   data=(where/name).read_bytes();record.update(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
 (where/'capture.json').write_bytes(encode(c))

def replace_svg_with(where,c,source_path,body):
 p=c['packages'][1];f=p['captured_files'][0];url='https://raw.githubusercontent.com/nical/rust_debug/'+p['commit']+'/'+source_path;response(where,c,f['request_ordinal'],body,url);blob=git_object('blob',body);f.update(source_path=source_path,sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),git_blob_sha1=blob,tree_blob_sha1=blob);f['document_role'].update(sha256=f['sha256'],bytes=len(body),full_license_text_candidate=True,kind='full-license-text-candidate')

cases=[('actual-document-byte-tamper','actual legal Git blob join mismatch'),('mirrored-commit-substitution','pinned package/VCS/declaration mismatch'),('mirrored-source-path-substitution','source request URL/commit/path mismatch'),('actual-code-promoted-as-terms','content-derived document role mismatch'),('actual-declaration-promoted-as-terms','content-derived document role mismatch'),('omit-no-legal-root-finding','required observed absence/content scope omitted'),('approve-empty-hexf-coverage','observed absence/notice/terms status differs'),('backfill-absent-VCS-path','absent VCS path backfilled'),('ambiguous-original-manifest-tree','original manifest blob path absent/ambiguous'),('flatten-raw-slash-expression','pinned package/VCS/declaration mismatch'),('promote-expression-coverage','package coverage/approval unknowns changed'),('omit-legal-body',None),('omit-captured-legal-record','captured legal sources omitted/added'),('alter-actual-Git-tree','reconstructed Git tree mismatch'),('rewrite-baseline23','independent baseline anchor mismatch'),('change-sourceID','pinned package/VCS/declaration mismatch')]
run('baseline-green',packet)
for name,error in cases:
 where,c=create(name)
 if name=='actual-document-byte-tamper':
  f=c['packages'][0]['captured_files'][1];data=(where/f['body_path']).read_bytes()+b'\nCONTROL tamper\n';response(where,c,f['request_ordinal'],data);f.update(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data));f['document_role'].update(sha256=f['sha256'],bytes=len(data))
 elif name=='mirrored-commit-substitution':
  p=c['packages'][0];p['commit']='0'*40;vpath=p['local_inputs']['.cargo_vcs_info.json']['path'];v=json.loads((where/vpath).read_text());v['git']['sha1']=p['commit'];(where/vpath).write_bytes(encode(v));p['local_inputs']['.cargo_vcs_info.json'].update(sha256=hashlib.sha256((where/vpath).read_bytes()).hexdigest(),bytes=(where/vpath).stat().st_size)
  r=c['requests'][p['commit_request']-1];d=json.loads((where/r['body_path']).read_text());d['sha']=p['commit'];response(where,c,p['commit_request'],encode(d),'https://api.github.com/repos/aclysma/profiling/git/commits/'+p['commit'])
 elif name=='mirrored-source-path-substitution':
  f=c['packages'][1]['captured_files'][0];f['source_path']='WRONG-LICENSE';r=c['requests'][f['request_ordinal']-1];response(where,c,f['request_ordinal'],(where/r['body_path']).read_bytes(),'https://raw.githubusercontent.com/nical/rust_debug/'+'0'*40+'/WRONG-LICENSE')
 elif name=='actual-code-promoted-as-terms':replace_svg_with(where,c,'svg_fmt/src/lib.rs',(where/c['control_source_fixture']['path']).read_bytes())
 elif name=='actual-declaration-promoted-as-terms':replace_svg_with(where,c,'svg_fmt/Cargo.toml',(where/'inputs/svg_fmt@0.4.5/Cargo.toml.orig').read_bytes())
 elif name=='omit-no-legal-root-finding':c['packages'][2]['absence_scope']=''
 elif name=='approve-empty-hexf-coverage':c['packages'][2]['state']='original terms candidates captured'
 elif name=='backfill-absent-VCS-path':
  p=c['packages'][2];p['vcs_path_in_vcs']='parse';p['vcs_path_state']='declared by published .cargo_vcs_info.json';path=where/p['local_inputs']['.cargo_vcs_info.json']['path'];v=json.loads(path.read_text());v['path_in_vcs']='parse';path.write_bytes(encode(v));p['local_inputs']['.cargo_vcs_info.json'].update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
 elif name=='ambiguous-original-manifest-tree':
  p=c['packages'][2];r=c['requests'][p['tree_request']-1];t=json.loads((where/r['body_path']).read_text());node=next(n for n in t['tree'] if n['path']=='Cargo.toml');node['sha']=p['original_manifest_git_blob_sha1'];node['size']=p['local_inputs']['Cargo.toml.orig']['bytes'];children=[n for n in t['tree'] if str(PurePosixPath(n['path']).parent)=='.'];children.sort(key=lambda n:(n['path']+('/' if n['type']=='tree' else '')).encode());data=b''.join((format(int(n['mode'],8),'o')+' '+n['path']+'\0').encode()+bytes.fromhex(n['sha']) for n in children);t['sha']=git_object('tree',data);p['root_tree_sha1']=t['sha'];p['manifest_tree_matches']=['Cargo.toml','parse/Cargo.toml'];response(where,c,p['tree_request'],encode(t),'https://api.github.com/repos/lifthrasiir/hexf/git/trees/'+t['sha']+'?recursive=1');r=c['requests'][p['commit_request']-1];commit=json.loads((where/r['body_path']).read_text());commit['tree']['sha']=t['sha'];response(where,c,p['commit_request'],encode(commit))
 elif name=='flatten-raw-slash-expression':c['packages'][1]['expression']='MIT'
 elif name=='promote-expression-coverage':c['packages'][1]['coverage_unknowns']['every_declared_expression_branch']='COMPLETE';c['unknown_policy']['whole_expression_coverage']='COMPLETE'
 elif name=='omit-legal-body':(where/c['packages'][0]['captured_files'][0]['body_path']).unlink()
 elif name=='omit-captured-legal-record':c['packages'][0]['captured_files'].pop()
 elif name=='alter-actual-Git-tree':
  p=c['packages'][0];r=c['requests'][p['tree_request']-1];t=json.loads((where/r['body_path']).read_text());t['tree'][0]['sha']='0'*40;response(where,c,p['tree_request'],encode(t))
 elif name=='rewrite-baseline23':
  path=where/'inputs/baseline-v3-manifest.json';b=json.loads(path.read_text());b['gaps']=b['gaps'][1:];path.write_bytes(encode(b));c['baseline']['missing_text_packages']=22
 elif name=='change-sourceID':c['packages'][0]['package_id']='registry+WRONG#profiling@1.0.18'
 synchronize(where,c);run(name+'-red',where,True,error);shutil.rmtree(where);run(name+'-restored-green',packet)
report={'status':'VERIFIED','mutations':len(cases),'runs':len(rows),'all_passed':all(x['passed'] for x in rows),'controls':rows,'temporary_mutation_copies_removed':True};(a.evidence/'controls.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='controls'}))
