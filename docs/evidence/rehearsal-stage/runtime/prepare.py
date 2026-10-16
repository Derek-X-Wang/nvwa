import argparse,copy,hashlib,json,subprocess
from pathlib import Path
parser=argparse.ArgumentParser(description='Exercise real offline CLI stage persistence and make private graphical acceptance Works.')
parser.add_argument('--cli',type=Path,required=True)
args=parser.parse_args()
root=Path(__file__).resolve().parents[4]; out=root/'.work/rehearsal-acceptance'; out.mkdir(parents=True,exist_ok=True); cli=args.cli.resolve()
receipts=[]
def require(ok,msg):
 if not ok: raise RuntimeError(msg)
def run(*args,expected=0):
 p=subprocess.run([str(cli),*map(str,args)],capture_output=True,text=True)
 receipts.append({'args':[str(x.relative_to(root)) if isinstance(x,Path) and x.is_relative_to(root) else str(x) for x in args], 'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
 require(p.returncode==expected,'CLI unexpected exit '+str(args)); return json.loads(p.stdout) if p.stdout else None
def write(path,data): path.write_text(json.dumps(data,indent=2)+'\n')
legacy=root/'examples/m1-sequence.nvwa.json'; original=json.loads(legacy.read_text()); digest=hashlib.sha256(legacy.read_bytes()).hexdigest()
cap=run('describe-capabilities',legacy); migrated=run('inspect',legacy)
require(cap['cli_contract']['set_stage']['profiles']['high']['contact_shadows'] is False,'high optional contact disabled')
require(migrated['schema_version']==2,'schema upgrade'); require(migrated['revision']==original['revision'],'migration revision')
for key in ['character','timeline','profile']: require(migrated[key]==original[key],'migration preserves '+key)
stage=copy.deepcopy(cap['stage']); require(stage==migrated['stage'],'discovery agrees')
# Every variant is produced through the real shared command and CLI persistence path.
variants={}
for name,quality in [('white-low','low'),('white-balanced','balanced'),('white-high','high'),('black-high','high'),('detail-high','high')]:
 s=copy.deepcopy(stage); s['quality']=quality
 if name.startswith('black'):
  s['background_color_srgb']=[.008,.011,.018];s['floor']['color_srgb']=[.035,.045,.065]
  s['key_light'].update(illuminance_lux=12000.,color_srgb=[1.,.92,.8],azimuth_degrees=-42.,elevation_degrees=38.)
  s['fill_light'].update(illuminance_lux=4500.,color_srgb=[.65,.8,1.],azimuth_degrees=115.,elevation_degrees=35.)
  s['ambient']={'brightness':95.,'color_srgb':[.8,.88,1.]}
 if name.startswith('detail'): s['camera']={'azimuth_degrees':8.,'elevation_degrees':3.,'distance':1.25,'target_height':1.65,'fov_degrees':30.}
 commands=[{'command_id':name+'-stage','expected_revision':original['revision'],'command':{'type':'set_stage','stage':s}}]
 cp=out/(name+'.commands.json'); wp=out/(name+'.nvwa.json'); write(cp,commands)
 run('apply',legacy,cp,wp);run('validate',wp,root/'assets'); actual=run('inspect',wp)
 require(actual['stage']==s,'stage persisted')
 for key in ['character','timeline','profile']: require(actual[key]==original[key],'stage preserves '+key)
 variants[name]=wp
# One stage command and undo/redo return exact content, while revisions remain monotonic.
cmd=json.loads((out/'black-high.commands.json').read_text())
cmd += [{'command_id':'stage-undo','expected_revision':original['revision']+1,'command':{'type':'undo'}},{'command_id':'stage-redo','expected_revision':original['revision']+2,'command':{'type':'redo'}}]
write(out/'history.commands.json',cmd);run('apply',legacy,out/'history.commands.json',out/'history.nvwa.json')
history=run('inspect',out/'history.nvwa.json'); black=run('inspect',variants['black-high'])
require(history['stage']==black['stage'] and history['revision']==original['revision']+3,'stage history')
run('save',out/'history.nvwa.json',out/'saved.nvwa.json');require((out/'history.nvwa.json').read_bytes()==(out/'saved.nvwa.json').read_bytes(),'save roundtrip')
# An invalid stage must leave an existing output untouched.
bad=copy.deepcopy(cmd[:1]);bad[0]['command']['stage']['camera']['distance']=0.
write(out/'invalid.commands.json',bad); before=(out/'saved.nvwa.json').read_bytes()
run('apply',legacy,out/'invalid.commands.json',out/'saved.nvwa.json',expected=1)
require((out/'saved.nvwa.json').read_bytes()==before,'failed stage preserves output')
require(hashlib.sha256(legacy.read_bytes()).hexdigest()==digest,'legacy file untouched')
write(out/'cli-receipts.json',{'status':'PASS','scope':'actual offline CLI, five stage variants, strict legacy upgrade, undo-redo, save and invalid-output preservation','receipts':receipts,'cli_sha256':hashlib.sha256(cli.read_bytes()).hexdigest()})
print('PASS: five real CLI stage variants, migration, history, save and failed-output preservation')
