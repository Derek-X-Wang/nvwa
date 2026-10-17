"""Independent f64 FK/LBS and actual-upload contact checks; no production sampler call."""
import hashlib
import json
import math
from pathlib import Path
from geometry import norm, sub, strain, surface_queries

CLIPS=('b1_arm_rehearsal_v1','b1_knee_flex_v1')
I=[[float(i==j) for j in range(4)] for i in range(4)]
FROZEN_AMPLITUDES={0.:0.,.5:.1464466094067262,1.:.5,1.5:.8535533905932737,2.:1.,2.5:.8535533905932737,3.:.5,3.5:.1464466094067262,4.:0.}

def require(ok,message):
 if not ok:raise ValueError(message)
def finite(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def check_time_binding(record):
 # This runs before any matrix keyframe/coverage credit or geometry evaluation.
 req=record['request'];sample=record['snapshot']['sample'];seconds=req['seconds']
 require(finite(seconds) and 0<=seconds<=4,'finite requested source time out of range')
 if record['kind']=='matrix':
  k=req['k'];require(isinstance(k,int) and not isinstance(k,bool) and 0<=k<=32,'matrix k must be an integer in0..32 (not bool)')
  require(seconds==k/8,'matrix request seconds must equal k/8')
 require(sample['timeline_id']=='probe-entry','stale/wrong timeline entry binding')
 for field in ('position_seconds','source_seconds'):
  value=sample[field];require(finite(value) and 0<=value<=4,'invalid finite timeline cursor/source '+field)
  require(abs(value-seconds)<=1e-6,'requested/finite timeline cursor/source mismatch: '+field)
 return seconds

def mat(x):
 require(isinstance(x,list) and len(x)==16 and all(finite(v) for v in x),'invalid finite column-major matrix')
 return [[x[j*4+i] for j in range(4)] for i in range(4)]
def flatten(m):return [m[i][j] for j in range(4) for i in range(4)]
def mul(a,b):return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def inv(a):
 b=[a[i][:]+I[i][:] for i in range(4)]
 for k in range(4):
  pivot=max(range(k,4),key=lambda i:abs(b[i][k]));require(abs(b[pivot][k])>1e-12,'singular matrix');b[k],b[pivot]=b[pivot],b[k];d=b[k][k];b[k]=[v/d for v in b[k]]
  for i in range(4):
   if i!=k:
    d=b[i][k];b[i]=[v-d*w for v,w in zip(b[i],b[k])]
 return [r[4:] for r in b]
def error(a,b):return max(abs(x-y) for ra,rb in zip(a,b) for x,y in zip(ra,rb))
def point(m,p):return [sum(m[i][k]*p[k] for k in range(3))+m[i][3] for i in range(3)]
def rotation(axis,degrees):
 a=math.radians(degrees);c=math.cos(a);s=math.sin(a);m=[r[:] for r in I]
 if axis=='x':m[1][1]=c;m[1][2]=-s;m[2][1]=s;m[2][2]=c
 else:m[0][0]=c;m[0][1]=-s;m[1][0]=s;m[1][1]=c
 return m

def expected_fk(bones,clip,t):
 require(clip in CLIPS,'unknown authored clip')
 require(finite(t) and 0<=t<=4,'source time out of range')
 amplitude=FROZEN_AMPLITUDES.get(t,(1-math.cos(math.pi*t/2))/2)
 rotations={'upperarm_l':('z',45*amplitude),'lowerarm_l':('z',75*amplitude)} if clip==CLIPS[0] else {'calf_l':('x',65*amplitude)}
 byname={b['name']:b for b in bones};canonical={};raw={};visiting=set()
 def visit(name):
  if name in canonical:return canonical[name]
  require(name not in visiting,'cyclic rig');visiting.add(name);b=byname[name];rest=mat(b['canonical_rest']);parent=b['parent']
  if parent is None:local=rest;parent_pose=I
  else:
   require(parent in byname,'missing parent');local=mul(inv(mat(byname[parent]['canonical_rest'])),rest);parent_pose=visit(parent)
  r=rotation(*rotations[name]) if name in rotations else I
  canonical[name]=mul(parent_pose,mul(local,r));raw[name]=mul(canonical[name],mat(b['frame_gauge']));visiting.remove(name);return canonical[name]
 for name in byname:visit(name)
 return canonical,raw

def independent_lbs(rest,influences,skins):
 require(len(rest)==len(influences),'influence coverage mismatch');out=[]
 for p,row in zip(rest,influences):
  require(bool(row),'empty influence row');total=sum(w for _,w in row);require(finite(total) and total>0,'bad positive influence sum');q=[0.,0.,0.]
  for j,w in row:
   require(isinstance(j,int) and not isinstance(j,bool) and 0<=j<len(skins) and finite(w) and w>0,'invalid positive aggregate influence')
   v=point(skins[j],p)
   for k in range(3):q[k]+=v[k]*w/total
  out.append(q)
 return out

def unique(part,key):
 ids=part['source_ids'];points=part[key];require(len(ids)==len(points),'source ID/vertex coverage mismatch');out={}
 for source,p in zip(ids,points):
  if source in out:require(max(abs(a-b) for a,b in zip(p,out[source]))<=1e-5,'inconsistent duplicate source vertex')
  else:out[source]=p
 return out

def source_triangles(part):
 indices=part['indices'];require(isinstance(indices,list) and len(indices)>0 and len(indices)%3==0,'missing triangle indices');ids=part['source_ids'];out=[]
 for k in range(0,len(indices),3):
  tri=indices[k:k+3];require(all(isinstance(i,int) and not isinstance(i,bool) and 0<=i<len(ids) for i in tri),'invalid display triangle index');out.append([ids[i] for i in tri])
 return out

def sha(value):return hashlib.sha256(json.dumps(value,separators=(',',':'),sort_keys=True,allow_nan=False).encode()).hexdigest()

def check_bones(bones,clip,t):
 canonical,raw=expected_fk(bones,clip,t);max_fk=0.;max_heads=0.;max_identity=0.;skins=[]
 for b in bones:
  name=b['name'];rest=mat(b['rest']);ibm=mat(b['inverse_bind']);posed=mat(b['posed']);expected=raw[name];skin=mul(expected,ibm);skins.append(skin)
  max_heads=max(max_heads,max(abs(posed[i][3]-expected[i][3]) for i in range(3)))
  for matrix in (rest,ibm,posed,mat(b['canonical_rest']),mat(b['frame_gauge'])):
   require(max(abs(sum(matrix[k][i]*matrix[k][j] for k in range(3))-float(i==j)) for i in range(3) for j in range(3))<=1e-4,'nonrigid bone matrix')
  max_identity=max(max_identity,error(mul(rest,ibm),I));max_fk=max(max_fk,error(posed,expected),error(mat(b['canonical_posed']),canonical[name]),error(mat(b['skin']),skin))
  require(error(mul(posed,ibm),mat(b['skin']))<=1e-5,'actual posed*IBM differs from stored skin')
 require(max_identity<=1e-5,'rest*IBM identity failed');require(max_fk<=1e-4 and max_heads<=1e-5,'independent authored FK/gauge/head failed')
 return skins,max_fk,max_heads,max_identity

class Checker:
 def __init__(self,assets,surfaces=True):
  assets=Path(assets);manifest=json.loads((assets/'characters/mpfb-b1-v1/manifest.json').read_text());self.asset=assets/'characters/mpfb-b1-v1';self.manifest=manifest;self.surfaces=surfaces
  require(hashlib.sha256((self.asset/'manifest.json').read_bytes()).hexdigest()=='abcdbc26e03431c740c5fce98de22902089f985823a3c655db2416d042d62b18','wrong admitted manifest')
  for entry in manifest['files']:
   require(hashlib.sha256((self.asset/entry['path']).read_bytes()).hexdigest()==entry['sha256'],'wrong admitted input '+entry['path'])
  self.rig=json.loads((self.asset/'rig.game_engine.json').read_text());weights=json.loads((self.asset/'weights.game_engine.json').read_text())['weights'];self.weights=weights
  self.source_weights={}
  for name,rows in weights.items():
   for source,w in rows:self.source_weights.setdefault(source,{})[name]=w
  self.garment_map=[];reading=False
  for line in (self.asset/'garment/female_sportsuit01.mhclo').read_text().splitlines():
   fields=line.split()
   if not fields or fields[0].startswith('#'):continue
   if fields[0]=='verts':reading=True;continue
   if reading:
    if fields[0]=='delete_verts':break
    if len(fields)==1 and fields[0].isdigit():self.garment_map.append([(int(fields[0]),1.)])
    elif len(fields)==9:self.garment_map.append(list(zip(map(int,fields[:3]),map(float,fields[3:6]))))
    else:raise ValueError('unexpected approved garment mapping row')
  require(len(self.garment_map)==1797,'garment source mapping coverage')
  self.regions={}
  for side in ('l','r'):
   sums={}
   for bone in ('foot_'+side,'ball_'+side):
    for i,w in weights[bone]:sums[i]=sums.get(i,0.)+w
   self.regions[side]={i for i,w in sums.items() if i<13380 and w>=.5}
  self.body_triangles=[]
  for line in (self.asset/'base.obj').read_text().splitlines():
   if line.startswith('f '):
    ids=[int(x.split('/')[0])-1 for x in line.split()[1:]]
    if all(0<=i<13380 for i in ids):
     self.body_triangles.extend([[ids[0],ids[k],ids[k+1]] for k in range(1,len(ids)-1)])
  self.baselines={};self.rests={};self.seen=set();self.keyframes=0
 def check(self,record):
  check_time_binding(record)
  frame=record['snapshot'];req=record['request'];sample=frame['sample'];clip=sample['clip_id'];t=sample['source_seconds'];params=frame['parameters'];recipe=(float(params['torso_length']),float(params['jaw_drop']));deep=record.get('deep',False) or (record['kind']=='matrix' and recipe[1]==0 and req['k']%8==0)
  require(frame['schema_version']==1,'wrong snapshot version');require(frame['profile_id']=='nvwa-mpfb-b1-motion-v1','not motion profile');require(frame['mode']=='motion','not motion mode');require(clip in CLIPS,'unknown sample clip')
  require(sample['timeline_id']=='probe-entry','stale/wrong timeline entry binding');require(req['clip_id']==clip and abs(req['seconds']-t)<=1e-6,'requested/source finite-clip time mismatch');require(all(params[k]==req[k] for k in ['torso_length','jaw_drop']),'recipe mismatch');require(sample['playing'] is False,'exact sample must be paused');require(isinstance(sample['serial'],int) and sample['serial']>=0,'missing sample serial')
  bones=frame['bones'];require(len(bones)==53 and {b['name']:b['parent'] for b in bones}=={n:(v['parent'] or None) for n,v in self.rig.items()},'actual source rig coverage/hierarchy mismatch')
  skins,max_fk,max_heads,max_identity=check_bones(bones,clip,t)
  rest_digest=sha([{k:b[k] for k in ['name','parent','rest','inverse_bind','canonical_rest','frame_gauge']} for b in bones]);key=(recipe,clip)
  if key in self.rests:require(rest_digest==self.rests[key],'fitted rest/IBM/gauge changed during clip')
  else:self.rests[key]=rest_digest
  parts={p['name']:p for p in frame['parts']};require(set(parts)=={'body','garment'},'both actual uploaded parts required');part_metrics={};placements={}
  for name,count in [('body',19158),('garment',1797)]:
   p=parts[name];ids=p['source_ids'];require(set(ids)==set(range(count)),name+' source coverage mismatch');require(len(p['positions'])==len(ids) and len(p['rest_positions'])==len(ids),name+' position lengths')
   for field,width in [('positions',3),('rest_positions',3),('normals',3),('rest_normals',3),('tangents',4)]:
    rows=p[field];require(len(rows)==len(ids) and all(isinstance(row,list) and len(row)==width and all(finite(x) for x in row) for row in rows),name+' invalid finite '+field)
    if field in ('normals','rest_normals','tangents'):
     require(all(abs(norm(row[:3])-1)<=1e-4 for row in rows),name+' nonunit '+field)
     if field=='tangents':require(all(abs(abs(row[3])-1)<=1e-6 for row in rows),'invalid tangent handedness')
   require(p.get('display_entity') is not None and p.get('mesh_handle') is not None,'actual display identity missing');tri=source_triangles(p)
   placement=mul(mat(p['display_transform']),inv(mat(p['model_to_world'])));placements[name]=placement
   if key in self.baselines:require(error(placement,self.baselines[key]['placement'])<=1e-6,'fixed fitted-rest placement changed (posed-floor correction?)')
   lbs=None
   if deep:
    # Independent transfer from authenticated source weights and signed MHCLO rows.
    influence_error=0.;expected_rows=[]
    for source,actual_row in zip(ids,p['full_joint_influences']):
     source_row={}
     mapping=[(source,1.)] if name=='body' else self.garment_map[source]
     for helper,coefficient in mapping:
      for bone,weight in self.source_weights.get(helper,{}).items():source_row[bone]=source_row.get(bone,0.)+coefficient*weight
     source_row={bone:weight for bone,weight in source_row.items() if weight>0};total=sum(source_row.values());require(total>0,'empty source transferred influence')
     expect={i:source_row[b['name']]/total for i,b in enumerate(bones) if b['name'] in source_row};actual_total=sum(w for _,w in actual_row);require(actual_total>0,'empty actual transferred influence');actual={i:w/actual_total for i,w in actual_row}
     influence_error=max(influence_error,max(abs(expect.get(i,0)-actual.get(i,0)) for i in set(expect)|set(actual)))
     expected_rows.append(list(expect.items()))
    require(influence_error<=1e-6,name+' independently sourced positive aggregate weights mismatch')
    expected=independent_lbs(p['rest_positions'],expected_rows,skins);lbs=max(abs(x-y) for a,b in zip(expected,p['positions']) for x,y in zip(a,b));require(lbs<=1e-5,name+' independent LBS vs actual uploaded POSITION failed')
   part_metrics[name]={'mesh_handle':p['mesh_handle'],'display_entity':p['display_entity'],'uploaded_position_sha256':sha(p['positions']),'display_indices_sha256':sha(p['indices']),'vertices':len(ids),'triangles':len(tri),'independent_lbs_max_component':lbs,'independent_lbs_status':'PASS' if deep else 'NOT-RUN (predeclared keyframe subset)'}
  require(error(placements['body'],placements['garment'])<=1e-6,'body/garment placement mismatch')
  body=parts['body'];byid=unique(body,'positions');restbyid=unique(body,'rest_positions');displayed=set(i for tri in source_triangles(body) for i in tri);world=mat(body['display_transform']);worldpoints={i:point(world,p) for i,p in byid.items()};restpoints={i:point(world,p) for i,p in restbyid.items()}
  if key not in self.baselines:
   require(record['kind']=='studio' or abs(t)<=1e-6,'first exact recipe/clip capture must be neutral')
   patches={};regions={}
   for side,source in self.regions.items():
    region=sorted(source & displayed);require(bool(region),'empty displayed foot region');low=min(restpoints[i][1] for i in region);patch=[i for i in region if restpoints[i][1]<=low+.003];require(bool(patch),'empty geometric low patch');regions[side]=region;patches[side]=patch
   self.baselines[key]={'placement':placements['body'],'patches':patches,'regions':regions,'points':{i:restpoints[i] for patch in patches.values() for i in patch},'mesh_handles':{n:p['mesh_handle'] for n,p in parts.items()}}
  baseline=self.baselines[key];feet={}
  for side,label in [('l','left'),('r','right')]:
   patch=baseline['patches'][side];region=baseline['regions'][side];moving=clip==CLIPS[1] and side=='l' and 0<t<4;declared='moving' if moving else 'planted';require(frame['contacts'][label]==declared,'wrong authored contact declaration');points=[worldpoints[i] for i in patch];drift=max(norm(sub(worldpoints[i],baseline['points'][i])) for i in patch);minimum=min(worldpoints[i][1] for i in region);patchmin=min(p[1] for p in points)
   require(minimum>=-.001,label+' foot region below floor')
   if not moving:require(drift<=.001 and abs(patchmin)<=.001,label+' planted geometric patch drift/contact failed')
   if moving and abs(t-2)<1e-6:require(minimum>=.020,'left moving apex clearance below20mm')
   feet[label]={'declared':declared,'patch_ids':patch,'patch_world_points':points,'region_vertices':len(region),'region_min_world_y':minimum,'patch_min_world_y':patchmin,'patch_max_world_y':max(p[1] for p in points),'max_patch_displacement_from_rest':drift,'anatomical_sole_claim':False}
  for name,p in parts.items():require(p['mesh_handle']==baseline['mesh_handles'][name],'per-frame mesh handle replacement')
  metrics={'kind':record['kind'],'request':req,'sample':sample,'parameters':params,'generation':frame['generation'],'revision':frame['revision'],'actual_bones':bones,'actual_bones_sha256':sha(bones),'parts':part_metrics,'feet':feet,'placement':flatten(placements['body']),'independent_fk_max_component':max_fk,'independent_joint_head_max_component':max_heads,'rest_ibm_identity_max_component':max_identity,'technical_pass':True,'quality':'HOLD; known sportsuit folds/poke-through','gpu_vertex_readback':False}
  if record['kind']=='matrix':
   samplekey=(recipe,clip,req['k']);require(samplekey not in self.seen,'duplicate matrix sample');self.seen.add(samplekey)
  if record['kind']=='pause':
   require(sample['source_seconds']==req['prior_sample']['source_seconds'],'paused source time advanced')
   old={p['name']:p['positions'] for p in req['prior_parts']};require(all(parts[n]['positions']==v for n,v in old.items()),'paused actual uploaded positions changed')
  if deep:
   if record['kind']=='matrix':self.keyframes+=1
   garment=parts['garment'];gp=unique(garment,'positions');gr=unique(garment,'rest_positions');gt=source_triangles(garment);metrics['garment_strain']=strain(gp,gr,gt)
   if self.surfaces:
    metrics['garment_to_full_body']=surface_queries(byid,self.body_triangles,list(gp.values()),list(gp))
    dt=source_triangles(body);metrics['garment_to_displayed_body']=surface_queries(byid,dt,list(gp.values()),list(gp))
    visible=sorted(displayed);probeids=[visible[round(k*(len(visible)-1)/255)] for k in range(256)]
    metrics['displayed_body_to_garment']=surface_queries(gp,gt,[byid[i] for i in probeids],probeids)
   else:metrics['surface_descriptors']='NOT-RUN; explicitly disabled'
   metrics['general_triangle_intersections']='NOT-RUN; bounded first-slice contract'
  return metrics,deep
 def coverage(self):
  expected={((float(t),float(j)),c,k) for t in [-1,0,1] for j in [-1,0,1] for c in CLIPS for k in range(33)}
  missing=sorted(expected-self.seen)
  return {'expected':594,'observed':len(self.seen),'missing':missing,'deep_keyframes_expected':30,'deep_keyframes_observed':self.keyframes,'complete':not missing and self.keyframes==30,'body_variants':3,'face_settings':3}
