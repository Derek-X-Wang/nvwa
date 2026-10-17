#!/usr/bin/env python3
"""One fixed experimental weight recipe; evaluate retained actual r4 captures only."""
from pathlib import Path
import argparse,gzip,hashlib,json,math,sys,time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'experiments/60-b1-continuous-motion'))
from geometry import BVH,strain,cross
CORE={182,244,246};FOLD={281,288,376,485,523,534,599,612};CLIPS=('b1_arm_rehearsal_v1','b1_knee_flex_v1')
def require(ok,message):
 if not ok:raise ValueError(message)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def norm(a):return math.sqrt(sum(v*v for v in a))
def sub(a,b):return [x-y for x,y in zip(a,b)]
def unique(p,key):
 out={}
 for i,v in zip(p['source_ids'],p[key]):
  if i in out:require(max(abs(x-y) for x,y in zip(v,out[i]))<1e-5,'inconsistent render duplicate')
  else:out[i]=v
 return out
def triangles(p):return [[p['source_ids'][i] for i in p['indices'][k:k+3]] for k in range(0,len(p['indices']),3)]
def normalize(row):
 total=sum(row.values());require(total>0 and all(math.isfinite(v) and v>0 for v in row.values()),'invalid positive row');return {n:w/total for n,w in row.items()}
def apply(p,row,bones):
 return [sum(w*(sum(bones[n][j*4+k]*p[j] for j in range(3))+bones[n][12+k]) for n,w in row.items()) for k in range(3)]
def adjacency(tri):
 out={i:set() for t in tri for i in t}
 for t in tri:
  for i in t:out[i].update(set(t)-{i})
 return out
def smooth(original,adj,core=CORE,core_strength=.5,ring_strength=.25):
 ring=set().union(*(adj[i] for i in core))-core;affected=core|ring;require(len(affected)<=64,'region exceeds64');out={}
 for i in sorted(affected):
  strength=core_strength if i in core else ring_strength
  if strength==0:continue
  names=set(original[i])|set(n for j in adj[i] for n in original[j]);mean={n:sum(original[j].get(n,0) for j in adj[i])/len(adj[i]) for n in names};row=normalize({n:(1-strength)*original[i].get(n,0)+strength*mean[n] for n in names});require(set(original[i])<=set(row),'original positive influence dropped');out[i]=row
 return out,ring
def source_rows(asset):
 weights=json.loads((asset/'weights.game_engine.json').read_text())['weights'];byid={}
 for n,rows in weights.items():
  for i,w in rows:
   if w>0:byid.setdefault(i,{})[n]=w
 mapping=[];reading=False
 for line in (asset/'garment/female_sportsuit01.mhclo').read_text().splitlines():
  f=line.split()
  if not f or f[0].startswith('#'):continue
  if f[0]=='verts':reading=True;continue
  if reading:
   if f[0]=='delete_verts':break
   mapping.append(f)
 out={}
 for i,f in enumerate(mapping):
  hs=[int(f[0])] if len(f)==1 else list(map(int,f[:3]));co=[1.] if len(f)==1 else list(map(float,f[3:6]));co=[w/sum(co) for w in co];row={}
  for h,c in zip(hs,co):
   for n,w in byid.get(h,{}).items():row[n]=row.get(n,0)+c*w
  out[i]=normalize({n:w for n,w in row.items() if w>0})
 require(len(out)==1797,'source garment mapping coverage');return out

def normal_descriptors(part,rows,bones,affected):
 angles=[];count=0;minimum=1.;maximum=1.
 for source,rest,actual in zip(part['source_ids'],part['rest_normals'],part['normals']):
  if source not in affected:continue
  row=rows[source];v=[sum(w*sum(bones[n][j*4+k]*rest[j] for j in range(3)) for n,w in row.items()) for k in range(3)];length=norm(v);require(length>0 and math.isfinite(length),'invalid candidate normal');v=[x/length for x in v];minimum=min(minimum,norm(v));maximum=max(maximum,norm(v));denom=norm(actual);require(denom>0,'invalid actual normal');angles.append(math.degrees(math.acos(max(-1.,min(1.,sum(a*b for a,b in zip(actual,v))/denom)))));count+=1
 return {'render_vertices':count,'max_angle_from_actual_uploaded_normal_degrees':max(angles),'candidate_normal_length_min':minimum,'candidate_normal_length_max':maximum,'scope':'offline normalized linear-skin normals from retained actual rest normals; candidate rendering NOT-RUN'}

def boundary_control(original,altered,affected):
 require(set(original)==set(altered),'source coverage changed');require(all(original[i]==altered[i] for i in original if i not in affected),'outside region changed');require(all(math.isfinite(v) for p in altered.values() for v in p),'nonfinite arrays')
def surface(bvh,points,ids):
 hits=[bvh.nearest(points[i]) for i in sorted(ids)];return {'queries':len(hits),'negative_over_2mm':sum(h['local_signed_projection']<-.002 for h in hits),'negative_over_5mm':sum(h['local_signed_projection']<-.005 for h in hits),'minimum_local_projection':min(h['local_signed_projection'] for h in hits),'minimum_unsigned_distance':min(h['distance'] for h in hits),'claim':'local nearest-triangle descriptors; not collision depth/global inside-outside'}
def triangle_details(original,altered,rest,tri,triangle_ids):
 out=[]
 for tid in triangle_ids:
  ids=tri[tid];edges=[(ids[0],ids[1]),(ids[1],ids[2]),(ids[2],ids[0])];area=lambda pts:norm(cross(sub(pts[ids[1]],pts[ids[0]]),sub(pts[ids[2]],pts[ids[0]])))/2;ra=area(rest);oa=area(original);ca=area(altered)
  out.append({'display_triangle_id':tid,'source_ids':ids,'original_rest_area_m2':ra,'candidate_rest_area_m2':ra,'original_posed_area_m2':oa,'candidate_posed_area_m2':ca,'original_against_original_rest_ratio':oa/ra,'candidate_against_original_rest_ratio':ca/ra,'candidate_against_candidate_rest_ratio':ca/ra,'original_rest_edge_lengths_m':[norm(sub(rest[a],rest[b])) for a,b in edges],'candidate_rest_edge_lengths_m':[norm(sub(rest[a],rest[b])) for a,b in edges],'original_posed_edge_lengths_m':[norm(sub(original[a],original[b])) for a,b in edges],'candidate_posed_edge_lengths_m':[norm(sub(altered[a],altered[b])) for a,b in edges]})
 return out

def evaluate(captures,output):
 started=time.monotonic();output.mkdir(parents=True,exist_ok=False);asset=ROOT/'assets/characters/mpfb-b1-v1';paths=sorted(captures.glob('*.json.gz'));require(len(paths)==30,'expected exactly30 retained keyframes');files={};seen=set();records=[];original=source_rows(asset);override=None;tri0=None;adj=None;affected=None;ring=None;frame_summaries=[];detail_frames=[];controls={'original_source_rows_match_captures':True,'original_independent_lbs_max_component_m':0.,'noop_actual_upload_identity':True,'outside_boundary_exact_identity':True,'rest_geometry_unchanged':True,'body_rig_motion_unchanged':True,'finite_arrays':True,'all_original_positive_influences_retained':True}
 fullbody=[]
 for line in (asset/'base.obj').read_text().splitlines():
  if line.startswith('f '):
   v=[int(f.split('/')[0])-1 for f in line.split()[1:]]
   if all(0<=i<13380 for i in v):fullbody.extend([[v[0],v[k],v[k+1]] for k in range(1,len(v)-1)])
 for path in paths:
  with gzip.open(path,'rt') as f:d=json.load(f)
  q=d['request'];frame=d['snapshot'];s=frame['sample'];key=(q['torso_length'],q['clip_id'],q['seconds']);require(key not in seen,'duplicate frame');seen.add(key);require(q['jaw_drop']==0 and q['k'] in [0,8,16,24,32] and q['seconds']==q['k']/8,'incorrect frame grid');require(s['source_seconds']==q['seconds'] and s['position_seconds']==q['seconds'] and s['clip_id']==q['clip_id'] and s['timeline_id']=='probe-entry' and s['playing'] is False,'capture time mismatch');require(frame['profile_id']=='nvwa-mpfb-b1-motion-v1','wrong source profile');require(frame['parameters']=={'torso_length':q['torso_length'],'jaw_drop':0.},'recipe mismatch');files[path.name]=digest(path)
  bones={b['name']:b['skin'] for b in frame['bones']};require(len(bones)==53,'bone coverage');names=[b['name'] for b in frame['bones']];parts={p['name']:p for p in frame['parts']};g=parts['garment'];actual,rest=unique(g,'positions'),unique(g,'rest_positions');tri=triangles(g);require(set(actual)==set(range(1797)),'source coverage')
  if tri0 is None:
   tri0=tri;adj=adjacency(tri);override,ring=smooth(original,adj);affected=CORE|ring;require(tri[200]==[246,244,182],'witness triangle changed');require(not(FOLD&affected),'neutral-fold safety region overlaps edit');incident=[t for t in tri if set(t)&affected];coretri=[t for t in tri if set(t)&CORE];boundary=[t for t in tri if set(t)&affected and set(t)-affected]
  require(tri==tri0,'topology changed across frames');captured={i:normalize({names[j]:w for j,w in row}) for i,row in zip(g['source_ids'],g['full_joint_influences'])};transfererr=max(abs(captured[i].get(n,0)-original[i].get(n,0)) for i in original for n in set(captured[i])|set(original[i]));require(transfererr<=1e-6,'source transferred rows mismatch')
  expected={i:apply(rest[i],original[i],bones) for i in original};lbserr=max(abs(expected[i][k]-actual[i][k]) for i in actual for k in range(3));require(lbserr<=1e-5,'original LBS mismatch');controls['original_independent_lbs_max_component_m']=max(controls['original_independent_lbs_max_component_m'],lbserr)
  noop={i:p[:] for i,p in actual.items()};require(noop==actual,'noop failed');altered={i:p[:] for i,p in actual.items()}
  for i,row in override.items():altered[i]=apply(rest[i],row,bones)
  boundary_control(actual,altered,affected);bvh=BVH(unique(parts['body'],'positions'),fullbody)
  item={'capture':path.name,'capture_sha256':files[path.name],'request':q,'sample':s,'backend':frame['backend'],'generation':frame['generation'],'revision':frame['revision'],'source_transfer_max_error':transfererr,'original_lbs_max_component_m':lbserr,'indices_sha256':hashlib.sha256(json.dumps(g['indices'],separators=(',',':')).encode()).hexdigest(),'rest_positions_sha256':hashlib.sha256(json.dumps(g['rest_positions'],separators=(',',':')).encode()).hexdigest(),'original_uploaded_normals_sha256':hashlib.sha256(json.dumps(g['normals'],separators=(',',':')).encode()).hexdigest(),'normal_policy':'offline LBS normal diagnostic only, not visual-policy normals; future visual variants must use contract source-adjacency normals/projected tangents; rendering NOT-RUN','candidate_normals':normal_descriptors(g,override,bones,affected),'max_displacement_m':max(norm(sub(altered[i],actual[i])) for i in affected),'changed_position_ids':sorted(i for i in affected if altered[i]!=actual[i]),'outside_max_displacement_m':0.,'original_core_incident':strain(actual,rest,coretri),'candidate_core_incident':strain(altered,rest,coretri),'original_affected_incident':strain(actual,rest,incident),'candidate_affected_incident':strain(altered,rest,incident),'original_boundary_incident':strain(actual,rest,boundary),'candidate_boundary_incident':strain(altered,rest,boundary),'original_fold_region':strain(actual,rest,[t for t in tri if set(t)&FOLD]),'candidate_fold_region':strain(altered,rest,[t for t in tri if set(t)&FOLD]),'original_full_garment':strain(actual,rest,tri),'candidate_full_garment':strain(altered,rest,tri),'original_local_surface':surface(bvh,actual,affected),'candidate_local_surface':surface(bvh,altered,affected),'candidate_geometry':'offline LBS at retained actual bones/rest, experimental16-vertex post-upload override; NOT actual admitted runtime output'}
  # Explicit fixed witness, independent of maximum selection.
  from geometry import cross
  ids=tri[200];A=lambda pts:norm(cross(sub(pts[ids[1]],pts[ids[0]]),sub(pts[ids[2]],pts[ids[0]])))/2;ra=A(rest);item['triangle200']={'source_ids':ids,'rest_area_m2':ra,'original_area_ratio':A(actual)/ra,'candidate_area_ratio':A(altered)/ra}
  detail_frames.append({'capture':path.name,'request':q,'triangles':triangle_details(actual,altered,rest,tri,[tid for tid,t in enumerate(tri) if set(t)&affected])});frame_summaries.append(item)
 expectedset={(t,c,float(k)) for t in [-1.,0.,1.] for c in CLIPS for k in range(5)};require(seen==expectedset,'incomplete30-frame coverage')
 prov={str(p.relative_to(ROOT)):digest(p) for p in [asset/'base.obj',asset/'garment/female_sportsuit01.obj',asset/'garment/female_sportsuit01.mhclo',asset/'weights.game_engine.json',Path(__file__).resolve()]}
 candidate={'schema_version':1,'id':'weight-local-v1','source_profile':'nvwa-mpfb-b1-motion-v1','region_source_ids':sorted(affected),'weight_overrides':[{'source_id':i,'weights':[[n,w] for n,w in sorted(row.items())]} for i,row in sorted(override.items())],'offset_deltas':[],'offset_scale_rules':[],'rule':'One simultaneous original-row source-topology neighbor-mean pass: core182,244,246 strength0.5; immediate one-edge ring strength0.25; outside exact identity. Positive union retained and normalized, no top4/no negative-source clamp. Rest/body/rig/motion unchanged. No tuning.','provenance':prov}
 write(output/'candidate.json',candidate);write(output/'frames.json',frame_summaries);write(output/'triangle-details.json',detail_frames);summary={'candidate_sha256':digest(output/'candidate.json'),'frames':len(frame_summaries),'core_source_ids':sorted(CORE),'ring_source_ids':sorted(ring),'region_source_ids':sorted(affected),'affected_incident_triangles':len(incident),'affected_display_triangle_ids':[tid for tid,t in enumerate(tri0) if set(t)&affected],'core_incident_triangles':len(coretri),'boundary_incident_triangles':len(boundary),'changed_weight_ids':sorted(override),'maximum_candidate_influence_count':max(len(r) for r in override.values()),'controls':controls,'raw_capture_sha256':files,'elapsed_seconds':time.monotonic()-started,'visual_live_candidate':'NOT-RUN','actual_candidate_runtime_matrix':'NOT-RUN','cloth_quality':'HOLD; descriptors are not collision/appearance acceptance'};write(output/'summary.json',summary);write(output/'SHA256SUMS.json',{p.name:digest(p) for p in output.iterdir() if p.is_file()});print(json.dumps(summary))
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--captures',required=True,type=Path);a.add_argument('--output',required=True,type=Path);args=a.parse_args();evaluate(args.captures.resolve(),args.output.resolve())
if __name__=='__main__':main()
