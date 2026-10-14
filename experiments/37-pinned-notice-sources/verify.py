#!/usr/bin/env python3
"""Portable offline verification of one fixed, unapproved source capture.

Trust root: verifier code/pins plus SHA-pinned independent baseline36. No Cargo,
network, source cache or old experiment is read unless --live is explicit.
"""
import argparse,datetime,json,re,sys,tomllib
from pathlib import Path,PurePosixPath
from pins import BASELINE_SHA256,CAPTURE_SHA256,CLASSIFIER_SHA256,PACKAGE_KEYS
from protocol import sha256,git_object,check_tree,legal_ancestor_entries,safe_relative
from source_types import classify_document

PACKAGE_UNKNOWNS={k:'UNKNOWN' for k in ['entire_license_instrument','whole_package_scope','every_declared_expression_branch','copyright_and_subasset_completeness','final_binary_membership','licensing_applicability','distribution_permission','first_party_licensing']}
GLOBAL_UNKNOWNS={k:'UNKNOWN' for k in ['licensing_applicability','whole_expression_coverage','entire_instrument','final_binary_membership','distribution_permission','first_party_license']};GLOBAL_UNKNOWNS['review_acceptance']='PENDING separate fresh reviewer'

def verify(packet,live=False):
    packet=packet.resolve();errors=[];result={}
    def need(ok,message):
        if not ok:errors.append(message)
    def read(path):
        if not safe_relative(path):raise ValueError('unsafe data path')
        target=packet/path
        if any(p.is_symlink() for p in [target,*target.parents] if p!=packet.parent):raise ValueError('symlink data path')
        if not target.resolve().is_relative_to(packet):raise ValueError('escaped data path')
        return target.read_bytes()
    try:
        baseline_data=read('inputs/baseline-v3-manifest.json')
        if sha256(baseline_data)!=BASELINE_SHA256:raise ValueError('independent baseline anchor mismatch')
        baseline=json.loads(baseline_data);raw=read('capture.json');c=json.loads(raw)
        need(sha256(raw)==CAPTURE_SHA256,'frozen capture hash mismatch')
        need(sha256(Path(__file__).with_name('source_types.py').read_bytes())==CLASSIFIER_SHA256,'classifier source pin mismatch')
        need(c['schema']==1,'unsupported capture schema')
        need([p['package'] for p in c['packages']]==list(PACKAGE_KEYS),'unsupported package scope/order')
        need(len(baseline['gaps'])==47 and sum(g['kind']=='missing-license-text' for g in baseline['gaps'])==23,'baseline23/47 changed')
        need(c['baseline']=={'manifest_path':'inputs/baseline-v3-manifest.json','sha256':BASELINE_SHA256,'missing_text_packages':23,'gap_records':47,'action':'UNCHANGED; no gap closure or packet amendment','other_300_packages':'terms-bearing presence does not establish complete/applicable coverage'},'baseline unknown/unchanged boundary differs')
        need(c['unknown_policy']==GLOBAL_UNKNOWNS,'required global unknowns erased/promoted')
        actual={str(p.relative_to(packet)) for folder in ['inputs','http'] for p in (packet/folder).rglob('*') if p.is_file()}|{'requests.json'}
        need(set(c['inventory'])==actual,'data inventory omitted/added file')
        for path,entry in c['inventory'].items():
            data=read(path);need(sha256(data)==entry['sha256'] and len(data)==entry['bytes'],'indexed original bytes/hash changed: '+path)
        requests=json.loads(read('requests.json'));need(requests==c['requests'],'independent raw request log differs')
        need(0<len(requests)<=20 and [r['ordinal'] for r in requests]==list(range(1,len(requests)+1)),'request bound/order differs')
        for r in requests:
            need(r['timeout_seconds']==10 and r['limit_bytes']==262144 and r['authentication']=='none' and r['redirect_policy']=='no follow','request safety bounds changed')
            start=datetime.datetime.fromisoformat(r['started_utc']);end=datetime.datetime.fromisoformat(r['completed_utc']);need(start.utcoffset()==datetime.timedelta(0) and end.utcoffset()==datetime.timedelta(0) and 0<=(end-start).total_seconds()<=10,'observed request UTC/duration invalid')
            need(bool(r['headers']),'HTTP response headers missing')
            if 'error' in r:
                if 'error_body_path' in r:
                    body=read(r['error_body_path']);need(sha256(body)==r['error_body_sha256'] and len(body)==r['error_body_bytes'],'failed raw response differs')
            else:
                body=read(r['body_path']);need(sha256(body)==r['sha256'] and len(body)==r['bytes']<=262144,'raw response hash/length differs: '+r['body_path']);need(r['status']==200 and r['final_url']==r['url'],'unexpected HTTP status/final URL')
        def response(ordinal,url):
            r=requests[ordinal-1];need(r['url']==url,'source request URL/commit/path mismatch');need('error' not in r and r['status']==200,'required source response unavailable');return r,read(r['body_path'])
        used=[];summary=[]
        for p in c['packages']:
            key=p['package'];expected=baseline['packages'][key];vcs=expected['origin']['cargo_vcs_info'];commit=vcs['git']['sha1'];repo=expected['repository'];short=repo.removeprefix('https://github.com/')
            for field,value in [('repository',repo),('commit',commit),('package_id',expected['package_id']),('expression',expected['license_expression']),('vcs_path_in_vcs',vcs.get('path_in_vcs'))]:need(p[field]==value,'pinned package/VCS/declaration mismatch: '+key+' '+field)
            need(p['vcs_path_state']==('ABSENT/UNKNOWN' if 'path_in_vcs' not in vcs else 'declared by published .cargo_vcs_info.json'),'absent VCS path backfilled: '+key)
            need(p['coverage_unknowns']==PACKAGE_UNKNOWNS and p['review_acceptance']=='PENDING separate fresh review' and p['sealed_v3_gap_action']=='NONE; baseline unchanged','package coverage/approval unknowns changed: '+key)
            for name in ['Cargo.toml','Cargo.toml.orig','.cargo_vcs_info.json']:
                entry=p['local_inputs'][name];need(entry['path']=='inputs/'+key+'/'+name,'package input path differs');body=read(entry['path']);need(sha256(body)==entry['sha256'] and len(body)==entry['bytes'],'package input bytes differ')
            normalized=read('inputs/'+key+'/Cargo.toml');original=read('inputs/'+key+'/Cargo.toml.orig');published_vcs=json.loads(read('inputs/'+key+'/.cargo_vcs_info.json'))
            need(sha256(normalized)==expected['origin']['manifest_sha256'],'normalized manifest independent baseline hash mismatch')
            need(published_vcs==vcs,'published VCS metadata altered/backfilled')
            for body in [normalized,original]:
                package=tomllib.loads(body.decode())['package'];need((package['name'],package['version'],package['license'],package['repository'])==(expected['name'],expected['version'],expected['license_expression'],repo),'raw package/version/expression/repository differs')
            _,commit_body=response(p['commit_request'],'https://api.github.com/repos/'+short+'/git/commits/'+commit);git_commit=json.loads(commit_body);need(git_commit['sha']==commit,'actual commit record mismatch')
            _,tree_body=response(p['tree_request'],'https://api.github.com/repos/'+short+'/git/trees/'+git_commit['tree']['sha']+'?recursive=1');tree=json.loads(tree_body);need(tree['sha']==git_commit['tree']['sha']==p['root_tree_sha1'],'actual commit-to-tree join mismatch');nodes,tree_errors=check_tree(tree);errors.extend(tree_errors)
            blob=git_object('blob',original);hits=[path for path,n in nodes.items() if n['type']=='blob' and path.endswith('Cargo.toml') and n['sha']==blob]
            need(len(hits)==1,'original manifest blob path absent/ambiguous');need(p['manifest_tree_matches']==hits and p['original_manifest_git_blob_sha1']==blob,'resolved manifest blob/path claims differ')
            if len(hits)!=1:continue
            resolved=hits[0];directory=str(PurePosixPath(resolved).parent);directory='' if directory=='.' else directory
            need((p['resolved_manifest_path'],p['resolved_package_path'])==(resolved,directory),'actual package path resolution differs')
            if 'path_in_vcs' in vcs:need(directory==vcs['path_in_vcs'],'published/actual package path mismatch')
            legal=legal_ancestor_entries(nodes,directory);need(p['legal_entries']==legal,'actual legal-file tree inventory differs')
            need([f['source_path'] for f in p['captured_files']]==[n['path'] for n in legal],'captured legal sources omitted/added')
            expected_state='UNKNOWN no legal file at package/ancestor roots' if not legal else 'original terms candidates captured' if any(f['document_role']['full_license_text_candidate'] for f in p['captured_files']) else 'UNKNOWN notice-only source documents captured'
            need(p['state']==expected_state,'observed absence/notice/terms status differs')
            need(p['absence_scope']=='Tree filenames inspected recursively; legal files sought only at resolved package directory and ancestors. README/code/header bodies and other nested document scopes NOT-RUN.','required observed absence/content scope omitted')
            need(p['observed_scope']=='original legal files at resolved package directory and repository ancestors only; not whole-package coverage','source/coverage boundary differs')
            local_used=[p['commit_request'],p['tree_request']]
            for f in p['captured_files']:
                r,body=response(f['request_ordinal'],'https://raw.githubusercontent.com/'+short+'/'+commit+'/'+f['source_path']);node=nodes[f['source_path']]
                need(f['body_path']==r['body_path'] and sha256(body)==f['sha256'] and len(body)==f['bytes']==node['size'],'legal raw body/path/hash/length join mismatch')
                need(git_object('blob',body)==node['sha']==f['git_blob_sha1']==f['tree_blob_sha1'],'actual legal Git blob join mismatch')
                need(f['document_role']==classify_document(f['source_path'],body),'content-derived document role mismatch')
                lines=[line for line in body.decode(errors='replace').splitlines() if re.search(r'copyright|©',line,re.I)];need(f['copyright_lines']==lines,'original copyright lines differ')
                need(f['location_scope']=='repository/package ancestor source; applicability UNKNOWN','legal file applicability promoted');local_used.append(f['request_ordinal'])
            need(p['request_ordinals']==local_used,'per-package request join differs');used.extend(local_used);summary.append({'package':key,'observed_state':p['state'],'captured_files':len(p['captured_files']),'resolved_package_path':directory,'published_path_in_vcs':vcs.get('path_in_vcs'),'expression':p['expression']})
        need(sorted(used)==list(range(1,len(requests)+1)),'request ownership incomplete/duplicated')
        fixture=c['control_source_fixture'];svg=next(p for p in c['packages'] if p['package']=='svg_fmt@0.4.5');tree=json.loads(read(requests[svg['tree_request']-1]['body_path']));node=next(n for n in tree['tree'] if n['path']==fixture['original_source_path']);body=read(fixture['path']);need(git_object('blob',body)==node['sha']==fixture['git_blob_sha1'] and sha256(body)==fixture['sha256'],'actual control source tree/blob join differs')
        before=json.loads(read(c['source_snapshots']['before']));after=json.loads(read(c['source_snapshots']['after']));need(before==after and c['source_snapshots']['all_unchanged'] is True and len(before)==c['source_snapshots']['paths'],'actual before/after input snapshots differ')
        need(c['limits']=={'http_max_requests':20,'http_actual_requests':len(requests),'http_failed_requests':sum('error' in x for x in requests),'max_response_bytes':262144,'timeout_seconds':10,'automatic_retry':False,'redirect_following':False},'total acquisition bounds/results differ')
        if live:
            if errors:errors.append('live comparison refused for invalid offline evidence')
            else:
                for path,value in before.items():need(sha256(Path(path).read_bytes())==value,'explicit live source differs/unavailable: '+path)
        result={'status':'FAIL' if errors else 'VERIFIED-SOURCE-INTEGRITY/UNAPPROVED-COVERAGE','errors':errors,'capture_sha256':sha256(raw),'packages':summary,'actual_http_requests':len(requests),'captured_legal_files':sum(len(p['captured_files']) for p in c['packages']),'failed_requests':sum('error' in r for r in requests),'baseline_missing_unchanged':23,'baseline_gaps_unchanged':47,'live_comparison':'NOT-RUN' if not live else 'VERIFIED' if not errors else 'FAIL','review_acceptance':'PENDING','legal_distribution_approval':'NOT-RUN'}
    except (OSError,ValueError,KeyError,TypeError,IndexError,StopIteration) as error:result={'status':'FAIL','errors':errors+[str(error)]}
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('packet',type=Path,nargs='?',default=Path(__file__).resolve().parent);parser.add_argument('--live',action='store_true');a=parser.parse_args();result=verify(a.packet,a.live);print(json.dumps(result,indent=2));sys.exit(1 if result['status']=='FAIL' else 0)
