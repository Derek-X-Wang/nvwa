"""Independent small geometry/BVH diagnostics. Open-surface signs are local only."""
import math

def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def add(a,b): return tuple(x+y for x,y in zip(a,b))
def scale(a,s): return tuple(x*s for x in a)
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(a): return math.sqrt(dot(a,a))
def unit(a):
 n=norm(a)
 return scale(a,1/n) if n>1e-15 else (0.,0.,0.)
def closest_segment(p,a,b):
 ab=sub(b,a);d=dot(ab,ab);t=max(0.,min(1.,dot(sub(p,a),ab)/d)) if d else 0.
 return add(a,scale(ab,t))
def closest_triangle(p,a,b,c):
 # Ericson region tests, independently authored implementation; degenerates use edges.
 ab=sub(b,a);ac=sub(c,a)
 if norm(cross(ab,ac))<1e-14:
  q=min((closest_segment(p,a,b),closest_segment(p,b,c),closest_segment(p,c,a)),key=lambda q:dot(sub(p,q),sub(p,q)))
  return q,None
 ap=sub(p,a);d1=dot(ab,ap);d2=dot(ac,ap)
 if d1<=0 and d2<=0:return a,(1.,0.,0.)
 bp=sub(p,b);d3=dot(ab,bp);d4=dot(ac,bp)
 if d3>=0 and d4<=d3:return b,(0.,1.,0.)
 vc=d1*d4-d3*d2
 if vc<=0 and d1>=0 and d3<=0:
  v=d1/(d1-d3);return add(a,scale(ab,v)),(1-v,v,0.)
 cp=sub(p,c);d5=dot(ab,cp);d6=dot(ac,cp)
 if d6>=0 and d5<=d6:return c,(0.,0.,1.)
 vb=d5*d2-d1*d6
 if vb<=0 and d2>=0 and d6<=0:
  w=d2/(d2-d6);return add(a,scale(ac,w)),(1-w,0.,w)
 va=d3*d6-d5*d4
 if va<=0 and d4-d3>=0 and d5-d6>=0:
  w=(d4-d3)/((d4-d3)+(d5-d6));return add(b,scale(sub(c,b),w)),(0.,1-w,w)
 denominator=1/(va+vb+vc);v=vb*denominator;w=vc*denominator
 return add(a,add(scale(ab,v),scale(ac,w))),(1-v-w,v,w)

class BVH:
 def __init__(self,points,triangles,leaf=12):
  self.points=points;self.triangles=triangles
  bounds=[]
  for tri in triangles:
   p=[points[i] for i in tri];bounds.append((tuple(min(v[k] for v in p) for k in range(3)),tuple(max(v[k] for v in p) for k in range(3))))
  def build(ids):
   low=tuple(min(bounds[i][0][k] for i in ids) for k in range(3));high=tuple(max(bounds[i][1][k] for i in ids) for k in range(3))
   if len(ids)<=leaf:return low,high,ids,None
   axis=max(range(3),key=lambda k:high[k]-low[k]);ids.sort(key=lambda i:bounds[i][0][axis]+bounds[i][1][axis]);m=len(ids)//2
   return low,high,build(ids[:m]),build(ids[m:])
  if not triangles:raise ValueError('empty triangle surface')
  self.root=build(list(range(len(triangles))))
 def nearest(self,p):
  best=[math.inf,None,None,None]
  def bound(node):return sum(max(node[0][k]-p[k],0.,p[k]-node[1][k])**2 for k in range(3))
  def visit(node):
   if bound(node)>best[0]:return
   if node[3] is None:
    for i in node[2]:
     tri=self.triangles[i];a,b,c=[self.points[j] for j in tri];q,bary=closest_triangle(p,a,b,c);dist=dot(sub(p,q),sub(p,q))
     if dist<best[0]:best[:]=[dist,i,q,bary]
   else:
    for child in sorted(node[2:],key=bound):visit(child)
  visit(self.root);distance,tid,q,bary=best;a,b,c=[self.points[j] for j in self.triangles[tid]];normal=unit(cross(sub(b,a),sub(c,a)))
  return {'distance':math.sqrt(distance),'triangle':tid,'closest':q,'barycentric':bary,'normal':normal,'local_signed_projection':dot(sub(p,q),normal)}

def surface_queries(points,triangles,probes,probe_ids):
 bvh=BVH(points,triangles);counts={'negative_over_2mm':0,'negative_over_5mm':0};worst=None;mind=math.inf
 for p,pid in zip(probes,probe_ids):
  hit=bvh.nearest(p);signed=hit['local_signed_projection'];mind=min(mind,hit['distance'])
  counts['negative_over_2mm']+=signed<-.002;counts['negative_over_5mm']+=signed<-.005
  if worst is None or signed<worst['local_signed_projection']:worst={**hit,'probe_source_id':pid,'triangle_vertices':triangles[hit['triangle']]}
 return {'queries':len(probes),'min_unsigned_distance':mind,'worst_local_side':worst,**counts,'claim':'local triangle-side descriptors only; open-surface inside/outside and collision quality NOT-RUN'}

def strain(points,rest,triangles):
 normals=[];edges={};area_ratios=[];edge_ratios=[];degenerate=0
 for tid,tri in enumerate(triangles):
  a,b,c=[points[i] for i in tri];ra,rb,rc=[rest[i] for i in tri];n=cross(sub(b,a),sub(c,a));area=norm(n);r=norm(cross(sub(rb,ra),sub(rc,ra)));normals.append(unit(n));degenerate+=area<1e-12
  if r>1e-12:area_ratios.append(area/r)
  for i,j in zip(tri,(tri[1],tri[2],tri[0])):
   edge=tuple(sorted((i,j)));edges.setdefault(edge,[]).append(tid);length=norm(sub(rest[i],rest[j]))
   if length>1e-12:edge_ratios.append(norm(sub(points[i],points[j]))/length)
 angles=[];folds=[]
 for edge,tids in edges.items():
  if len(tids)==2:
   angle=math.degrees(math.acos(max(-1.,min(1.,dot(normals[tids[0]],normals[tids[1]])))));angles.append(angle)
   if angle>150:folds.append({'edge':edge,'triangles':tids,'degrees':angle})
 return {'triangles':len(triangles),'degenerate_triangles':degenerate,'minimum_area_ratio':min(area_ratios,default=None),'maximum_area_ratio':max(area_ratios,default=None),'minimum_edge_ratio':min(edge_ratios,default=None),'maximum_edge_ratio':max(edge_ratios,default=None),'boundary_edges':sum(len(v)==1 for v in edges.values()),'nonmanifold_edges':sum(len(v)>2 for v in edges.values()),'maximum_adjacent_normal_angle_degrees':max(angles,default=None),'fold_candidates_over_150_degrees':len(folds),'first_fold_candidates':folds[:8],'self_intersection':'NOT-RUN; adjacent normal angle is only a fold descriptor'}
