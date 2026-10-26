import hashlib,importlib.util,json,re,tomllib,unittest
from pathlib import Path
from frozen_context import source_contexts,select_context,historical_sources,RIG119_CONTEXT,RIG119_SUPPLEMENTS
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
  try:contexts=source_contexts(EXP,p.read_bytes(),inputs,include_current=True)
  except ValueError as error:self.fail(str(error))
  # Historical contexts keep their309 inputs. Current module/admission inputs
  # are explicit additions; partial or mixed current maps cannot select history.
  for name in RIG119_SUPPLEMENTS:
   path=ROOT/name
   if path.exists() or path.is_symlink():
    message=f'FROZEN-INPUTS.json supplemental entry {name}'
    path=ROOT
    for part in Path(name).parts:
     path=path/part;self.assertFalse(path.is_symlink(),message+' symlink rejected')
    self.assertTrue(path.is_file(),message+' file is required')
    actual[name]={'sha256':digest(path),'bytes':path.stat().st_size}
  try:context,selected=select_context(actual,contexts)
  except ValueError as error:self.fail(str(error))
  if context==RIG119_CONTEXT:
   self.assertEqual(len(selected),311,'current source set must include both explicit supplements')
  else:
   self.assertIn(context,['original-frozen309','character-stage-closeout-v1','hair79-short01-product-v1'])
   self.assertEqual(len(selected),309,'FROZEN-INPUTS.json complete source set required')
  for name,item in selected.items():
   message=f'FROZEN-INPUTS.json entry {name}'
   self.assertEqual(digest(ROOT/name),item['sha256'],message+' SHA256 mismatch')
   self.assertEqual((ROOT/name).stat().st_size,item['bytes'],message+' byte count mismatch')
if __name__=='__main__':unittest.main()
