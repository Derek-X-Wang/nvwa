#!/usr/bin/env python3
"""Analytical source correspondence; old CPU geometry/new saved camera, not GPU IDs."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
SUPPORT = ROOT / 'experiments/70-b1-garment-defect'
sys.path.insert(0, str(SUPPORT))
from diagnose import point, require, triangles

FRAME_SHA = '82e27eadb01a9db21855b1f050c1c06222c9412fa3351c5029aa5fbe30da8206'
WORK_SHA = '001ad5aab777bc0c4c3c011f42bf55f9674a15092287f0104ec3505a758e5174'
ROI = (330, 185, 350, 205)
# Existing geometry arithmetic bounds; not image or garment acceptance thresholds.
DISTANCE_EPS = 1e-5
BARY_EPS = 1e-9

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sub(a,b): return [x-y for x,y in zip(a,b)]
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
def unit(v):
 n=math.sqrt(dot(v,v)); require(n>1e-15, 'zero vector'); return [x/n for x in v]
def camera(c):
 az,el=map(math.radians,(c['azimuth_degrees'],c['elevation_degrees']))
 back=[math.sin(az)*math.cos(el),math.sin(el),math.cos(az)*math.cos(el)]
 right=unit(cross([0,1,0],back)); up=cross(back,right)
 origin=[c['distance']*x+(c['target_height'] if i==1 else 0) for i,x in enumerate(back)]
 return right,up,back,origin

def projection(c):
 near=.05; fw,fh,sw,sh=81920.,39040.,81920.,46080.
 top=near*math.tan(math.radians(c['fov_degrees'])/2); right=top*fw/fh
 # Existing SubCameraView: offset0, scene610px and canvas720px, not viewport aspect.
 bottom=-top; by=fh-sh
 bp=bottom+2*top*by/fh; tp=top
 return near/right,2*near/(tp-bp),0.,(tp+bp)/(tp-bp)

def project(p,cam,frustum):
 right,up,back,origin=cam[:4]; delta=sub(p,origin)
 axes=cam[4] if len(cam)==5 else (right,up,back)
 v=[dot(a,delta) for a in axes]; w=-v[2]
 require(w>.05,'geometry crosses near plane; no projected-bbox shortcut allowed')
 x,y,a,b=frustum
 return [(1+(x*v[0]+a*v[2])/w)*640,(1-(y*v[1]+b*v[2])/w)*360]

def ray(pixel,cam,frustum):
 x,y,a,b=frustum; nx,ny=pixel[0]/640-1,1-pixel[1]/360
 v=[(nx+a)/x,(ny+b)/y,-1]
 return unit([sum(cam[k][i]*v[k] for k in range(3)) for i in range(3)])

def intersect(origin,direction,ps):
 a,b,c=ps; e1,e2=sub(b,a),sub(c,a); p=cross(direction,e2); determinant=dot(e1,p)
 if abs(determinant)<1e-12: return None
 s=sub(origin,a); u=dot(s,p)/determinant; q=cross(s,e1); v=dot(direction,q)/determinant; t=dot(e2,q)/determinant
 if u < -BARY_EPS or v < -BARY_EPS or u+v>1+BARY_EPS or t<0:return None
 return {'distance_m':t,'barycentric':[1-u-v,u,v],'front_facing_by_winding':determinant>0}

def read_obj(path):
 faces=[]; group=None
 for line_number,line in enumerate(path.read_text().splitlines(),1):
  row=line.split()
  if not row:continue
  if row[0]=='g':group=' '.join(row[1:])
  if row[0]=='f':
   ids=[int(v.split('/')[0])-1 for v in row[1:]]
   faces.append({'source_face0':len(faces),'OBJ_line1':line_number,'group':group,'source_ids':ids})
 return faces

def deleted_ids(path):
 tokens=re.findall(r'\d+|-',path.read_text().split('delete_verts',1)[1]); result=set();i=0
 while i<len(tokens):
  first=int(tokens[i]);i+=1
  if i<len(tokens) and tokens[i]=='-':
   last=int(tokens[i+1]);i+=2;result.update(range(first,last+1))
  else:result.add(first)
 return result

def cyclic(t):return min(tuple(t[i:]+t[:i]) for i in range(3))

def bind_source(part,faces,delete=None):
 expected=[]; lookup={}; removed=[]
 for face in faces:
  ids=face['source_ids']; hidden=delete is not None and (any(i>=13380 for i in ids) or all(i in delete for i in ids))
  if hidden:removed.append(face['source_face0']);continue
  for j in range(1,len(ids)-1):
   tri=[ids[0],ids[j],ids[j+1]];expected.append(tri); key=cyclic(tri)
   require(key not in lookup,'ambiguous duplicate source triangle');lookup[key]={**face,'fan_triangle0':j-1}
 actual=triangles(part)
 require(len(actual)==len(expected),'body deletion/source triangle count mismatch')
 require(Counter(map(cyclic,actual))==Counter(map(cyclic,expected)),'actual displayed topology differs from source/mask')
 return [lookup[cyclic(t)] for t in actual],removed,actual

def controls():
 c={'azimuth_degrees':180,'elevation_degrees':3,'distance':.95,'target_height':1.2807446,'fov_degrees':30}
 cam=camera(c);fr=projection(c)
 require(max(abs(a-b) for a,b in zip(project([0,c['target_height'],0],cam,fr),[640,305]))<1e-9,'scene-center control')
 for pixel in ([340.5,196.5],[330.5,185.5],[349.5,204.5]):
  d=ray(pixel,cam,fr); p=[o+v*.9 for o,v in zip(cam[3],d)]
  require(max(abs(a-b) for a,b in zip(project(p,cam,fr),pixel))<1e-9,'ray/project inverse control')
 tri=[[-1,-1,1],[1,-1,1],[0,1,1]]
 require(abs(intersect([0,0,0],[0,0,1],tri)['distance_m']-1)<1e-12,'front ray control')
 require(intersect([0,0,0],[0,0,1],list(reversed(tri))) is not None,'double-sided control')
 require(intersect([3,0,0],[0,0,1],tri) is None,'miss control')
 return 7

def run(args):
 require(not args.out.exists(),'existing output would be overwritten');args.out.mkdir(parents=True)
 require(digest(args.work)==WORK_SHA,'frozen saved Work mismatch')
 expected_sha=args.actual_frame_sha256 or FRAME_SHA
 require(digest(args.frame)==expected_sha,'frame SHA mismatch')
 require(bool(args.actual_frame_sha256)==bool(args.actual_request_id),'fresh mode needs independent frame SHA and request ID')
 envelope=json.loads(args.frame.read_text());frame=envelope['frame'];work=json.loads(args.work.read_text());oldwork=json.loads(envelope['report']['work_json'])
 sample=frame['full_base']['sample']
 require(sample['source_seconds']==sample['position_seconds']==2 and sample['clip_id']=='b1_arm_rehearsal_v1' and sample['playing'] is False,'independently required actual held arm source2 differs')
 require(all(work[k]==oldwork[k] for k in ('profile','character','timeline')),'new saved recipe/action differs from old CPU geometry')
 c=work['stage']['camera'];require(c=={'azimuth_degrees':180.,'elevation_degrees':3.,'distance':.95,'target_height':1.2807446,'fov_degrees':30.},'fixed rear camera changed')
 cam=camera(c); frustum=projection(c); controls_count=controls()
 if args.actual_frame_sha256:
  report=envelope['report']; rid=args.actual_request_id
  require(report['phase']=='ready' and all(report[k] is True for k in ('acknowledged','request_succeeded','current')),'fresh envelope not ready/current')
  require(report['request_id']==frame['request_id']==rid,'fresh request pairing mismatch')
  require(json.loads(report['work_json'])==work,'fresh actual Work values differ')
  require(hashlib.sha256(report['work_json'].encode()).hexdigest()==report['work_sha256']==frame['work_sha256'],'fresh actual Work hash mismatch')
  require(report['captured_identity']==frame['identity'] and report['camera']==frame['camera']==frame['identity']['camera'],'fresh camera/currentness binding differs')
  actual=frame['camera']; m=actual['global_transform']
  require(actual['viewport']==[1280,720] and actual['active'] is True,'fresh viewport unavailable')
  require(actual['sub_camera_view']=='Some(SubCameraView { full_size: UVec2(81920, 39040), offset: Vec2(0.0, 0.0), size: UVec2(81920, 46080) })','fresh subcamera differs')
  require('fov: 0.5235988,' in actual['projection'] and 'near: 0.05,' in actual['projection'],'fresh projection differs')
  predicted=camera(c)
  right,up,back=([m[0],m[1],m[2]],[m[4],m[5],m[6]],[m[8],m[9],m[10]])
  det=dot(right,cross(up,back));require(abs(det)>1e-12,'actual camera singular')
  inverse_rows=[[x/det for x in v] for v in (cross(up,back),cross(back,right),cross(right,up))]
  cam=(right,up,back,m[12:15],inverse_rows)
  require(max(abs(a-b) for col,pcol in zip(cam,predicted) for a,b in zip(col,pcol))<1e-6,'fresh camera not frozen rear')
  # Use exported f32 camera basis and exported fov debug value, not saved-camera prediction.
  # Invert exported affine basis explicitly; do not assume f32 basis is exactly orthogonal.
  fov=float(re.search(r'fov: ([0-9.e-]+)',actual['projection'])[1]);near=.05
  top=near*math.tan(fov/2);right=top*1280/610;bottom=-top;bp=bottom+2*top*(610-720)/610
  frustum=(near/right,2*near/(top-bp),0.,(top+bp)/(top-bp))
 asset=ROOT/'assets'/work['profile']['asset_path'];require(digest(asset)==work['profile']['asset_sha256'],'descriptor changed')
 descriptor=json.loads(asset.read_text())
 for entry in descriptor['files']:
  p=asset.parent/entry['path'];require(p.stat().st_size==entry['bytes'] and digest(p)==entry['sha256'],'payload identity failure')
 source=ROOT/'assets/characters/mpfb-b1-v1';delete=deleted_ids(source/'garment/female_sportsuit01.mhclo')
 bindings={}; all_meshes={}; candidates=[]; alpha_candidates=[]; topology={}
 for buf in frame['buffers']:
  role=buf['role'];world=[point(buf['display_transform'],p) for p in buf['positions']]
  pixels=[project(p,cam,frustum) for p in world]
  render_tris=[buf['indices'][k:k+3] for k in range(0,len(buf['indices']),3)]
  all_meshes[role]={'world':world,'pixels':pixels,'triangles':render_tris}
  if role in ('body','garment'):
   part=next(p for p in frame['full_base']['parts'] if p['name']==role)
   require(all(part[k]==buf[k] for k in ('positions','indices','display_transform')),'display/full-base mismatch')
   path=source/('base.obj' if role=='body' else 'garment/female_sportsuit01.obj')
   binding,removed,source_triangles=bind_source(part,read_obj(path),delete if role=='body' else None)
   bindings[role]=binding
   topology[role]={'OBJ_sha256':digest(path),'actual_render_triangles':len(render_tris),'source_faces_removed_by_existing_policy':len(removed),'source_ids_match':True,'removed_source_face0':removed,'delete_vertices_count':len(delete) if role=='body' else None}
  for ti,tri in enumerate(render_tris):
   pp=[pixels[i] for i in tri]; box=[min(p[j] for p in pp) for j in (0,1)]+[max(p[j] for p in pp) for j in (0,1)]
   if box[2]<ROI[0] or box[0]>ROI[2] or box[3]<ROI[1] or box[1]>ROI[3]:continue
   row={'role':role,'render_triangle0':ti,'screen_points':pp,'pixel_bbox':box,'world_points':[world[i] for i in tri]}
   if role in bindings:row['source']=bindings[role][ti];row['source_triangle_ids']=source_triangles[ti];candidates.append(row)
   else:alpha_candidates.append(row)
 samples=[];first_counts=Counter();body_first=[]
 for y in range(ROI[1],ROI[3]):
  for x in range(ROI[0],ROI[2]):
   pixel=[x+.5,y+.5];direction=ray(pixel,cam,frustum);hits=[]
   for row in candidates+alpha_candidates:
    box=row['pixel_bbox']
    if not(box[0]-1e-9<=pixel[0]<=box[2]+1e-9 and box[1]-1e-9<=pixel[1]<=box[3]+1e-9):continue
    hit=intersect(cam[3],direction,row['world_points'])
    if hit:hits.append({**hit,'role':row['role'],'render_triangle0':row['render_triangle0'],'source':row.get('source'),'source_triangle_ids':row.get('source_triangle_ids')})
   opaque=sorted([h for h in hits if h['role'] in ('body','garment')],key=lambda h:h['distance_m'])
   alpha=sorted([h for h in hits if h['role'] not in ('body','garment')],key=lambda h:h['distance_m'])
   first=opaque[0] if opaque else None
   cluster=[h for h in opaque if h['distance_m']<=first['distance_m']+DISTANCE_EPS] if first else []
   if first:
    first_counts[(first['role'],first['render_triangle0'],first['source']['source_face0'])]+=1
    if first['role']=='body':body_first.append(pixel)
   samples.append({'pixel_center':pixel,'first_opaque':first,'first_cluster':cluster,'opaque_hits':opaque,'alpha_geometry_hits':alpha})
 require(not alpha_candidates,'alpha geometry projected into ROI; require real alpha policy before classifying')
 # All charted positions are prediction only; retain exact source IDs, not raster ID claims.
 selected_source={role:sorted({h['source']['source_face0'] for s in samples for h in s['first_cluster'] if h['role']==role}) for role in ('body','garment')}
 result={'scope':('ACTUAL EXPORTED CPU GEOMETRY/CAMERA ray correspondence; paired source-color screenshot needed for rendered attribution; not GPU object ID.' if args.actual_frame_sha256 else 'ANALYTICAL SOURCE CORRESPONDENCE CANDIDATES ONLY: prior76 actual displayed CPU geometry + new saved rear camera; ordinary screenshot UI2.00 is not new bone/camera parity or GPU ownership.'),'inputs':{'frame':{'path':str(args.frame),'sha256':digest(args.frame)},'work':{'path':str(args.work),'sha256':digest(args.work)},'photo':{'path':str(args.photo),'sha256':digest(args.photo)},'helper_sha256':digest(Path(__file__))},'roi_xyxy':ROI,'pixel_centers':400,'camera':c,'camera_origin_world':cam[3],'subcamera_assumption':{'full_size':[81920,39040],'size':[81920,46080],'offset':[0,0],'canvas':[1280,720],'new_raw_readback':bool(args.actual_frame_sha256)},'body_mask_policy':'Source body quads omitted if any ID>=13380 OR all four IDs in unchanged garment delete_verts; exact resulting displayed triangle multiset checked.','topology':topology,'controls_pass':controls_count,'opaque_candidate_triangles':candidates,'alpha_candidates':alpha_candidates,'first_hit_counts':[{'role':r,'render_triangle0':t,'source_face0':f,'pixel_count':n} for (r,t,f),n in sorted(first_counts.items())],'source_faces_first_at_fixed_samples':selected_source,'body_first_pixel_centers':body_first,'samples':samples,'visible_notch_attribution':'Source-color actual screenshots require independent review; CPU ray first hits alone are not GPU object ID.'}
 (args.out/'mapping.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 # Reproducible vector-only overlay references unchanged actual ordinary JPEG.
 image_uri=args.photo.as_uri(); lines=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">',f'<image href="{image_uri}" width="1280" height="720"/>']
 for row in candidates:
  color='#ff9e25' if row['role']=='body' else '#00edff';ps=row['screen_points'];points=' '.join(f'{p[0]:.3f},{p[1]:.3f}' for p in ps)
  lines.append(f'<polygon points="{points}" fill="none" stroke="{color}" stroke-width=".8" opacity=".7"/>')
 for pixel in body_first:lines.append(f'<rect x="{pixel[0]-.5}" y="{pixel[1]-.5}" width="1" height="1" fill="#ff365c" opacity=".65"/>')
 lines += ['<rect x="330" y="185" width="20" height="20" fill="none" stroke="#ff365c" stroke-width="1"/>',f'<rect x="10" y="10" width="1160" height="26" fill="#111"/><text x="18" y="28" fill="white" font-size="13" font-family="monospace">{("ACTUAL CPU geometry + camera" if args.actual_frame_sha256 else "ANALYTICAL old CPU + saved rear camera")} | cyan cloth | orange body | red body-first pixel centers | NOT GPU IDs</text>','</svg>']
 (args.out/'overlay.svg').write_text('\n'.join(lines)+'\n')
 if args.fail_on_body_first and body_first:
  print('ANALYTICAL EXPOSED BODY: '+str(len(body_first))+' fixed ROI pixel centers; exit3 is geometric symptom, not GPU proof',file=sys.stderr)
 print(json.dumps({'topology':{k:{a:v for a,v in t.items() if a!='removed_source_face0'} for k,t in topology.items()},'ROI_candidates':len(candidates),'alpha_candidates':len(alpha_candidates),'first_hit_counts':result['first_hit_counts'],'body_first_pixel_centers':body_first,'controls':controls_count},indent=2))
 return 3 if args.fail_on_body_first and body_first else 0

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--frame',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--photo',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--actual-frame-sha256');p.add_argument('--actual-request-id');p.add_argument('--fail-on-body-first',action='store_true')
 try:sys.exit(run(p.parse_args()))
 except (ValueError,KeyError,TypeError) as error:print('FAIL:',error,file=sys.stderr);sys.exit(2)
