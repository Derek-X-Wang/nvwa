from pathlib import Path
import copy,hashlib,importlib.util,json,sys,time
stage=Path(__file__).resolve().parent;sys.path.insert(0,str(stage));import checker_fixture as fixtures,source_binding as guard
root=fixtures.ROOT;exp=fixtures.EXP;sys.path.insert(0,str(exp));import check_captures as original
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--legacy-capture-root',type=Path,required=True);parser.add_argument('--actual68',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--historical-r1-checker',type=Path,default=root/'.work/eyes73/source-r1/check_captures.py');args=parser.parse_args();actual=args.actual68;legacy=args.legacy_capture_root
source=json.loads(actual.read_bytes())['frame']['full_base'];topology={p['name']:{'render_vertices':len(p['source_ids']),'indices':len(p['indices']),'source_ids_sha256':fixtures.sha(p['source_ids']),'indices_sha256':fixtures.sha(p['indices'])} for p in source['parts']}
guard.require(topology==json.loads((exp/'BODY-CORRESPONDENCE.json').read_text())['parts'],'historical source topology fixture differs')
t=time.monotonic();envelopes=fixtures.fixtures(legacy,actual);print('fixture built',len(envelopes),time.monotonic()-t,flush=True)
historical=args.historical_r1_checker
old_spec=importlib.util.spec_from_file_location('checker73_R1',historical);old=importlib.util.module_from_spec(old_spec);old_spec.loader.exec_module(old)
old_validate=old.validate
def validate(e):return integrated_validate(e)
integrated_validate=original.validate
original.validate=validate
print('matrix green',original.check(envelopes),time.monotonic()-t,flush=True)
# Build small copies: immutable bulk arrays are shared; each mutation changes only its explicit target.
mutations=[]
def reject(name,transform):
 base=envelopes[0];e={k:v.copy() for k,v in base.items()};e['frame']=base['frame'].copy();e['report']=base['report'].copy();transform(e)
 try:validate(e)
 except (ValueError,KeyError,TypeError) as error:mutations.append({'mutation':name,'result':'rejected','reason':str(error)});return
 raise ValueError('mutation escaped: '+name)
reject('missing_witness',lambda e:e['frame'].update(candidate={k:v for k,v in e['frame']['candidate'].items() if k!='pre_visibility_publication'}))
for key in ['variant','positions_sha256','normals_sha256','placement','camera','work_sha256','generation']:
 def mutate(e,key=key):
  c=e['frame']['candidate'].copy();c['pre_visibility_publication']=c['pre_visibility_publication'].copy();c['pre_visibility_publication'][key]=None;e['frame']['candidate']=c
 reject('witness_'+key,mutate)
for key in ['published_positions_sha256','published_normals_sha256']:
 def mutate(e,key=key):
  c=e['frame']['candidate'].copy();c[key]='wrong';c['pre_visibility_publication']=c['pre_visibility_publication'].copy();c['pre_visibility_publication'][key.replace('published_','')]='wrong';e['frame']['candidate']=c
 reject(key,mutate)
reject('compact_bone_digest',lambda e:(e['frame'].update(base={**e['frame']['base'],'bones_sha256':'wrong'}),e['report'].update(base=e['frame']['base'])))
reject('work_hash',lambda e:(e['frame'].update(work_sha256='bad'),e['report'].update(work_sha256='bad')))
reject('cross_record_identity',lambda e:e['report'].update(captured_identity={**e['frame']['identity'],'seconds':2}))
reject('wrong_recipe_parameters',lambda e:e['frame'].update(full_base={**e['frame']['full_base'],'parameters':{'torso_length':1,'jaw_drop':1}}))
reject('wrong_source_position',lambda e:e['frame'].update(full_base={**e['frame']['full_base'],'sample':{**e['frame']['full_base']['sample'],'position_seconds':2}}))
reject('wrong_revision',lambda e:e['frame'].update(full_base={**e['frame']['full_base'],'revision':999}))
reject('wrong_backend',lambda e:e['frame'].update(full_base={**e['frame']['full_base'],'backend':{}}))
reject('wrong_pose',lambda e:e['frame'].update(full_base={**e['frame']['full_base'],'diagnostic_pose':'bad'}))
# Complete-matrix controls use coherent labels on the original source0 short cage.
wrong=[]
for good in envelopes:
 f=good['frame'];case=original.classify_work(good['report']['work_json']);seconds=f['full_base']['sample']['source_seconds'];short=next(x for x in envelopes if original.classify_work(x['report']['work_json'])=='short-front' and x['frame']['full_base']['sample']['source_seconds']==seconds and x['frame']['candidate']['variant']==f['candidate']['variant']);bad={'report':good['report'].copy(),'frame':f.copy()};bad['frame']['full_base']=short['frame']['full_base'];bad['frame']['base']=short['frame']['base'];bad['report']['base']=bad['frame']['base'];wrong.append(bad)
try:original.check(wrong)
except (ValueError,KeyError,TypeError) as error:mutations.append({'mutation':'complete16_reused_short_cage','result':'rejected','reason':str(error)})
else:raise ValueError('complete wrong Work matrix escaped')
# Coherently wrong full body buffer association (same count/topology) must reject.
def buffer_mutate(e):
 buffers=e['frame']['buffers'].copy();b=buffers[0].copy();p=b['positions'].copy();p[0]=[v+.01 for v in p[0]];b['positions']=p;buffers[0]=b;e['frame']['buffers']=buffers
reject('actual_body_upload_differs_from_full_base',buffer_mutate)
for name,kw in [('coherent_complete16_wrong_Work_cage',{'force_short_cage':True}),('coherent_complete16_source2_geometry_labeled_source0',{'force_peak_at_zero':True})]:
 bad=fixtures.fixtures(legacy,actual,**kw)
 baseline=old.check(bad)
 try:original.check(bad)
 except (ValueError,KeyError,TypeError) as error:mutations.append({'mutation':name,'R1_result':'accepted with zero eye replay error','R1_baseline':baseline,'R2_result':'rejected','reason':str(error)})
 else:raise ValueError('coherent full-matrix mutation escaped: '+name)
 del bad
args.out.write_text(json.dumps({'positive':'complete16 synthetic matrix accepted','negative':mutations,'seconds':time.monotonic()-t,'scope':'synthetic checker controls only; no runtime/GPU quality claim'},indent=2)+'\n');print('negative controls',len(mutations),'seconds',time.monotonic()-t,flush=True)
