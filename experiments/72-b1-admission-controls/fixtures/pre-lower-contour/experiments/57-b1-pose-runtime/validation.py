"""Admission checks shared by full local and sampled CI gates; never use assert."""
import math

def require(ok,message):
 if not ok:raise ValueError(message)
def matrix(values):
 require(isinstance(values,list) and len(values)==16 and all(isinstance(x,(int,float)) and math.isfinite(x) for x in values),'invalid matrix dimensions/finite values')
 return [[values[4*j+i] for j in range(4)] for i in range(4)]
def mul(a,b):return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def maximum(a,b):return max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))
IDENTITY=[[float(i==j) for j in range(4)] for i in range(4)]
def rigid(m):
 require(max(abs(m[3][i]-IDENTITY[3][i]) for i in range(4))<=1e-5,'nonaffine matrix')
 require(max(abs(sum(m[k][i]*m[k][j] for k in range(3))-float(i==j)) for i in range(3) for j in range(3))<=1e-4,'nonrigid/singular matrix')
 det=m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1])-m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0])+m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0])
 require(abs(det-1.)<=1e-4,'noninvertible/improper rigid matrix')
def inverse(m):
 # General inversion keeps the identity checks independent of the rigidity assumption.
 a=[row[:]+eye[:] for row,eye in zip(m,IDENTITY)]
 for col in range(4):
  pivot=max(range(col,4),key=lambda row:abs(a[row][col]));require(abs(a[pivot][col])>1e-10,'singular matrix');a[col],a[pivot]=a[pivot],a[col];scale=a[col][col];a[col]=[v/scale for v in a[col]]
  for row in range(4):
   if row!=col:
    scale=a[row][col];a[row]=[x-scale*y for x,y in zip(a[row],a[col])]
 return [row[4:] for row in a]
def vectors(rows,count,width,label,unit=False,tangent=False):
 require(isinstance(rows,list) and len(rows)==count,label+' count mismatch')
 lengths=[]
 for row in rows:
  require(isinstance(row,list) and len(row)==width and all(isinstance(x,(int,float)) and math.isfinite(x) for x in row),label+' dimensions/finite values')
  if unit or tangent:
   length=math.sqrt(sum(x*x for x in row[:3]));require(length>0 and abs(length-1.)<=1e-4,label+' must be nonzero unit vectors');lengths.append(length)
  if tangent:require(abs(abs(row[3])-1.)<=1e-6,'invalid tangent handedness')
 return min(lengths) if lengths else None

def validate_frame(frame,count,canonical=False):
 require(count>0,'empty mesh')
 vectors(frame['positions'],count,3,'positions');vectors(frame['rest_positions'],count,3,'rest positions')
 normal_min=vectors(frame['normals'],count,3,'normals',unit=True);vectors(frame['rest_normals'],count,3,'rest normals',unit=True);tangent_min=vectors(frame['tangents'],count,4,'tangents',tangent=True)
 bones=frame['bones'];require(isinstance(bones,list) and len(bones)==53 and len({b['name'] for b in bones})==53,'bone coverage mismatch')
 max_identity=0.
 for b in bones:
  matrices={key:matrix(b[key]) for key in ('rest','posed','inverse_bind','local_rest','local_posed','skin')}
  for m in matrices.values():rigid(m)
  rest=matrices['rest'];posed=matrices['posed'];ibm=matrices['inverse_bind'];identity_error=maximum(mul(rest,ibm),IDENTITY);skin_error=maximum(mul(posed,ibm),matrices['skin']);require(identity_error<=1e-5 and skin_error<=1e-5,'rest/inverse-bind or stored skin identity failed');max_identity=max(max_identity,identity_error,skin_error)
  if canonical:
   f=matrix(b['canonical_rest']);p=matrix(b['canonical_posed']);q=matrix(b['frame_gauge'])
   for m in (f,p,q):rigid(m)
   qi=inverse(q);errors=[maximum(mul(rest,qi),f),maximum(mul(posed,qi),p),maximum(mul(posed,ibm),mul(p,inverse(f)))];require(max(errors)<=1e-5,'canonical gauge/physical skin identity failed');max_identity=max(max_identity,*errors)
 if 'model_to_world' in frame:rigid(matrix(frame['model_to_world']))
 return {'passed':True,'present_finite':True,'normal_min_length':normal_min,'tangent_min_length':tangent_min,'max_frame_identity_error':max_identity,'appearance_acceptance':'NOT-RUN'}
