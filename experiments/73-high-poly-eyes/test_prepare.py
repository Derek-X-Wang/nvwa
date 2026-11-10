from frozen_context import has_reference_motion_inputs,_reference_motion_context,REFERENCE_MOTION_CONTEXT_ID,REFERENCE_MOTION_ADDITIONS,regular_file
from frozen_context import has_waist_inputs,_waist_context,waist_regular_file,WAIST_CONTEXT_ID,WAIST_ADDITIONS,check_waist_preexisting,_pre_waist_sources
from frozen_context import _combined_context,COMBINED_CONTEXT_ID
from frozen_context import has_leg_inputs,leg_source_context,LEG_CONTEXT_ID,has_upper_inputs,upper_source_context,UPPER_CONTEXT_ID
from frozen_context import has_hip_inputs,hip_source_context,HIP_CONTEXT_ID
from frozen_context import has_arm_inputs,arm_source_context,ARM_CONTEXT_ID
from frozen_context import has_cpu_inputs,_cpu_context,cpu_regular_file,CPU_CONTEXT_ID,CPU_ADDITIONS,check_cpu_preexisting,_pre_cpu_sources
import hashlib,importlib.util,json,re,tomllib,unittest
from pathlib import Path
from frozen_context import current_source_contexts as source_contexts,select_context,historical_sources,_running_source_context,RUNNING_ADDITIONS
from frozen_context import _motion_query_source_context,check_no_motion_query_additions,MOTION_QUERY_ADDITIONS,MOTION_QUERY_CONTEXT
ROOT=Path(__file__).resolve().parents[2];EXP=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('cpu_probe',EXP/'cpu_probe.py');probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class SourceContract(unittest.TestCase):
 def test_exact_original_subset_provenance_and_material(self):
  receipt=json.loads((EXP/'SOURCE.json').read_text());self.assertEqual(receipt['subset_bytes'],785436);self.assertEqual(receipt['network_bytes'],0)
  self.assertEqual(sum(i['bytes'] for i in receipt['files'].values()),785436)
  for path,item in receipt['files'].items():
   p=EXP/'source'/path;self.assertEqual(p.stat().st_size,item['bytes']);self.assertEqual(digest(p),item['sha256'])
   if p.suffix in ['.obj','.mhclo','.mhmat']:
    self.assertIn('released as CC0',p.read_text());self.assertIn('Data Collection AB',p.read_text())
  self.assertEqual(digest(EXP/'source/provenance/CC0-1.0.txt'),'f6089cba01cb570a24712b41ab8a586ccd3cc5ef53dc266ca50b95c288956d2c')
  self.assertEqual(digest(EXP/'source/provenance/pack.json'),'e86f1572432cfd062f372adddba4eb7c2e2e31280e96c29291a970320e0a5df0')
  self.assertEqual((EXP/'source/eyes/materials/brown_eye.png').read_bytes(),(ROOT/'assets/appearances/mpfb-b1-cc0-v1/eyes/materials/brown_eye.png').read_bytes())
  self.assertEqual((EXP/'source/eyes/materials/brown.mhmat').read_bytes(),(ROOT/'assets/appearances/mpfb-b1-cc0-v1/eyes/materials/brown.mhmat').read_bytes())
 def test_signed_mapping_and_once_only_conversion(self):
  obj,rows,scales=probe.source('b');self.assertEqual(obj['count'],1064);self.assertEqual(obj['uv_rows'],808);self.assertEqual(obj['faces'],1020);self.assertEqual(len(obj['pairs']),1076);self.assertEqual(len(obj['indices'])//3,2040)
  self.assertEqual(sum(c<0 for ids,coeff,offset in rows for c in coeff),102)
  self.assertEqual(scales[0],(5399,11998,1.6482*.1));self.assertEqual(rows[0][2],[-.00208*.1,-.00037*.1,.00667*.1])
  self.assertTrue(all(abs(sum(c)-1)<1e-12 for ids,c,o in rows))
  source_map=json.loads((EXP/'works/high-source-map.json').read_text());self.assertEqual(source_map['source_uv_pairs'],[list(p) for p in obj['pairs']]);self.assertEqual(source_map['uv_0'],obj['uv']);self.assertEqual(source_map['indices'],obj['indices'])
 def test_numeric_production_mirror_body_identity(self):
  record=json.loads((EXP/'NUMERIC-SOURCE.json').read_text());source=ROOT/record['source']
  frozen=(EXP/'FROZEN-INPUTS.json').read_bytes();contexts=source_contexts(EXP,frozen,json.loads(frozen))
  historical=historical_sources(EXP,contexts)['original-frozen309'][record['source']]
  self.assertEqual(hashlib.sha256(historical).hexdigest(),record['sha256'])
  a=historical.decode();b=(EXP/'src/geometry.rs').read_text();current=source.read_text()
  # Compare each numeric function byte-for-byte after removing only visibility and whitespace.
  for name in ['number','id','mapping','obj','cage','weights','transfer','fit','source_normals','skin']:
   def function(text):
    start=text.index('fn '+name+'(');brace=text.index('{',start);depth=1;i=brace+1
    while depth:
     if text[i]=='{':depth+=1
     elif text[i]=='}':depth-=1
     i+=1
    body=text[brace:i]
    if name=='obj':
     added=b[b.index('            \"vn\" => {'):b.index('            \"vt\" => {')]
     body=body.replace(added,'')
    return re.sub(r'\s+','',body)
   self.assertEqual(function(a),function(b),name)
   self.assertEqual(function(a),function(current),name+' current production')
 def test_all_fixed_works_preserve_recipe_pose_stage_lights_camera(self):
  appearance=json.loads((ROOT/'experiments/68-b1-eye-render-diagnosis/works/short-front.nvwa.json').read_text())['character']['appearance']
  for case in ['short-front','long-front','short-quarter','long-quarter']:
   source=json.loads((ROOT/f'experiments/65-b1-appearance-quality/evidence/inputs/{case}.nvwa.json').read_text());fixed=json.loads((EXP/f'works/{case}.nvwa.json').read_text())
   self.assertEqual(fixed['character'].pop('appearance'),appearance);source['character'].pop('appearance');self.assertEqual(fixed.pop('revision'),source.pop('revision')+1);self.assertEqual(fixed,source)
   camera=json.loads((EXP/f'works/reference-{case}.json').read_text());self.assertEqual(digest(ROOT/camera['source']),camera['source_sha256']);self.assertEqual(camera['camera'],json.loads((ROOT/camera['source']).read_text())['camera'])
 def test_standalone_locked_dependency_closure(self):
  manifest=tomllib.loads((EXP/'Cargo.toml').read_text());self.assertIn('workspace',manifest)
  old=tomllib.loads((ROOT/'experiments/68-b1-eye-render-diagnosis/Cargo.toml').read_text());extra=manifest['dependencies'].copy();extra.pop('nvwa-b1-adapter');self.assertEqual(extra,old['dependencies'])
  lock=tomllib.loads((EXP/'Cargo.lock').read_text());p=next(x for x in lock['package'] if x['name']==manifest['package']['name']);self.assertIn('nvwa-b1-adapter',p['dependencies'])
  packages=lambda x:{(p['name'],p['version'],p.get('checksum')) for p in x['package'] if not p['name'].startswith('b1-')}
  self.assertEqual(packages(lock),packages(tomllib.loads((ROOT/'experiments/68-b1-eye-render-diagnosis/Cargo.lock').read_text())))
 def test_frozen_source_inputs(self):
  p=EXP/'FROZEN-INPUTS.json'
  self.assertTrue(p.is_file(),'FROZEN-INPUTS.json is required')
  self.assertFalse(p.is_symlink(),'FROZEN-INPUTS.json symlink rejected')
  try:inputs=json.loads(p.read_text())
  except (json.JSONDecodeError,UnicodeDecodeError) as error:self.fail(f'FROZEN-INPUTS.json must be valid JSON: {error}')
  self.assertIsInstance(inputs,dict,'FROZEN-INPUTS.json must be an object')
  self.assertTrue(inputs,'FROZEN-INPUTS.json must not be empty')
  actual={}
  for name,item in inputs.items():
   message=f'FROZEN-INPUTS.json entry {name}'
   self.assertIsInstance(item,dict,message+' must be an object')
   self.assertEqual(type(item.get('bytes')),int,message+' needs integer bytes')
   self.assertGreaterEqual(item['bytes'],0,message+' needs nonnegative bytes')
   self.assertIsInstance(item.get('sha256'),str,message+' needs SHA256')
   self.assertRegex(item['sha256'],r'\A[0-9a-f]{64}\Z',message+' needs lowercase SHA256')
   path=ROOT
   for part in Path(name).parts:
    path=path/part;self.assertFalse(path.is_symlink(),message+' symlink rejected')
   self.assertTrue((ROOT/name).is_file(),message+' file is required')
   actual[name]={'sha256':digest(ROOT/name),'bytes':(ROOT/name).stat().st_size}
  try:
   contexts=source_contexts(EXP,p.read_bytes(),inputs)
   reference_motion=has_reference_motion_inputs(ROOT)
   waist=has_waist_inputs(ROOT)
   legs=has_leg_inputs(ROOT)
   upper=has_upper_inputs(ROOT)
   hip=has_hip_inputs(ROOT)
   arm=has_arm_inputs(ROOT)
   if reference_motion or waist or legs or upper or hip or arm or has_cpu_inputs(ROOT):
    previous=_motion_query_source_context(EXP,_running_source_context(EXP,inputs,contexts))
    cpu=_cpu_context(EXP,previous[1])
    if arm:
     product=arm_source_context(EXP,cpu)
    elif hip:
     product=hip_source_context(EXP,cpu)
    elif upper:
     product=upper_source_context(EXP,cpu)
    elif legs:
     product=leg_source_context(EXP,cpu)
    elif waist and reference_motion:
     product=_combined_context(EXP,cpu)
    elif waist:
     product=_waist_context(EXP,cpu[1])
    else:
     product=_reference_motion_context(EXP,cpu) if reference_motion else cpu
     check_waist_preexisting(ROOT,_pre_waist_sources(EXP,cpu[1]))
    actual={}
    reader=waist_regular_file if waist else regular_file if reference_motion else cpu_regular_file
    for name in product[1]:
     path=reader(ROOT,name)
     actual[name]={'bytes':path.stat().st_size,'sha256':digest(path)}
    if reference_motion and not waist:
     context,selected=product
     self.assertTrue(actual == selected,'FROZEN-INPUTS.json exact reference motion source required')
    else:
     context,selected=select_context(actual,[product])
   elif any(actual == expected for _,expected in contexts):
    self.assertFalse(any((ROOT/name).exists() or (ROOT/name).is_symlink() for name in RUNNING_ADDITIONS),'FROZEN-INPUTS.json running additions in historical context')
    check_no_motion_query_additions(ROOT)
    context,selected=select_context(actual,contexts)
   else:
    running=_running_source_context(EXP,inputs,contexts)
    for name in RUNNING_ADDITIONS:
     path=ROOT
     for part in Path(name).parts:
      path=path/part;self.assertFalse(path.is_symlink(),'FROZEN-INPUTS.json running input symlink rejected')
     self.assertTrue(path.is_file(),'FROZEN-INPUTS.json running input required: '+name)
     actual[name]={'bytes':path.stat().st_size,'sha256':digest(path)}
    if actual == running[1]:
     check_no_motion_query_additions(ROOT)
     context,selected=select_context(actual,[running])
    else:
     motion_query=_motion_query_source_context(EXP,running)
     for name in MOTION_QUERY_ADDITIONS:
      path=ROOT
      for part in Path(name).parts:
       path=path/part;self.assertFalse(path.is_symlink(),'FROZEN-INPUTS.json motion-query input symlink rejected: '+name)
      self.assertTrue(path.is_file(),'FROZEN-INPUTS.json motion-query input required: '+name)
      actual[name]={'bytes':path.stat().st_size,'sha256':digest(path)}
     context,selected=select_context(actual,[motion_query])
     check_cpu_preexisting(ROOT,_pre_cpu_sources(EXP,motion_query[1]))
  except ValueError as error:self.fail(str(error))
  if context == ARM_CONTEXT_ID:
   self.assertEqual(len(selected),812,'FROZEN-INPUTS.json arm complete source set required')
  elif context == HIP_CONTEXT_ID:
   self.assertEqual(len(selected),689,'FROZEN-INPUTS.json hip complete source set required')
  elif context == UPPER_CONTEXT_ID:
   self.assertEqual(len(selected),580,'FROZEN-INPUTS.json upper complete source set required')
  elif context == LEG_CONTEXT_ID:
   self.assertEqual(len(selected),482,'FROZEN-INPUTS.json leg complete source set required')
  elif context == COMBINED_CONTEXT_ID:
   self.assertEqual(set(selected),set(inputs)|set(RUNNING_ADDITIONS)|set(MOTION_QUERY_ADDITIONS)|set(CPU_ADDITIONS)|set(WAIST_ADDITIONS)|set(REFERENCE_MOTION_ADDITIONS),'FROZEN-INPUTS.json combined complete source paths required')
   self.assertEqual(len(selected),394,'FROZEN-INPUTS.json combined complete source set required')
  elif context == WAIST_CONTEXT_ID:
   self.assertEqual(set(selected),set(inputs)|set(RUNNING_ADDITIONS)|set(MOTION_QUERY_ADDITIONS)|set(CPU_ADDITIONS)|set(WAIST_ADDITIONS),'FROZEN-INPUTS.json WAIST complete source paths required')
  elif context == REFERENCE_MOTION_CONTEXT_ID:
   self.assertEqual(set(selected),set(inputs)|set(RUNNING_ADDITIONS)|set(MOTION_QUERY_ADDITIONS)|set(CPU_ADDITIONS)|set(REFERENCE_MOTION_ADDITIONS),'FROZEN-INPUTS.json reference motion complete source paths required')
   self.assertEqual(len(selected),327,'FROZEN-INPUTS.json reference motion complete source set required')
  elif context == CPU_CONTEXT_ID:
   self.assertEqual(set(selected),set(inputs)|set(RUNNING_ADDITIONS)|set(MOTION_QUERY_ADDITIONS)|set(CPU_ADDITIONS),'FROZEN-INPUTS.json CPU complete source paths required')
   self.assertEqual(len(selected),324,'FROZEN-INPUTS.json CPU complete source set required')
  elif context == MOTION_QUERY_CONTEXT:
   self.assertEqual(set(selected),set(inputs)|set(RUNNING_ADDITIONS)|set(MOTION_QUERY_ADDITIONS),'FROZEN-INPUTS.json motion-query complete source paths required')
   self.assertEqual(len(selected),318,'FROZEN-INPUTS.json motion-query complete source set required')
  elif context == 'b1-running-product-v1':
   self.assertEqual(set(selected),set(inputs)|set(RUNNING_ADDITIONS),'FROZEN-INPUTS.json running complete source paths required')
   self.assertEqual(len(selected),314,'FROZEN-INPUTS.json running complete source set required')
  else:
   if context == 'b1-lower-face-squareness-product-v1':
    self.assertEqual(set(selected),set(inputs),'FROZEN-INPUTS.json exact original source paths required')
   else:
    if context in ('b1-multisegment-product-v1','b1-cheek-fullness-product-v1'):self.assertEqual(set(selected),set(inputs),'FROZEN-INPUTS.json exact original source paths required')
    else:
     self.assertIn(context,['original-frozen309','character-stage-closeout-v1','hair79-short01-product-v1','hair79-selector-product-v1','b1-motion-authoring-product-v1'])
   self.assertEqual(len(selected),309,'FROZEN-INPUTS.json complete source set required')
  for name,item in selected.items():
   message=f'FROZEN-INPUTS.json entry {name}'
   self.assertEqual(digest(ROOT/name),item['sha256'],message+' SHA256 mismatch')
   self.assertEqual((ROOT/name).stat().st_size,item['bytes'],message+' byte count mismatch')
if __name__=='__main__':unittest.main()
