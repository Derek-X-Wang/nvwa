#!/usr/bin/env python3
"""Diagnostic contrast only: endpoint/roll algorithm, never candidate input."""
import json
from pathlib import Path
import numpy as np
from compare import C,matrix,sha
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent.parent

def bone_point(spec,helpers,groups):
 strategy=spec['strategy']
 if strategy=='MEAN':return np.mean(helpers[spec['vertex_indices'][:2]],axis=0)
 if strategy=='VERTEX':return helpers[spec['vertex_index']]
 if strategy=='CUBE':
  start,end=groups[spec['cube_name']][0];return np.mean(helpers[start:end+1],axis=0)
 raise ValueError(strategy)

def main():
 old=ROOT.parent/'55-source-character-runtime';rig=json.loads((old/'data/rig.game_engine.json').read_text());groups=json.loads((old/'data/vertex_groups.json').read_text());reports=[]
 freeze=ROOT.parent/'56-b1-pose-reference/reference/frozen/manifest.json';manifest=json.loads(freeze.read_text())
 for entry in manifest['cases']:
  if entry['pose_id']!='neutral':continue
  candidate_path=ROOT/'results/padding-fixed1'/entry['recipe_id']/'neutral.json';candidate=json.loads(candidate_path.read_text());refpath=REPO/entry['path'];assert sha(refpath)==entry['sha256'];ref=json.loads(refpath.read_text());refbones={b['name']:b for b in ref['bones']}
  helpers=np.array(json.loads((old/'results/B1-run1'/(entry['recipe_id']+'.json')).read_text())['helper_positions_raw_basis'])/10
  rows=[]
  for bone in candidate['parts']['body']['frame']['bones']:
   spec=rig[bone['name']];head=bone_point(spec['head'],helpers,groups);tail=bone_point(spec['tail'],helpers,groups);direction=C[:3,:3]@(tail-head);direction/=np.linalg.norm(direction)
   cross=np.cross([0.,1.,0.],direction);dot=direction[1];x,y,z=cross;K=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
   assert dot>-0.999999
   align=np.eye(3)+K+K@K/(1+dot);roll=spec.get('roll',0);c=np.cos(roll);s=np.sin(roll);rollmat=np.array([[c,0,s],[0,1,0],[-s,0,c]])
   predicted=np.eye(4);predicted[:3,:3]=align@rollmat;predicted[:3,3]=C[:3,:3]@head
   expected=np.array(refbones[bone['name']]['matrix_local']);actual=C@matrix(bone['rest']);rows.append({'bone':bone['name'],'actual_rest_max_component':float(np.abs(actual-expected).max()),'endpoint_roll_prediction_max_component':float(np.abs(predicted-expected).max()),'head_from_candidate_helpers':head.tolist(),'tail_from_candidate_helpers':tail.tolist()})
  rows.sort(key=lambda row:row['actual_rest_max_component'],reverse=True);reports.append({'recipe_id':entry['recipe_id'],'candidate_sha256':sha(candidate_path),'reference_sha256':sha(refpath),'predicted_all_bones_max_component':max(row['endpoint_roll_prediction_max_component'] for row in rows),'worst_actual_bones':rows[:5]})
 result={'status':'diagnosis_only_not_candidate_output','source_policy':'fitted heads with unchanged base reference rotations','alternative':'existing get_bone_transform endpoint+roll algorithm on morphed helpers','cases':reports};(ROOT/'evidence/rest-frame-diagnosis.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
