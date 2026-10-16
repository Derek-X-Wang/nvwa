#!/usr/bin/env python3
"""Compile audited source data. Never runs Blender or uses reference vertex outputs."""
import argparse,gzip,hashlib,json,math,pathlib
HERE=pathlib.Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def parse_proxy(path):
 scales={};vertices=[];inside=False
 for line in path.read_text().splitlines():
  words=line.split()
  if not words:inside=False;continue
  if words[0].startswith('#'):continue
  if words[0] in ['x_scale','y_scale','z_scale']:
   scales[words[0]]=(int(words[1]),int(words[2]),float(words[3]));inside=False
  elif words[0]=='verts':inside=True
  elif inside and words[0].isdigit():
   if len(words)==1:vertices.append({'vertices':[int(words[0])]*3,'weights':[1,0,0],'offset':[0,0,0]})
   elif len(words)==9:vertices.append({'vertices':list(map(int,words[:3])),'weights':list(map(float,words[3:6])),'offset':[float(words[6]),-float(words[8]),float(words[7])]})
   else:raise ValueError('unsupported MHCLO vertex record')
  else:inside=False
 assert len(scales)==3 and vertices,'selected proxy needs all three axis-scale records'
 order=[('x_scale',0),('z_scale',1),('y_scale',2)]
 return {'id':path.stem,'scales':[{'vertices':list(scales[key][:2]),'axis':axis,'denominator':scales[key][2]} for key,axis in order],'vertices':vertices}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--addon',type=pathlib.Path,required=True);ap.add_argument('--reference-dir',type=pathlib.Path,required=True);ap.add_argument('--manifest',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);ap.add_argument('--garment',type=pathlib.Path);ap.add_argument('--core-only',action='store_true');a=ap.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);addon=a.addon.resolve();ref=a.reference_dir.resolve();manifest=a.manifest.resolve();common=json.loads(manifest.read_text())
 if a.core_only:
  summary=common;transform=summary['raw_obj_to_reference'];baseline=summary['baseline'];allowed=None
 else:
  assert common['sample_class']=='makehuman-approved-sample' and common['approved'] is True
  transform=common['transforms']['raw_obj_to_reference'];baseline=common['baseline']
  assert ref==(manifest.parent/common['reference_directory']).resolve()
  assert a.garment and a.garment.resolve()==(manifest.parent/common['source_paths']['garment_mhclo']).resolve()
  allowed={(manifest.parent/row['path']).resolve():row for row in common['files']}
  for path,row in allowed.items():
   if row['role']!='reference':assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'] and row['license']=='CC0-1.0','frozen source identity mismatch'
 declared=[[.1,0,0,0],[0,0,-.1,0],[0,.1,0,0],[0,0,0,1]]
 assert transform==declared,'only measured root-declared MPFB .1 transform supported'
 assert baseline=='raw hm08, scale .1, no macros, no grounding, all helpers retained'
 source_files=[]
 audit_path=HERE.parent/'53-character-comparison/delivery/mpfb-extraction-receipt.json'
 audit=json.loads(audit_path.read_text());assert audit['status']=='audited-and-extracted'
 audited={(HERE.parent.parent/row['path']).resolve():row for row in audit['files']}
 def source(relative):
  p=addon/relative
  if allowed is not None:assert p in allowed and sha(p)==allowed[p]['sha256'],'source absent/different from common manifest'
  assert p in audited and sha(p)==audited[p]['sha256'],'source file differs from audited archive'
  source_files.append({'path':str(p),'sha256':sha(p)});return p
 def convert(v):return [sum(transform[i][j]*v[j] for j in range(3))+transform[i][3] for i in range(3)]
 base_rel='data/3dobjs/base.obj' if a.core_only else str((manifest.parent/common['source_paths']['basemesh']).resolve().relative_to(addon))
 basis=[convert(list(map(float,line.split()[1:4]))) for line in source(base_rel).read_text().splitlines() if line.startswith('v ')]
 assert len(basis)==19158
 selected=[('torso_length','torso/torso-scale-vert-decr.target.gz','torso/torso-scale-vert-incr.target.gz'),('jaw_drop','chin/chin-jaw-drop-decr.target.gz','chin/chin-jaw-drop-incr.target.gz')]
 if not a.core_only:
  selected=[]
  for ident,spec in common['parameters'].items():
   assert (spec['min'],spec['max'],spec['default'])==(-1,1,0),'unsupported signed parameter domain'
   selected.append((ident,*[str((manifest.parent/spec['targets'][branch]).resolve().relative_to(addon/'data/targets')) for branch in ['decr','incr']]))
 pairs=[]
 for parameter,neg,pos in selected:
  pair={'parameter_id':parameter}
  for branch,path in [('negative',neg),('positive',pos)]:
   deltas=[]
   for line in gzip.decompress(source('data/targets/'+path).read_bytes()).decode().splitlines():
    words=line.split()
    if not words or words[0].startswith(('#','"')):continue
    assert len(words)==4;v=list(map(float,words[1:]));deltas.append({'vertex':int(words[0]),'delta':convert(v)})
   pair[branch]=deltas
  pairs.append(pair)
 group_rel='data/mesh_metadata/basemesh_vertex_groups.json' if a.core_only else str((manifest.parent/common['source_paths']['vertex_groups']).resolve().relative_to(addon))
 rig_rel='data/rigs/standard/rig.game_engine.json' if a.core_only else str((manifest.parent/common['source_paths']['rig']).resolve().relative_to(addon))
 groups=json.loads(source(group_rel).read_text());rig=json.loads(source(rig_rel).read_text());helpers=[];bones=[]
 for name,bone in rig.items():
  endpoints={}
  assert not bone.get('roll_strategy'),'unsupported roll strategy'
  for end in ['head','tail']:
   rule=bone[end];assert not rule.get('offset'),'unsupported endpoint offset'
   if rule['strategy']=='CUBE':indices=[i for lo,hi in groups[rule['cube_name']] for i in range(lo,hi+1)]
   elif rule['strategy']=='MEAN':indices=rule['vertex_indices']
   else:raise ValueError('unsupported actual rig strategy '+rule['strategy'])
   ident=name+':'+end;helpers.append({'id':ident,'vertices':indices});endpoints[end]=ident
  bones.append({'id':name,'parent':bone['parent'] or None,'head':endpoints['head'],'tail':endpoints['tail'],'roll':bone['roll']})
 garments=[]
 if a.garment:
  garment=a.garment.resolve();ga_path=HERE.parent/'53-character-comparison/delivery/system-garment-extraction-receipt.json';ga=json.loads(ga_path.read_text());assert ga['status']=='garment-geometry-and-three-texture-dependencies-audited'
  ga_files={(HERE.parent.parent/row['path']).resolve():row for row in ga['files']}
  for garment_source in [garment,garment.with_suffix('.obj')]:
   assert garment_source in ga_files and sha(garment_source)==ga_files[garment_source]['sha256'],'garment source differs from audited archive'
   source_files.append({'path':str(garment_source),'sha256':sha(garment_source)})
  garments=[parse_proxy(garment)];assert len(garments[0]['vertices'])==sum(line.startswith('v ') for line in garment.with_suffix('.obj').read_text().splitlines())
 if not a.core_only:assert garments,'full sample requires the audited garment'
 sample_class='makehuman-approved-core-control' if a.core_only else 'makehuman-approved-sample'
 package={'schema_version':2,'sample_class':sample_class,'source_manifest_path':str(manifest),'source_manifest_sha256':sha(manifest),'source_package_revision':'MPFB 2.0.18; d0a32e57a7f915cb2f2b95410e2117648c7bbb7e; source data audited against Git blobs','compiler_provenance':{'compiler':str(pathlib.Path(__file__).resolve()),'compiler_sha256':sha(pathlib.Path(__file__)),'source_audit_sha256':sha(audit_path),'source_files':source_files,'baseline_construction':'raw source OBJ and exact declared transform, no reference vertex fitting','missing_channels':['rest matrices','inverse binds','posed skinning']},'coordinate_convention':'Blender mesh-local Z-up; root measured raw OBJ transform; all helpers retained','transform_identity':{'raw_obj_to_reference':transform,'reference_manifest_sha256':common.get('reference_manifest_sha256',sha(manifest))},'bodies':[{'topology_id':'mpfb-2.0.18-hm08-all-19158','node':'Human','mesh':'hm08-base','primitive':'source-topology','positions':basis,'signed_pairs':pairs,'helper_rules':helpers,'bone_rules':bones,'garment_rules':garments}]}
 pp=out/'compiled-package.json';pp.write_text(json.dumps(package,separators=(',',':'),allow_nan=False)+'\n')
 receipts=[]
 for case in common['cases']:
  if a.core_only:
   reference_path=ref/case['path'];reference=json.loads(reference_path.read_text());assert reference['case_id']==case['case_id'];assert sha(reference_path)==case['sha256'];values=reference['recipe'];reference_hash=case['sha256']
  else:
   reference_path=(manifest.parent/case['reference_path']).resolve();assert reference_path in allowed and allowed[reference_path]['role']=='reference';values=case['recipe'];reference_hash=allowed[reference_path]['sha256']
  recipe={'schema_version':2,'case_id':case['case_id'],'package_sha256':sha(pp),'source_manifest_sha256':sha(manifest),'values':values};p=out/(case['case_id']+'.recipe.json');p.write_text(json.dumps(recipe,indent=2)+'\n');receipts.append({'case_id':case['case_id'],'recipe':str(p),'reference':str(reference_path),'reference_sha256':reference_hash})
 (out/'compile-receipt.json').write_text(json.dumps({'sample_class':sample_class,'source_manifest_sha256':sha(manifest),'package_sha256':sha(pp),'package_bytes':pp.stat().st_size,'source_files':source_files,'cases':receipts,'reference_vertex_outputs_used_to_compile':False},indent=2)+'\n')
 print(json.dumps({'status':'compiled-source-data','sample_class':sample_class,'package':str(pp),'vertices':len(basis),'bones':len(bones),'garments':len(garments),'bytes':pp.stat().st_size}))
if __name__=='__main__':main()
