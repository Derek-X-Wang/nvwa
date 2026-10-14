#!/usr/bin/env python3
"""Check frozen candidate integrity and refuse unsupported completeness claims."""
import argparse, json, sys
from pathlib import Path
from collect import TARGETS, EXPECTED, digest, parse_tree, expression_status
from cohort import semantic_errors, frozen, TOOLING_VERSION, COHORT_SHA256


def check(pack,require_complete=False,source_root=None):
    pack=pack.resolve(); errors=[]
    def need(condition,message):
        if not condition:errors.append(message)
    try:
        m=json.loads((pack/'manifest.json').read_text())
        need(m['schema']==1,'unsupported schema')
        need(set(m['targets'])==set(TARGETS.values()),'unsupported or missing target')
        for name,expected in EXPECTED.items():need(m['identity'][name]['sha256']==expected,'frozen production identity changed: '+name)
        need(digest(pack/'inputs/Cargo.lock')==EXPECTED['Cargo.lock'],'lock cohort hash mismatch')
        need(m['redistribution_completeness']=='BLOCKED','unsupported completeness claim')
        need(m['legal_approval']=='NOT-RUN','unsupported legal-approval claim')
        for name,entry in frozen()['files'].items():
            p=pack/name
            need(not Path(name).is_absolute() and '..' not in Path(name).parts,'unsafe pack path: '+name)
            need(p.is_file() and not p.is_symlink(),'missing required file: '+name)
            if p.is_file():
                need(digest(p)==entry['sha256'],'altered required file: '+name)
                need(p.stat().st_size==entry['bytes'],'byte count mismatch: '+name)
        anchor=json.loads((pack/'inputs/package-metadata.json').read_text())
        need(set(anchor)==set(m['packages']),'package coverage differs from metadata anchor')
        for key,p in m['packages'].items():
            source=anchor[key]
            for field in ['package_id','license_expression','authors','notice_files','license_text_candidate_files','notice_documents','excluded_source_documents']:need(p[field]==source[field],'package metadata altered: '+key+' '+field)
            try:need(p['expression_status']==expression_status(p['license_expression']),'expression status differs: '+key)
            except ValueError as e:errors.append(str(e))
            for path in [p['manifest'],*p['notice_files']]:need(path in m['files'],'required package file omitted: '+path)
        union=set()
        for triple,t in m['targets'].items():
            label=t['label'];need(TARGETS.get(label)==triple,'unsupported target mapping')
            tree=parse_tree((pack/('inputs/'+label+'-tree.txt')).read_text());runtime=parse_tree((pack/('inputs/'+label+'-runtime-tree.txt')).read_text())
            need(t['normal_build_packages']==sorted(tree),'target closure changed: '+triple)
            need(t['features_by_package']==tree,'target features changed: '+triple)
            need(t['normal_without_proc_macro_packages']==sorted(runtime),'normal closure changed: '+triple)
            need(set(runtime)<=set(tree),'normal closure outside build-input closure: '+triple)
            need(t['root']=='nvwa-studio@0.1.0','unsupported build root')
            need('nvwa-cli@0.1.0' not in tree,'CLI accidentally included in Studio pack')
            if label=='native':
                actual=parse_tree((pack/'inputs/native-production-command-tree.txt').read_text())
                need(all(actual.get(k)==v for k,v in tree.items()),'actual native build root feature cohort differs')
                need(t['production_command_feature_comparison']['selected_studio_feature_differences']==[],'unresolved native feature comparison')
                need(t['production_command_feature_comparison']['extra_build_root_packages']==sorted(set(actual)-set(tree)),'native extra root inventory changed')
            union.update(tree)
        need(union==set(m['packages']),'package union differs from target closure')
        for asset in m['assets']:
            for p in asset['notice_files']:need(p in m['files'],'missing asset notice reference: '+p)
        for font in m['embedded_default_font_candidates']:
            for p in font['notice_files']:need(p in m['files'],'missing embedded-font notice reference: '+p)
        missing={key for key,p in m['packages'].items() if not p['license_text_candidate_files']};unknown={key for key,p in m['packages'].items() if p['license_expression'] is None}
        need(missing=={g['package'] for g in m['gaps'] if g['kind']=='missing-license-text'},'missing-text gaps not preserved')
        need(unknown=={g['package'] for g in m['gaps'] if g['kind']=='first-party-owner-license-decision'},'unknown-license gaps not preserved')
        need(all(x['equal'] and x['current_sha256']==x['retained_sha256'] for x in m['source_comparisons']),'source cohort mismatch')
        need(bool(m['gaps']),'known completeness gaps disappeared')
        errors.extend(semantic_errors(pack,m,source_root))
        if require_complete:errors.append('redistribution completeness BLOCKED: '+str(len(m['gaps']))+' explicit gaps')
        result={'status':'FAIL' if errors else 'VERIFIED-INTEGRITY/PARTIAL-COVERAGE','errors':errors,'package_count':len(m['packages']),'file_count':len(m['files']),'missing_text_packages':len(missing),'unknown_license_packages':len(unknown),'target_counts':{k:len(v['normal_build_packages']) for k,v in m['targets'].items()},'completeness':m['redistribution_completeness'],'manifest_sha256':digest(pack/'manifest.json'),'tooling_version':TOOLING_VERSION,'independent_cohort_anchor_sha256':COHORT_SHA256,'live_source_check':'VERIFIED' if source_root is not None and not errors else 'NOT-RUN' if source_root is None else 'FAIL'}
    except (KeyError,ValueError,OSError,TypeError,StopIteration) as e:result={'status':'FAIL','errors':errors+[str(e)]}
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pack',type=Path);p.add_argument('--require-complete',action='store_true');p.add_argument('--source-root',type=Path);a=p.parse_args();result=check(a.pack,a.require_complete,a.source_root.resolve() if a.source_root else None);print(json.dumps(result,indent=2));sys.exit(1 if result['status']=='FAIL' else 0)
