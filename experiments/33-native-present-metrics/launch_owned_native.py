"""Root-executed bounded launcher; private files, exact birth, no GUI control."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / '.work/m11-perf/native'

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def monotonic_ns(): return time.clock_gettime_ns(time.CLOCK_MONOTONIC)
def stamp(event, **fields):
    return {'event':event,'CLOCK_MONOTONIC_ns':monotonic_ns(),
            'wall_UTC_ISO':datetime.now(timezone.utc).isoformat(),**fields}
def write(path, value): path.write_text(json.dumps(value,indent=2)+'\n')
def memory(helper, pid, expected=None):
    argv=[str(helper),str(pid)]
    if expected is not None: argv += [str(expected['birth_sec']),str(expected['birth_usec'])]
    run=subprocess.run(argv,capture_output=True,text=True,timeout=1)
    if run.returncode != 0: raise RuntimeError('libproc rejected identity: '+run.stderr.strip())
    value=json.loads(run.stdout)
    if value['pid'] != pid: raise RuntimeError('libproc PID mismatch')
    return value
def members(pgid):
    # comm is executable identity only; no user arguments/environment are read.
    result=subprocess.run(['/bin/ps','-axo','pid=,ppid=,pgid=,comm='],capture_output=True,text=True,timeout=1)
    if result.returncode: raise RuntimeError('ps group query unavailable')
    found=[]
    for line in result.stdout.splitlines():
        fields=line.split(None,3)
        if len(fields)==4 and int(fields[2])==pgid:
            pid=int(fields[0])
            if os.getpgid(pid)!=pgid or os.getsid(pid)!=pgid: raise RuntimeError('group/session disagreement')
            found.append({'pid':pid,'ppid':int(fields[1]),'pgid':pgid,'binary':fields[3]})
    return found
def absent(pgid):
    try: os.killpg(pgid,0); return False
    except ProcessLookupError: return True
    except OSError: return None
def inventory():
    result=subprocess.run(['/bin/ps','-axo','pid=,ppid=,%cpu=,rss=,comm='],capture_output=True,text=True,timeout=1)
    if result.returncode: return {'status':'UNKNOWN','exit_code':result.returncode}
    rows=[]
    for line in result.stdout.splitlines():
        f=line.split(None,4)
        if len(f)!=5: continue
        name=Path(f[4]).name
        # Retain only executable basenames, never unrelated paths/arguments.
        if float(f[2])>=50 or re.search(r'cargo|rustc|clang|Chrome|Nvwa|nvwa|Xcode|Instruments',name):
            rows.append({'pid':int(f[0]),'ppid':int(f[1]),'cpu_percent':float(f[2]),'rss_KiB':int(f[3]),'executable_basename':name})
    return {'status':'OBSERVED','rows':rows,'scope':'selected names or CPU>=50; no proof of all GPU contention'}

def run_owned(argv, environment, run_dir, helper, deadline=40):
    run_dir.mkdir(parents=True,exist_ok=False)
    rows=[stamp('before_launch',argv=argv,environment_override_names=sorted(environment),heavy_inventory=inventory())]
    write(run_dir/'launch.json',rows[0])
    child=None; registered={}; status='BLOCKED'; error=None; exit_code=None
    start=time.monotonic(); until=start+deadline
    def register_group():
        child.poll()
        current=members(child.pid)
        if len(current)>8: raise RuntimeError('owned group exceeds bounded8-member inspection')
        for item in current:
            prior=registered.get(item['pid'])
            sample=memory(helper,item['pid'],prior)
            if prior is None:
                if child.returncode is not None: raise RuntimeError('unregistered survivor after leader exit')
                leader=next((m for m in current if m['pid']==child.pid),None)
                if leader is None or leader['ppid']!=os.getpid(): raise RuntimeError('direct child ownership unavailable')
                if Path(leader['binary']).resolve()!=Path(argv[0]).resolve(): raise RuntimeError('direct child executable mismatch')
                registered[item['pid']]={**item,'birth_sec':sample['birth_sec'],'birth_usec':sample['birth_usec']}
            elif item['binary']!=prior['binary']: raise RuntimeError('owned executable identity changed')
        return current
    with (run_dir/'stdout.log').open('x') as stdout, (run_dir/'stderr.log').open('x') as stderr:
        try:
            before=monotonic_ns()
            child=subprocess.Popen(argv,cwd=ROOT,env={**os.environ,**environment},stdin=subprocess.DEVNULL,
                                   stdout=stdout,stderr=stderr,start_new_session=True)
            after=monotonic_ns()
            rows.append(stamp('popen_returned',pid=child.pid,ppid=os.getpid(),pgid=child.pid,
                              launch_before_monotonic_ns=before,launch_after_monotonic_ns=after))
            # Ownership registered before optional inspection. The Popen object
            # pins the direct child until waitpid; no pipe is closed prematurely.
            write(run_dir/'pid.json',rows[-1])
            print('NVWA_LAUNCH_PID '+json.dumps(rows[-1]),flush=True)
            while child.poll() is None and time.monotonic()<until:
                try:
                    register_group()
                    identity=registered.get(child.pid)
                    if identity is not None:
                        sample=memory(helper,child.pid,identity)
                        rows.append(stamp('memory_sample',sample=sample))
                        if not (run_dir/'identity.json').exists(): write(run_dir/'identity.json',identity)
                except Exception as exc:
                    rows.append(stamp('inspection_unknown_guard_continues',error=str(exc)))
                time.sleep(0.2)
        except BaseException as exc:
            error=repr(exc); rows.append(stamp('launch_or_guard_exception',error=error))
        finally:
            if child is not None:
                for sig,label in [(signal.SIGTERM,'TERM'),(signal.SIGKILL,'KILL')]:
                    child.poll()
                    if absent(child.pid) is True: break
                    try:
                        current=register_group()
                        if not current: raise RuntimeError('group exists but identity unknown')
                        # Every member is birth-qualified immediately before a
                        # signal; no signal after an identity disagreement.
                        for member in current: memory(helper,member['pid'],registered[member['pid']])
                        os.killpg(child.pid,sig)
                        rows.append(stamp('owned_group_signal',signal=label,pgid=child.pid,members=current))
                        end=time.monotonic()+1
                        while time.monotonic()<end and absent(child.pid) is not True:
                            child.poll(); time.sleep(0.025)
                    except Exception as exc:
                        error=repr(exc); rows.append(stamp('cleanup_blocked_no_signal',error=error)); break
                child.poll(); exit_code=child.returncode
                status='EXIT-VERIFIED' if exit_code is not None and absent(child.pid) is True else 'BLOCKED'
            rows.append(stamp('after_cleanup',status=status,exit_code=exit_code,heavy_inventory=inventory()))
            result={'status':status,'error':error,'exit_code':exit_code,'pid':child.pid if child else None,
                    'elapsed_seconds':time.monotonic()-start,'deadline_seconds':deadline,
                    'registered_members':list(registered.values()),'observations':rows,
                    'GPU_result':'NOT-VALIDATED by launcher; inspect actual callbacks and pixels separately'}
            write(run_dir/'process-receipt.json',result)
    return result

def verify_prelaunch(variant):
    freeze=json.loads((PACKET/'candidate-freeze.json').read_text())
    for name,digest in freeze['source_inputs_sha256'].items():
        if sha(ROOT/name)!=digest: raise RuntimeError('frozen source changed: '+name)
    if sha(freeze['candidate']['frozen'])!=freeze['candidate']['sha256']: raise RuntimeError('frozen candidate changed')
    if sha(freeze['helper']['path'])!=freeze['helper']['sha256']: raise RuntimeError('proc-memory changed')
    if sha(freeze['baseline']['path'])!=freeze['baseline']['sha256']: raise RuntimeError('baseline changed')
    accepted=json.loads((ROOT/'.work/m11-main-ci/main-runtime-inputs.json').read_text())
    for name,expected in accepted['files'].items():
        path=ROOT/name
        content=os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
        blob=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
        if blob!=expected['git_blob']: raise RuntimeError('accepted product input changed: '+name)
    contract=json.loads((ROOT/'.work/m11-perf/measurement-contract.json').read_text())
    work=Path(contract['scene_input']['frozen'])
    if sha(work)!=contract['scene_input']['sha256']: raise RuntimeError('work input changed')
    bundle=ROOT/'dist/Nvwa.app' if variant=='baseline' else Path(freeze['candidate']['bundle'])
    executable=bundle/'Contents/MacOS/Nvwa'
    wanted=freeze['baseline']['sha256'] if variant=='baseline' else freeze['candidate']['sha256']
    if sha(executable)!=wanted: raise RuntimeError('bundle executable changed')
    for relative,digest in freeze['bundle_assets_sha256'].items():
        if sha(bundle/relative)!=digest: raise RuntimeError('bundle resource changed: '+relative)
    info=plistlib.loads((bundle/'Contents/Info.plist').read_bytes())
    expected_id='dev.nvwa.studio' if variant=='baseline' else 'dev.nvwa.perf.native-diagnostic'
    if info['CFBundleIdentifier']!=expected_id or info['CFBundleExecutable']!='Nvwa': raise RuntimeError('bundle identifier/executable mismatch')
    return {'variant':variant,'bundle':str(bundle),'bundle_id':expected_id,'Info_plist_sha256':sha(bundle/'Contents/Info.plist'),
            'executable':str(executable),'binary_sha256':wanted,'proc_memory':freeze['helper'],
            'work':str(work),'work_sha256':sha(work),'source_freeze_sha256':sha(PACKET/'candidate-freeze.json'),
            'source_inputs_compared':len(freeze['source_inputs_sha256']),'accepted_main_inputs_compared':len(accepted['files']),
            'assets_compared':len(freeze['bundle_assets_sha256'])}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--variant',choices=['baseline','diagnostic'],required=True)
    p.add_argument('--run-name',required=True)
    p.add_argument('--hold-seconds',type=float,default=30)
    p.add_argument('--deadline',type=float,default=40)
    p.add_argument('--preflight-only',action='store_true')
    a=p.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,40}',a.run_name) or not 25<=a.hold_seconds<=35 or not a.hold_seconds+3<=a.deadline<=45: p.error('bounded name; hold25..35 and deadline hold+3..45 required')
    ready=verify_prelaunch(a.variant)
    if a.preflight_only: print(json.dumps(ready,indent=2)); return 0
    runs=PACKET/'runs'; runs.mkdir(exist_ok=True)
    if len(list(runs.glob('*/launch.json')))>=3: raise RuntimeError('native3-run budget exhausted')
    directory=runs/a.run_name
    captures=PACKET/'captures'/a.run_name
    environment={'NVWA_METAL_PROBE':'1' if a.variant=='diagnostic' else '0','NVWA_PROBE_CAPTURE_DIR':str(captures)}
    argv=[ready['executable'],'--work',ready['work'],'--benchmark','--smoke','--smoke-seconds',str(a.hold_seconds),'--timeout',str(a.deadline-2),'--capture',str(captures/'production-final.png')]
    captures.mkdir(parents=True,exist_ok=False)
    write(captures/'prelaunch.json',ready)
    result=run_owned(argv,environment,directory,Path(ready['proc_memory']['path']),a.deadline)
    print('NVWA_LAUNCH_COMPLETE '+json.dumps({k:result[k] for k in ['status','exit_code','pid','elapsed_seconds']}),flush=True)
    return 0 if result['status']=='EXIT-VERIFIED' and result['exit_code']==0 and not result['error'] else 1
if __name__=='__main__': raise SystemExit(main())
