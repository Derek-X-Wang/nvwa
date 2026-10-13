"""Actual CLI/process lifecycle controls; never launches Nvwa or GPU work."""
import json
import os
from pathlib import Path
import sys
import subprocess
from launch_owned_native import PACKET, absent, memory, monotonic_ns, run_owned

helper=PACKET/'proc-memory'
folder=PACKET/(sys.argv[1] if len(sys.argv)>1 else 'launcher-controls')
folder.mkdir(exist_ok=False)
results=[]
interpreter=subprocess.check_output(['/bin/ps','-p',str(os.getpid()),'-o','comm='],text=True).strip()
assert Path(interpreter).is_file(), interpreter
for name,code,deadline,expected in [
    ('empty','pass',2,0),
    ('failed','raise SystemExit(7)',2,7),
    ('large-output','import sys; sys.stdout.write("A"*4194304); sys.stderr.write("B"*4194304)',3,0),
    ('stubborn-hang','import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(10)',0.4,-9),
]:
    result=run_owned([interpreter,'-c',code],{},folder/name,helper,deadline)
    assert result['status']=='EXIT-VERIFIED' and result['exit_code']==expected, result
    assert absent(result['pid']) is True and not result['error'],result
    if name=='large-output':
        assert (folder/name/'stdout.log').stat().st_size==4194304
        assert (folder/name/'stderr.log').stat().st_size==4194304
    if name=='stubborn-hang':
        assert [row['signal'] for row in result['observations'] if row['event']=='owned_group_signal']==['TERM','KILL']
        assert result['elapsed_seconds']<3
    results.append({'name':name,'status':result['status'],'pid':result['pid'],'exit_code':result['exit_code'],'elapsed_seconds':result['elapsed_seconds']})
before=monotonic_ns()
identity=memory(helper,os.getpid())
after=monotonic_ns()
assert before<=identity['sample_begin_ns']<=identity['sample_end_ns']<=after,(before,identity,after)
results.append({'name':'actual-CLOCK_MONOTONIC-C-Python-bracket','status':'VERIFIED','before_ns':before,'sample':identity,'after_ns':after})
try:
    memory(helper,os.getpid(),{**identity,'birth_sec':identity['birth_sec']+1})
    raise AssertionError('birth mismatch accepted')
except RuntimeError as exc:
    assert 'expected-birth-mismatch' in str(exc)
results.append({'name':'actual-self-birth-mismatch','status':'REJECTED'})
packet={'status':'VERIFIED CPU CLI controls; native/GPU NOT-RUN','results':results,'background_helpers_remaining':False}
(folder/'result.json').write_text(json.dumps(packet,indent=2)+'\n')
print(json.dumps(packet,indent=2))
