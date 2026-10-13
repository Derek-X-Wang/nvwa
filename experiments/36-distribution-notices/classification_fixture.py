#!/usr/bin/env python3
"""Real archived-source fixtures exercising the production classification seam."""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--module',type=Path);p.add_argument('--legacy',action='store_true');a=p.parse_args();root=Path(__file__).resolve().parent;old=root/'baseline-v2/sample-production-pack';m=json.loads((old/'manifest.json').read_text());failures=[];records=[]
negatives=['objc2-foundation@0.2.2/src/copying.rs','objc2-foundation@0.3.2/src/tests/copying.rs','aho-corasick@1.1.5/COPYING','craft-ui@0.1.0/NOTICE','craft-ui@0.1.0/ATTRIBUTION.md','linebender_resource_handle@0.1.1/AUTHORS','typenum@1.20.1/LICENSE','guillotiere@0.7.0/LICENSE-APACHE','shlex@2.0.1/LICENSE-APACHE','petgraph@0.8.3/assets/images/LICENSE.md','winit@0.30.13/docs/res/ATTRIBUTION.md','tiff@0.11.3/tests/COPYRIGHT']
positives=['craft-ui@0.1.0/LICENSE-MIT','craft-ui@0.1.0/LICENSE-APACHE','epaint_default_fonts@0.36.2/fonts/OFL.txt','blake3@1.8.7/LICENSE_CC0','unicode-ident@1.0.26/LICENSE-UNICODE','glam@0.32.1/ATTRIBUTION.md','adler2@2.0.1/LICENSE-0BSD','atomic-waker@1.1.2/LICENSE-THIRD-PARTY','futures-lite@2.6.1/LICENSE-THIRD-PARTY']
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
module=load(a.module or root/'notice_types.py','fixture_notice_types');legacy=load(root/'baseline-v2/collect.py','original_collector') if a.legacy else None
for name in negatives+positives:
 key=name.split('/')[0];relative=name.removeprefix(key+'/');path=old/'texts/packages'/name;data=path.read_bytes();expected=name in positives;info=m['packages'][key]
 if a.legacy:
  base=Path(info['origin']['manifest_path']).parent
  if key.startswith('craft-ui@'):base=base.parent.parent
  candidates=legacy.text_files(Path(info['origin']['manifest_path']).parent if not key.startswith('craft-ui@') else base)
  selected=(base/relative) in candidates
  observed=selected and 'texts/packages/'+name in info['license_text_candidate_files'];kind='filename-selected-as-candidate' if observed else 'not selected'
 else:
  included,excluded=module.select_documents([path]);classification=module.classify_document(path,data);observed=classification['full_license_text_candidate'];kind=classification['kind']
  # A trusted LICENSE filename must not promote source/metadata-only bytes.
  # Keep mutation failures structured rather than aborting before raw JSON.
  misleading_filename_promoted=not expected and module.classify_document('LICENSE.txt',data)['full_license_text_candidate']
 record={'misleading_license_filename_promoted':False if a.legacy else misleading_filename_promoted if not expected else False,'fixture':name,'sha256':hashlib.sha256(data).hexdigest(),'expected_full_text_candidate':expected,'actual_full_text_candidate':observed,'kind':kind};records.append(record)
 if observed!=expected or record['misleading_license_filename_promoted']:failures.append(record)
result={'status':'FAIL' if failures else 'VERIFIED','mode':'original production filename selector' if a.legacy else 'current production select_documents/classify_document','fixtures':records,'failures':failures};print(json.dumps(result,indent=2));sys.exit(1 if failures else 0)
