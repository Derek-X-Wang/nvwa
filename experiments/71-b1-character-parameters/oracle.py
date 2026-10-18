"""Independent raw-source rest cage and actual full-positive LBS arithmetic.
No production imports, renderer, fit implementation or generated expectation.
"""
import hashlib
import json
import math
from pathlib import Path

CAGE=19158
TOLERANCE_M=1e-6  # Preserve the existing fitted/display correspondence limit.
EXP=Path(__file__).resolve().parent

def require(ok,message):
    if not ok:raise ValueError(message)

def finite(value):return type(value) in (int,float) and math.isfinite(value)

def vector(value,size,label):
    require(isinstance(value,list) and len(value)==size and all(finite(x) for x in value),label+' malformed/nonfinite')

def rows(value,size,count,label):
    require(isinstance(value,list) and len(value)==count and count>0,label+' missing/count mismatch')
    for row in value:vector(row,size,label)

def source_text(path,item):
    data=path.read_bytes();require(hashlib.sha256(data).hexdigest()==item['sha256'],'raw source identity mismatch: '+item['file']);return data.decode('utf-8')

class Oracle:
    def __init__(self,inputs=EXP/'inputs'):
        manifest=json.loads((inputs/'oracle-sources.json').read_text());raw=inputs/'raw'
        self.base=[]
        for line in source_text(raw/manifest['base']['file'],manifest['base']).splitlines():
            f=line.split()
            if f and f[0]=='v':
                require(len(f)==4,'raw base vertex shape');p=[float(x)*0.1 for x in f[1:]];vector(p,3,'raw base');self.base.append(p)
        require(len(self.base)==CAGE,'exact19158 original source vertices required')
        self.targets={}
        for parameter,pair in manifest['parameters'].items():
            self.targets[parameter]={}
            for sign,item in pair.items():
                delta={}
                for line in source_text(raw/item['file'],item).splitlines():
                    f=line.split()
                    if not f or f[0].startswith('#'):continue
                    require(len(f)==4,'raw sparse row shape');index=int(f[0]);require(0<=index<CAGE and index not in delta,'duplicate/out-of-range raw sparse source ID')
                    value=[float(x)*0.1 for x in f[1:]];vector(value,3,'raw delta');delta[index]=value
                require(bool(delta),'empty raw target');self.targets[parameter][sign]=delta
        require(len(self.targets)==8 and all(set(p)=={'decr','incr'} for p in self.targets.values()),'exact16 raw targets required')
    def expected(self,parameters):
        require(set(parameters)==set(self.targets),'recipe parameter identity mismatch')
        result=[p.copy() for p in self.base]
        for name,pair in self.targets.items():
            value=parameters[name];require(finite(value) and -1<=value<=1,'recipe outside existing signed range')
            if value==0:continue
            for index,delta in pair['decr' if value<0 else 'incr'].items():
                for axis in range(3):result[index][axis]+=abs(value)*delta[axis]
        return result
    def rest_error(self,body,parameters):
        actual=body['rest_positions'];ids=body['source_ids'];rows(actual,3,len(ids),'actual body rest');require(len(ids)==len(actual),'rest/source ID mismatch')
        cage={};duplicate_error=0.
        for source,point in zip(ids,actual):
            require(type(source) is int and 0<=source<CAGE,'invalid actual source ID')
            if source in cage:duplicate_error=max(duplicate_error,max(abs(a-b) for a,b in zip(cage[source],point)))
            else:cage[source]=point
        require(set(cage)==set(range(CAGE)),'incomplete19158 helper cage coverage')
        require(duplicate_error<=TOLERANCE_M,'duplicate source render vertices disagree')
        expected=self.expected(parameters)
        error=max(abs(cage[i][axis]-expected[i][axis]) for i in range(CAGE) for axis in range(3))
        require(error<=TOLERANCE_M,'raw base+16target rest cage mismatch: '+str(error))
        return {'source_vertices':CAGE,'max_component_error_m':error,'duplicate_max_component_error_m':duplicate_error,'tolerance_m':TOLERANCE_M,'scope':'independent original raw sparse-delta sum times0.1; actual full source coverage; no production math called'}

def full_positive_lbs(part,bones):
    require(isinstance(bones,list) and len(bones)==53 and len({b['name'] for b in bones})==53,'complete53 unique observed bones required')
    matrices=[]
    for bone in bones:vector(bone['skin'],16,'observed bone skin');matrices.append(bone['skin'])
    rest,actual,influences=part['rest_positions'],part['positions'],part['full_joint_influences'];count=len(rest)
    rows(rest,3,count,'part rest');rows(actual,3,count,'actual upload');require(isinstance(influences,list) and len(influences)==count,'full positive influence coverage missing')
    maximum=0.;max_count=0
    for point,uploaded,row in zip(rest,actual,influences):
        require(isinstance(row,list) and row,'empty actual influence row');seen=set();total=0.
        for pair in row:
            require(isinstance(pair,list) and len(pair)==2,'influence pair malformed');joint,weight=pair
            require(type(joint) is int and 0<=joint<53 and joint not in seen and finite(weight) and weight>0,'nonpositive/duplicate/invalid actual influence')
            seen.add(joint);total+=weight
        require(math.isfinite(total) and total>0,'invalid full influence sum');max_count=max(max_count,len(row))
        expected=[0.,0.,0.]
        # Column-major actual skin matrices already include producer skeleton space.
        # Normalize every positive influence. Do not add model_to_world or display.
        for joint,weight in row:
            matrix=matrices[joint];weight/=total
            for axis in range(3):expected[axis]+=weight*(matrix[axis]*point[0]+matrix[4+axis]*point[1]+matrix[8+axis]*point[2]+matrix[12+axis])
        maximum=max(maximum,max(abs(a-b) for a,b in zip(expected,uploaded)))
    require(maximum<=TOLERANCE_M,'independent full-positive LBS/upload mismatch: '+str(maximum))
    return {'vertices':count,'max_positive_influences':max_count,'max_component_error_m':maximum,'tolerance_m':TOLERANCE_M,'scope':'independent scalar normalized all-positive LBS from observed rest/rows/53 skin matrices; no second transform'}
