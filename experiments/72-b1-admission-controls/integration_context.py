"""Exact offline integration candidate, NOT independent review or numeric acceptance.
No manifest generation is exposed here. All expectations are immutable literal pins.
"""
from pathlib import Path
import hashlib,json
NAME='input-context-chest-v14-integration-candidate-v1.json'
SHA='5ae81c52bea6fbde072b84a52f6511905aa4bd9d12e192c821b26426a344293a'
ID='b1-chest-v10-with-v14-cli-level1-integration-candidate-v1'
EXP=Path(__file__).resolve().parent

def need(ok,message):
 if not ok:raise ValueError('integration candidate: '+message)
def file(root,name):
 p=Path(root)
 need(not Path(name).is_absolute() and '..' not in Path(name).parts,'unsafe path')
 for part in Path(name).parts:
  p=p/part;need(not p.is_symlink(),'symlink '+name)
 need(p.is_file(),'missing '+name);return p
def pin(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def has(root):
 return (root/'assets/characters/mpfb-b1-v10').exists() and (root/'assets/characters/mpfb-b1-v14').exists()
def predecessors72(api,pins):
 arm=api.cpu_source_context(pins)
 for fn in ['_combined_context','_leg_context','_upper_context','_hip_context','_arm_context']:arm=getattr(api,fn)(api.HERE,arm)
 chest=api._chest_context(api.HERE,arm);main=arm
 for fn in ['_body_reference_context','_hand_context','_shoulder_context','_forearm_context','_upper_arm_context','_level1_context','_cli_level1_context']:main=getattr(api,fn)(api.HERE,main)
 return main,chest

def expected(main,chest,cohort):
 raw=file(EXP,NAME).read_bytes();need(hashlib.sha256(raw).hexdigest()==SHA,'manifest identity mismatch')
 value=json.loads(raw);need(value['context']==ID and value['status']=='OFFLINE_CANDIDATE_PENDING_INDEPENDENT_REVIEW','identity/status')
 meta=value['cohorts'][str(cohort)]
 need((main[0],chest[0],len(main[1]),len(chest[1]))==(meta['main_context'],meta['pr_context'],meta['main_count'],meta['pr_count']),'predecessor identity/count')
 conflicts=sorted(p for p in set(main[1])&set(chest[1]) if main[1][p]!=chest[1][p])
 need(conflicts==meta['conflicting_predecessor_paths'],'predecessor overlap mismatch')
 # Authenticate retained bytes of BOTH lineages, never reverse changes from current worktree.
 for key,item in value['fixtures'].items():
  tag,name=key.split('/',1);old=main[1] if tag=='main' else chest[1]
  need(name in old and item['pin']==old[name],'fixture differs from predecessor pin '+key)
  need(pin(file(EXP,item['fixture']).read_bytes())==old[name],'fixture bytes mismatch '+key)
 tree=EXP/'fixtures/pre-chest-v14-integration';paths=list(tree.rglob('*'))
 need(not tree.is_symlink() and all(not p.is_symlink() for p in paths),'fixture tree symlink')
 need({p.relative_to(EXP).as_posix() for p in paths if p.is_file()}=={i['fixture'] for i in value['fixtures'].values()},'fixture inventory mismatch')
 out=dict(chest[1]);out.update(main[1]) # explicit main preference only for already-frozen overlapping files
 overrides=value['candidate_overrides']
 need(set(overrides)==set(value['changed_paths']) and set(overrides)<=set(out),'explicit changed-path mismatch')
 need(all(out[p]!=v for p,v in overrides.items()),'non-change claimed as override')
 out.update(overrides);need(len(out)==meta['union_count'],'union count')
 # Every displaced predecessor byte must be retained, including unmodified-main preference.
 for tag,old in [('main',main[1]),('pr',chest[1])]:
  for p,i in old.items():
   if out[p]!=i:need(tag+'/'+p in value['fixtures'],'missing retained predecessor '+tag+'/'+p)
 return ID,out

def verify(root,main,chest,cohort):
 name,out=expected(main,chest,cohort)
 for p,i in out.items():need(pin(file(root,p).read_bytes())==i,'source bytes mismatch '+p)
 for v in range(9,15):
  prefix=f'assets/characters/mpfb-b1-v{v}/';tree=root/prefix;paths=list(tree.rglob('*'))
  need(not tree.is_symlink() and all(not p.is_symlink() for p in paths),'asset symlink')
  need({p.relative_to(root).as_posix() for p in paths if p.is_file()}=={p for p in out if p.startswith(prefix)},'asset inventory mismatch '+prefix)
 return name,out

# Test-fixture materialization only. No production admission path uses this lookup.
def historical_input(name, expected_pin, root):
 p=Path(root)/name
 if p.is_file() and pin(file(root,name).read_bytes())==expected_pin:return p
 for p in (EXP/'fixtures').rglob(Path(name).name):
  if p.as_posix().endswith('/'+name) and p.is_file():
   relative=p.relative_to(EXP).as_posix()
   if pin(file(EXP,relative).read_bytes())==expected_pin:return p
 if name=='crates/nvwa-cli/src/motion_query.rs':
  relative='pre-travel-query/'+name
  p=EXP/relative
  if p.is_file() and pin(file(EXP,relative).read_bytes())==expected_pin:return p
 raise ValueError('no authenticated historical fixture for '+name)

def current_test_identity(api, root, previous_id):
 # Never a permissive match: tests must still assert one exact root identity.
 return ID if has(root) else previous_id
