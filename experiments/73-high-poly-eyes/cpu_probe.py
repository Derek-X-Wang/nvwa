"""Independent stdlib source/cage/full-positive replay. No renderer or asset admission."""
import argparse,hashlib,json,math,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EXP=Path(__file__).resolve().parent
LIMIT=1e-6

def require(ok,message):
    if not ok: raise ValueError(message)
def sha(b):return hashlib.sha256(b).hexdigest()
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def sub(a,b):return [x-y for x,y in zip(a,b)]
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def unit(v):
    n=math.sqrt(dot(v,v));require(n>0 and math.isfinite(n),'finite nonzero normal required');return [x/n for x in v]
def point(m,v):return [sum(m[j*4+i]*v[j] for j in range(3))+m[12+i] for i in range(3)]
def normal(m,v):
    # inverse transpose of the affine3x3, independently derived from column cross products
    a,b,c=[m[j*4:j*4+3] for j in range(3)];d=dot(a,cross(b,c));require(abs(d)>1e-12,'singular bone matrix')
    rows=[cross(b,c),cross(c,a),cross(a,b)]
    return [sum(rows[j][i]*v[j] for j in range(3))/d for i in range(3)]
def mesh(text):
    positions=[];tex=[];pairs=[];lookup={};indices=[];faces=0
    for line in text.splitlines():
        f=line.split()
        if not f or f[0].startswith('#'):continue
        if f[0]=='v':positions.append([float(x) for x in f[1:]])
        elif f[0]=='vn':
            require(len(f)==4 and all(math.isfinite(float(x)) for x in f[1:]),'finite original OBJ normal required')
        elif f[0]=='vt':tex.append([f32(float(f[1])),f32(1-f32(float(f[2])))])
        elif f[0]=='f':
            face=[];faces+=1
            for token in f[1:]:
                p=tuple(int(x)-1 for x in token.split('/'));require(len(p)==2 and 0<=p[0]<len(positions) and 0<=p[1]<len(tex),'OBJ corner outside source')
                if p not in lookup:lookup[p]=len(pairs);pairs.append(p)
                face.append(lookup[p])
            for i in range(1,len(face)-1):indices.extend([face[0],face[i],face[i+1]])
    require(set(p for p,t in pairs)==set(range(len(positions))),'missing source coverage')
    return {'count':len(positions),'faces':faces,'uv_rows':len(tex),'pairs':pairs,'uv':[tex[t] for p,t in pairs],'indices':indices}
def mapping(text,count,unit_scale=.1):
    rows=[];scales={};section=False
    for line in text.splitlines():
        f=line.split()
        if not f or f[0].startswith('#'):continue
        if f==['verts','0']:section=True;continue
        require(f[0]!='delete_verts','body deletion forbidden')
        if f[0] in ['x_scale','y_scale','z_scale']:
            scales['xyz'.index(f[0][0])]=(int(f[1]),int(f[2]),float(f[3])*unit_scale)
        elif section:
            if len(f)==1:ids=[int(f[0])];coeff=[1.];offset=[0.,0.,0.]
            else:
                require(len(f)==9,'unexpected source mapping row');ids=[int(x) for x in f[:3]];coeff=[float(x) for x in f[3:6]];offset=[float(x)*unit_scale for x in f[6:]]
            total=sum(coeff);require(abs(total)>2**-23,'zero coefficient sum')
            rows.append((ids,[c/total for c in coeff],offset))
    require(len(rows)==count and len(scales)==3,'source mapping incomplete')
    require(all(0<=i<19158 for ids,c,o in rows for i in ids),'helper outside domain')
    return rows,scales

def source(which):
    stem=(ROOT/'assets/appearances/mpfb-b1-cc0-v1/eyes/low-poly/low-poly') if which=='a' else EXP/'source/eyes/high-poly/high-poly'
    obj=mesh(stem.with_suffix('.obj').read_text());rows,scales=mapping(stem.with_suffix('.mhclo').read_text(),obj['count']);return obj,rows,scales

def replay(base,which,unit_scale=.1,cap=None,clamp_signed=False):
    obj,rows,scales=source(which)
    if unit_scale!=.1:
        stem=(ROOT/'assets/appearances/mpfb-b1-cc0-v1/eyes/low-poly/low-poly') if which=='a' else EXP/'source/eyes/high-poly/high-poly'
        rows,scales=mapping(stem.with_suffix('.mhclo').read_text(),obj['count'],unit_scale)
    body=next(p for p in base['parts'] if p['name']=='body');cage={}
    for i,p in zip(body['source_ids'],body['rest_positions']):
        require(i not in cage or cage[i]==p,'conflicting cage duplicate');cage[i]=p
    require(set(cage)==set(range(19158)),'complete19158 cage required')
    bones=base['bones'];require(len(bones)==53,'exact53 bones required')
    raw=(ROOT/'assets/characters/mpfb-b1-v1/weights.game_engine.json').read_bytes();require(sha(raw)=='9f4a773e74ce5ba08415b4f30070338e9f75bae5971b5075b10cd6b9caa58473','weight source hash')
    original=json.loads(raw)['weights'];weight_maps=[dict(original[b['name']]) for b in bones]
    scale=[(cage[scales[a][1]][a]-cage[scales[a][0]][a])/scales[a][2] for a in range(3)]
    rest=[];weights=[];negative=0
    for ids,coeff,offset in rows:
        negative+=sum(c<0 for c in coeff)
        if clamp_signed:coeff=[max(c,0) for c in coeff];coeff=[c/sum(coeff) for c in coeff]
        rest.append([sum(cage[i][a]*c for i,c in zip(ids,coeff))+offset[a]*scale[a] for a in range(3)])
        row=[(j,sum(w.get(i,0)*c for i,c in zip(ids,coeff))) for j,w in enumerate(weight_maps)]
        row=[(j,w) for j,w in row if w>0]
        if cap:row=sorted(row,key=lambda p:p[1],reverse=True)[:cap]
        total=sum(w for j,w in row);require(total>0 and math.isfinite(total),'positive aggregate missing');weights.append([(j,w/total) for j,w in row])
    normals=[[0.,0.,0.] for _ in rest];area_min=math.inf
    for k in range(0,len(obj['indices']),3):
        ids=[obj['pairs'][obj['indices'][k+j]][0] for j in range(3)];a,b,c=[rest[i] for i in ids];n=cross(sub(b,a),sub(c,a));area=dot(n,n);require(area>=1e-24,'degenerate fitted triangle');area_min=min(area_min,math.sqrt(area))
        for i in ids:normals[i]=[x+y for x,y in zip(normals[i],n)]
    normals=[unit(n) for n in normals];p=[];n=[]
    for restp,restn,row in zip(rest,normals,weights):
        q=[0.,0.,0.];r=[0.,0.,0.]
        for j,w in row:
            posed=point(bones[j]['skin'],restp);posedn=normal(bones[j]['skin'],restn)
            q=[x+y*w for x,y in zip(q,posed)];r=[x+y*w for x,y in zip(r,posedn)]
        p.append([f32(x) for x in q]);n.append([f32(x) for x in unit(r)])
    return {'positions':[p[i] for i,t in obj['pairs']],'normals':[n[i] for i,t in obj['pairs']],'uv_0':obj['uv'],'indices':obj['indices'],'rest':rest,'weights':weights,'scales':scale,'source_count':obj['count'],'signed_negative_coefficients':negative,'max_positive_influences':max(map(len,weights)),'minimum_triangle_doubled_area_m2':area_min}

def compare(expected,actual):
    errors={}
    for name in ['positions','normals','uv_0']:
        require(len(expected[name])==len(actual[name]),name+' row coverage mismatch')
        errors[name]=max(abs(x-y) for a,b in zip(expected[name],actual[name]) for x,y in zip(a,b));require(errors[name]<=LIMIT,name+' replay differs beyond1e-6')
    require(expected['indices']==actual['indices'],'index mismatch')
    return errors

def probe(path):
    raw=path.read_bytes();e=json.loads(raw);f=e['frame'];base=f.get('full_base',f.get('snapshot'))
    result={'capture_basename':path.name,'bytes':len(raw),'sha256':sha(raw),'sample':base['sample'],'parameters':base['parameters']}
    a=replay(base,'a');b=replay(base,'b');result['a']=summary(a);result['b']=summary(b)
    if 'full_base' in f:
        actual=next(p for p in f['buffers'] if p['role']=='eyes');result['A_actual_production_replay_errors']=compare(a,actual)
    else:result['A_actual_production_replay_errors']='NOT-RUN: retained65 uses an earlier accessory renderer; cage-only replay'
    result['scope']='source/cage CPU replay only; no actual high-poly upload, GPU, visual quality or intended lid-fit evidence'
    return result

def summary(r):
    return {k:r[k] for k in ['source_count','signed_negative_coefficients','max_positive_influences','minimum_triangle_doubled_area_m2','scales']}|{'render_vertices':len(r['positions']),'triangles':len(r['indices'])//3,'minimum_m':[min(p[a] for p in r['positions']) for a in range(3)],'maximum_m':[max(p[a] for p in r['positions']) for a in range(3)]}

def main():
    p=argparse.ArgumentParser();p.add_argument('captures',nargs='+',type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();records=[probe(c) for c in a.captures];a.out.write_text(json.dumps({'records':records,'scope':'bounded CPU only'},indent=2)+'\n')
if __name__=='__main__':main()
