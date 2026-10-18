#!/usr/bin/env python3
"""Source-grounded scalar reference. Standard library only; configure an explicit repo."""
import hashlib,json,math
from pathlib import Path
REPO=None
ASSETS=None
STEMS={'eyes':'eyes/low-poly/low-poly','hair':'hair/short04/short04'}
TOL=1e-5 # Existing arithmetic guard, not an appearance-quality threshold.
def configure(repo):
 global REPO,ASSETS
 REPO=Path(repo).resolve(strict=True)
 if not REPO.is_dir():raise ValueError('--repo must name the repository directory')
 ASSETS=REPO/'experiments/62-b1-appearance-preview/assets'
def need(ok,msg):
 if not ok: raise ValueError(msg)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def dump(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')

def finite(v):return all(type(x) in (int,float) and math.isfinite(x) for x in v)

def err(a,b):
 need(len(a)==len(b),'array length mismatch')
 return max((abs(x-y) for p,q in zip(a,b) for x,y in zip(p,q)),default=0)

def point(m,p):return [math.fsum(m[k*4+a]*p[k] for k in range(3))+m[12+a] for a in range(3)]

def mapping(path):
 rows=[];rules={};active=False
 for line in path.read_text().splitlines():
  f=line.split()
  if not f or f[0].startswith('#'):continue
  if f[:2]==['verts','0']:active=True;continue
  if f[0]=='delete_verts':raise ValueError('new accessory mask unsupported')
  if not active:
   if f[0] in ('x_scale','y_scale','z_scale'):rules['xyz'.index(f[0][0])]=(int(f[1]),int(f[2]),float(f[3])*.1)
  elif f[0]!='material':
   need(len(f) in (1,9),'mapping row')
   if len(f)==1: rows.append(([int(f[0])],[1.],[0.,0.,0.]))
   else:
    c=list(map(float,f[3:6]));s=math.fsum(c);need(abs(s)>2**-23,'zero coefficients')
    rows.append((list(map(int,f[:3])),[x/s for x in c],[float(x)*.1 for x in f[6:9]]))
 need(set(rules)=={0,1,2},'scale coverage');return rows,rules

def obj(path):
 uv=[];faces=[];positions=[];normals=0
 for line in path.read_text().splitlines():
  f=line.split()
  if not f:continue
  if f[0]=='v':positions.append([float(x)*.1 for x in f[1:]])
  elif f[0]=='vn':normals+=1
  elif f[0]=='vt':uv.append([float(f[1]),1-float(f[2])])
  elif f[0]=='f':faces.append([tuple(int(x)-1 for x in t.split('/')) for t in f[1:]])
 need(all(len(c)==2 for f in faces for c in f),'pinned OBJ must be v/vt corners')
 need(set(c[0] for f in faces for c in f)==set(range(len(positions))),'OBJ source coverage')
 triangles=[(f[0],f[i-1],f[i]) for f in faces for i in range(2,len(f))]
 corners=list(dict.fromkeys(c for t in triangles for c in t))
 return {'source_count':len(positions),'uvs':uv,'corners':corners,'triangles':triangles,'source_faces':len(faces),'normal_count':normals}

def cage_of(body):
 ids=body['source_ids'];rest=body['rest_positions'];need(len(ids)==len(rest),'cage coverage');cage={}
 for sid,p in zip(ids,rest):
  need(type(sid) is int and 0<=sid<19158 and len(p)==3 and finite(p),'cage ID/nonfinite')
  need(sid not in cage or cage[sid]==p,'conflicting duplicate cage source')
  cage[sid]=p
 need(set(cage)==set(range(19158)),'cage incomplete');return cage

def compute(snapshot,name,clamp=False,offset_factor=1.):
 body=next(p for p in snapshot['parts'] if p['name']=='body');cage=cage_of(body)
 rows,rules=mapping(ASSETS/(STEMS[name]+'.mhclo'));mesh=obj(ASSETS/(STEMS[name]+'.obj'))
 need(len(rows)==mesh['source_count'],'MHCLO/OBJ mismatch')
 names=[b['name'] for b in snapshot['bones']];need(len(set(names))==len(names)==53,'53 stable bones')
 weights=json.loads((REPO/'assets/characters/mpfb-b1-v1/weights.game_engine.json').read_bytes())['weights'];need(set(weights)==set(names),'weight name set')
 bybone={n:dict(weights[n]) for n in names}
 scales=[(cage[rules[a][1]][a]-cage[rules[a][0]][a])/rules[a][2] for a in range(3)]
 rest=[];influences=[];posed=[]
 for helpers,coeff,offset in rows:
  if clamp:
   coeff=[max(0,c) for c in coeff];s=math.fsum(coeff);coeff=[c/s for c in coeff]
  need(all(h in cage for h in helpers),'source ID mapping')
  r=[math.fsum(c*cage[h][a] for h,c in zip(helpers,coeff))+scales[a]*offset[a]*offset_factor for a in range(3)];rest.append(r)
  raw=[(j,math.fsum(bybone[n].get(h,0)*c for h,c in zip(helpers,coeff) if bybone[n].get(h,0)>0)) for j,n in enumerate(names)]
  positive=[(j,w) for j,w in raw if w>0];s=math.fsum(w for j,w in positive);need(s>0,'no positive final weights');row=[[j,w/s] for j,w in positive];influences.append(row)
  transformed=[(point(snapshot['bones'][j]['skin'],r),w) for j,w in row]
  posed.append([math.fsum(p[a]*w for p,w in transformed) for a in range(3)])
 return {'rest_positions':rest,'positions':posed,'full_joint_influences':influences,'display_transform':body['display_transform'],'stage_positions':[point(body['display_transform'],p) for p in posed],'scales':scales,'obj':mesh}
