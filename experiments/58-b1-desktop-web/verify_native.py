#!/usr/bin/env python3
"""Actual viewer headless boundary, explicit admission and independent f64 LBS."""
import argparse,hashlib,importlib.util,json,math,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
spec=importlib.util.spec_from_file_location('viewer_frame_parity',ROOT/'compare_frames.py');strict=importlib.util.module_from_spec(spec);spec.loader.exec_module(strict)
require=strict.require

def fresh_environment(binary,assets,output,state=None,omit=False):
    env=os.environ.copy()
    for key in ['B1_COMMAND_FILE','B1_OMIT_TARGET','B1_INITIAL_STATE','B1_HEADLESS_STOP_FILE']:
        env.pop(key,None)
    env.update(B1_HEADLESS='1',B1_FRAME_FILE=str(output),B1_ASSET_ROOT=str(assets))
    if state is not None:env['B1_INITIAL_STATE']=json.dumps(state,allow_nan=False)
    if omit:env['B1_OMIT_TARGET']='1'
    return env

def one_run(binary,assets,out,name,state=None,omit=False):
    output=out/(name+'.json');log=out/(name+'.log');start=time.monotonic()
    result=subprocess.run([str(binary)],env=fresh_environment(binary,assets,output,state,omit),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=150,cwd=out)
    log.write_text(result.stdout)
    report=json.loads(output.read_text()) if output.exists() else None
    return result.returncode,report,time.monotonic()-start

def check_report(report,state,assets,bones):
    require(isinstance(report,dict) and report.get('phase')==4 and not report.get('error'),'viewer did not produce an error-free ready report')
    require(report.get('state')==state and report['frame']['state']==state,'outer/embedded selected state mismatch')
    require(report.get('graphical_path_attached') is False,'headless verifier must not claim graphics')
    return strict.admit(report['frame'],assets,bones)

def independent(frame):
    maximum=0.;count=0
    for part in frame['parts'].values():
        full=part.get('full_joint_influences') if frame['state']['backend']=='full-weight-cpu' else None
        for i,(position,rest) in enumerate(zip(part['positions'],part['rest_positions'])):
            row=full[i] if full is not None else list(zip(part['joint_indices'][i],part['joint_weights'][i]))
            total=sum(weight for _,weight in row) if full is not None else 1.
            require(math.isfinite(total) and total>0,'invalid selected influence sum')
            expected=[sum(weight/total*sum(part['bones'][joint]['skin'][4*j+axis]*(rest[j] if j<3 else 1.) for j in range(4)) for joint,weight in row) for axis in range(3)]
            maximum=max(maximum,max(abs(a-b) for a,b in zip(position,expected)));count+=1
    require(maximum<=1e-5,'independent actual-candidate LBS arithmetic mismatch')
    return maximum,count

def live_commands(binary,assets,out,state):
    report_path=out/'live-report.json';command_path=out/'live-command.json';stop_path=out/'live-stop';log_path=out/'live.log'
    env=fresh_environment(binary,assets,report_path,state);env.update(B1_COMMAND_FILE=str(command_path),B1_HEADLESS_STOP_FILE=str(stop_path))
    stream=log_path.open('x');process=subprocess.Popen([str(binary)],env=env,cwd=out,stdout=stream,stderr=subprocess.STDOUT)
    def wait_report(predicate):
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            require(process.poll() is None,'live headless viewer exited before command acceptance')
            if report_path.exists():
                report=json.loads(report_path.read_text())
                if predicate(report):return report
            time.sleep(.05)
        raise ValueError('live viewer command/report timeout')
    def send(command):
        temporary=command_path.with_suffix('.tmp');temporary.write_text(json.dumps(command,allow_nan=False));temporary.replace(command_path)
    try:
        initial=wait_report(lambda report:report.get('phase')==4 and not report.get('error'))
        send({'action':'select','camera_yaw':-20})
        camera=wait_report(lambda report:report.get('state',{}).get('camera_yaw')==-20 and report.get('frame',{}).get('state',{}).get('camera_yaw')==-20)
        require(camera['frame']['sequence']==initial['frame']['sequence'] and camera['frame']['parts']==initial['frame']['parts'],'camera-only command reran/changed actual skin frame')
        (out/'camera-only.json').write_text(json.dumps(camera,allow_nan=False))
        accepted=camera['state'];invalid=dict(accepted,unexpected_field=True)
        send({'action':'import','state':invalid})
        rejected=wait_report(lambda report:bool(report.get('error')))
        require(rejected['state']==accepted and rejected['frame']['state']==accepted and rejected['frame']['parts']==initial['frame']['parts'],'invalid import changed active state/character frame')
        (out/'invalid-import.json').write_text(json.dumps(rejected,allow_nan=False))
        restored=dict(accepted,camera_yaw=45.)
        send({'action':'import','state':restored})
        recovered=wait_report(lambda report:not report.get('error') and report.get('state')==restored and report.get('frame',{}).get('state')==restored)
        require(recovered['frame']['sequence']==initial['frame']['sequence'] and recovered['frame']['parts']==initial['frame']['parts'],'camera-only valid restore changed skin frame')
        (out/'live-restored.json').write_text(json.dumps(recovered,allow_nan=False))
        stop_path.write_text('requested completion\n');code=process.wait(timeout=10);require(code==0,'live verifier viewer exited nonzero')
        return {'camera_only_outer_and_frame_state_atomic':True,'camera_only_skin_sequence_unchanged':True,'invalid_schema_import_preserved_actual_state_and_frame':True,'valid_import_cleared_error':True,'process_exit':code}
    finally:
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        stream.close()

def fatal_commands(binary,assets,out):
    report_path=out/'fatal-report.json';command_path=out/'fatal-command.json';stop_path=out/'fatal-stop';log_path=out/'fatal.log'
    env=fresh_environment(binary,assets,report_path,omit=True)
    env.update(B1_COMMAND_FILE=str(command_path),B1_HEADLESS_STOP_FILE=str(stop_path))
    stream=log_path.open('x');process=subprocess.Popen([str(binary)],env=env,cwd=out,stdout=stream,stderr=subprocess.STDOUT)
    def wait_report(predicate):
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            require(process.poll() is None,'fatal-boundary viewer exited before rejection checks')
            if report_path.exists():
                report=json.loads(report_path.read_text())
                if predicate(report):return report
            time.sleep(.05)
        raise ValueError('fatal command rejection/report timeout')
    try:
        initial=wait_report(lambda report:report.get('phase')==255 and report.get('fatal_reload_required') is True)
        require(initial.get('frame') is None and 'Explicit target missing' in initial.get('error',''),'missing-target fatal admission failed')
        commands=[{'action':'import','state':dict(initial['state'],recipe='combined',pose='combined',backend='full-weight-cpu',camera_yaw=25.)},{'action':'select','camera_yaw':45.},{'action':'select','recipe':'body-positive','pose':'elbow','backend':'full-weight-cpu'}]
        for count,command in enumerate(commands,1):
            temporary=command_path.with_suffix('.tmp');temporary.write_text(json.dumps(command,allow_nan=False));temporary.replace(command_path)
            rejected=wait_report(lambda report:report.get('rejected_commands')==count)
            require(all(rejected[key]==initial[key] for key in ('phase','error','status','state','frame')) and rejected.get('fatal_reload_required') is True,'fatal command changed original error/state/frame')
            (out/('fatal-rejected-'+str(count)+'.json')).write_text(json.dumps(rejected,allow_nan=False))
        stop_path.write_text('fatal rejection checks complete\n');code=process.wait(timeout=10);require(code!=0,'fatal viewer reported successful exit')
        return {'valid_import_rejected':True,'camera_command_rejected':True,'recipe_pose_backend_command_rejected':True,'first_error_state_frame_preserved':True,'commands_acknowledged':len(commands),'process_exit':code}
    finally:
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        stream.close()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path);parser.add_argument('--binary',type=Path,default=ROOT/'target/debug/b1-desktop-web');parser.add_argument('--asset-root',type=Path,default=REPO/'.work/b1-pose-viewer/site/assets');args=parser.parse_args()
    binary=args.binary.absolute();assets=args.asset_root.absolute();require(binary.is_file(),'viewer binary missing')
    expected_assets,bones=strict.expectations(assets)
    out=args.out.absolute() if args.out else REPO/'.work/b1-pose-viewer'/('native-check-'+str(time.time_ns()))
    require(not out.exists() and not out.is_symlink(),'output already exists; retain original captures')
    for ancestor in out.parents:require(not ancestor.is_symlink(),'output ancestor symlink rejected')
    out.parent.mkdir(parents=True,exist_ok=True);out.mkdir()
    state=dict(format='nvwa-b1-pose-prototype',schema_version=1,recipe='combined',pose='combined',camera_yaw=25.,backend='gpu4')
    rows={};frames={};coverage={};oracles={};roundtrips={}
    for backend,prefix in [('gpu4','gpu4'),('full-weight-cpu','positive-cpu')]:
        selected=dict(state,backend=backend)
        code,report,elapsed=one_run(binary,assets,out,prefix,selected);require(code==0,'actual viewer source execution failed: '+prefix)
        coverage[prefix]=check_report(report,selected,expected_assets,bones);oracles[prefix]=independent(report['frame'])
        code2,restored,elapsed2=one_run(binary,assets,out,prefix+'-restored',report['state']);require(code2==0,'actual viewer JSON restoration failed')
        check_report(restored,selected,expected_assets,bones)
        parity=strict.compare_frames(report['frame'],restored['frame'],assets);roundtrips[prefix]=parity['maximum_component_error']
        frames[prefix]=report;rows[prefix]={'initial_seconds':elapsed,'restored_seconds':elapsed2,'exact_state_restored':True}
    missing_code,missing,missing_elapsed=one_run(binary,assets,out,'omitted-target',omit=True)
    require(missing_code!=0 and isinstance(missing,dict) and missing.get('phase')==255 and missing.get('frame') is None and 'Explicit target missing' in missing.get('error',''),'explicit target omission did not fail visibly with null frame')
    commands=live_commands(binary,assets,out,dict(state,backend='full-weight-cpu'))
    fatal=fatal_commands(binary,assets,out)
    receipt={'schema_version':1,'native_actual_source_headless':True,'native_graphical_executed':False,'wasm_executed':False,'common_manifest_sha256':strict.COMMON,'native_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'binary':str(binary),'asset_root':str(assets),'output':str(out),'coverage_and_vectors':coverage,'independent_cpu_max_component_metres':{key:value[0] for key,value in oracles.items()},'independent_vertices_checked':{key:value[1] for key,value in oracles.items()},'exact_state_restoration':rows,'roundtrip_max_component_errors':roundtrips,'live_command_boundary':commands,'fatal_command_boundary':fatal,'omitted_target':{'exit':missing_code,'error':missing['error'],'seconds':missing_elapsed},'comparator_sha256':hashlib.sha256((ROOT/'compare_frames.py').read_bytes()).hexdigest(),'shared_validator_sha256':hashlib.sha256((ROOT.parent/'57-b1-pose-runtime/validation.py').read_bytes()).hexdigest()}
    (out/'native-runtime.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n');print(json.dumps(receipt,indent=2));return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,KeyError,TypeError,IndexError,OSError,subprocess.SubprocessError) as error:
        print('VERIFY_NATIVE_REJECTED: '+str(error));raise SystemExit(3)
