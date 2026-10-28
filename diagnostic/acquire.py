"""Two distinct fixed public Git fetches, one shared setup clock; no fallback/retry."""
import time
PROCESS_START_NS=time.monotonic_ns()
import hashlib
import base64
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
REMOTE='https://github.com/Derek-X-Wang/nvwa.git'
REPO='Derek-X-Wang/nvwa'
REF='refs/heads/codex/exp73-ubuntu-base-overlay-once'
BASE_SHA='eb90badc63fd12753224f1691e8a57b3848241e8'
FILES=['.github/workflows/observe.yml', 'README.md', 'diagnostic/ACQUISITION-INVENTORY.json', 'diagnostic/CONTROL-PROVENANCE.json', 'diagnostic/SOURCE-INVENTORY.json', 'diagnostic/acquire.py', 'diagnostic/codec.py', 'diagnostic/complete-ledger.json', 'diagnostic/export.py', 'diagnostic/plan.json', 'diagnostic/run_once.py', 'source/experiments/73-high-poly-eyes/README.md', 'source/experiments/73-high-poly-eyes/frozen_context.py', 'source/experiments/73-high-poly-eyes/source_gate.py', 'source/experiments/73-high-poly-eyes/test_frozen_inputs.py', 'source/experiments/73-high-poly-eyes/test_prepare.py']
PHASE='bootstrap'
GIT_EVENTS=[]
LIVE=None
LAUNCHING=False
FINALIZING=False
PENDING=set()
GLOBAL_END_NS=None
GROUP_END_NS=None
LOG=None
READ_INDEX=0

class AcquisitionAbort(Exception): pass

def interrupted(signum,frame):
    PENDING.add(signum)
    if not LAUNCHING and not FINALIZING:
        raise AcquisitionAbort('catchable acquisition interruption')

def git_environment():
    # No inherited token, proxy, Git-config injection, credential helper or user
    # hook/config. Changes are process-local; machine configuration is untouched.
    return {'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8',
            'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_SYSTEM':'/dev/null',
            'GIT_CONFIG_GLOBAL':'/dev/null','GIT_TERMINAL_PROMPT':'0',
            'GIT_ASKPASS':'/bin/false','SSH_ASKPASS':'/bin/false',
            'GIT_TEMPLATE_DIR':str(Path(os.environ['RUNNER_TEMP'])/'exp73-empty-template')}

def git_command(*args):
    return ['/usr/bin/git','-c','credential.helper=','-c','core.hooksPath=/dev/null',
            '-c','protocol.file.allow=never','-c','protocol.ext.allow=never',*args]

def remaining_ns(cleanup=False):
    end=min(GLOBAL_END_NS,GROUP_END_NS)
    return end-time.monotonic_ns()-(0 if cleanup else 2000000000)

def group_exists():
    if LIVE is None: return False
    try: os.killpg(LIVE.pid,0);return True
    except ProcessLookupError: return False

def kill_group(sig):
    if LIVE is not None:
        try: os.killpg(LIVE.pid,sig)
        except ProcessLookupError: pass

def cleanup_owned():
    global FINALIZING
    FINALIZING=True
    try:
        if group_exists():
            kill_group(signal.SIGTERM)
            grace=min(time.monotonic_ns()+500000000,min(GLOBAL_END_NS,GROUP_END_NS)-500000000)
            while group_exists() and time.monotonic_ns()<grace:
                LIVE.poll();time.sleep(.01)
            if group_exists(): kill_group(signal.SIGKILL)
        if LIVE is not None:
            seconds=remaining_ns(True)/1e9
            if seconds<=0:
                if LIVE.poll() is None: raise AcquisitionAbort('cleanup deadline; owned process exit unknown')
            else: LIVE.wait(timeout=seconds)
        if group_exists(): raise AcquisitionAbort('owned Git process group remains')
    finally: FINALIZING=False

def run_git(label,*args):
    global LIVE,LAUNCHING
    if PENDING or remaining_ns()<=0: raise AcquisitionAbort('shared setup work deadline or interruption')
    label=PHASE+'-'+label
    out=LOG/(label+'.stdout');err=LOG/(label+'.stderr')
    row={'phase':PHASE,'label':label,'argv':git_command(*args),'start_monotonic':time.monotonic()}
    code=None
    try:
        with out.open('xb') as stdout,err.open('xb') as stderr:
            LAUNCHING=True
            try:
                LIVE=subprocess.Popen(git_command(*args),env=git_environment(),stdout=stdout,stderr=stderr,start_new_session=True)
                row.update(pid=LIVE.pid,pgid=LIVE.pid)
            finally: LAUNCHING=False
            if PENDING: raise AcquisitionAbort('interrupted during launch; handle retained')
            seconds=remaining_ns()/1e9
            if seconds<=0: raise AcquisitionAbort('Git launch exhausted shared setup work allowance')
            code=LIVE.wait(timeout=seconds)
        if code!=0: raise AcquisitionAbort('Git operation failed: '+label)
        if group_exists(): raise AcquisitionAbort('Git descendants remain after command exit')
    finally:
        cleanup_owned()
        row.update(returncode=LIVE.returncode if LIVE is not None else None,
                   end_monotonic=time.monotonic(),owned_group_absent=not group_exists())
        LIVE=None
        for stream,path in (('stdout',out),('stderr',err)):
            if path.exists():
                raw=path.read_bytes();row[stream+'_sha256']=hashlib.sha256(raw).hexdigest()
        GIT_EVENTS.append(row)
    if PENDING: raise AcquisitionAbort('interrupted during owned cleanup; no continuation')
    raw=out.read_bytes()
    if len(raw)>1048576 or err.stat().st_size>1048576: raise AcquisitionAbort('Git diagnostic output exceeds ceiling')
    return raw.decode('utf-8').strip()

def setup_path(): return Path(os.environ['RUNNER_TEMP'])/'exp73-setup.json'

def begin_group(name,origin_ns):
    global GLOBAL_END_NS,GROUP_END_NS,LOG
    if GLOBAL_END_NS is not None: raise AcquisitionAbort('shared setup clock cannot reset')
    GLOBAL_END_NS=origin_ns+120000000000
    GROUP_END_NS=GLOBAL_END_NS
    if remaining_ns()<=0: raise AcquisitionAbort('no acquisition/cleanup allowance remains')
    signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGALRM,interrupted)
    signal.setitimer(signal.ITIMER_REAL,max(.001,remaining_ns()/1e9))
    LOG=Path(os.environ['RUNNER_TEMP'])/('exp73-'+name)
    LOG.mkdir() # Exclusive attempt barrier, never reset/retry.
    empty=Path(git_environment()['GIT_TEMPLATE_DIR'])
    empty.mkdir(exist_ok=True)
    if any(empty.iterdir()): raise AcquisitionAbort('Git template directory not empty')
    version=run_git('version','--version')
    match=re.fullmatch(r'git version (\d+)\.(\d+)(?:\.[0-9]+)?(?:[ .].*)?',version)
    if not match or tuple(map(int,match.groups()))<(2,28): raise AcquisitionAbort('Git>=2.28 required')
    return version

def materialize(name,sha,names):
    target=Path(os.environ['GITHUB_WORKSPACE'])/name
    if target.exists() or target.is_symlink(): raise AcquisitionAbort('fresh absent destination required')
    patterns=[]
    for path in sorted(names):
        if Path(path).is_absolute() or '..' in Path(path).parts or any(x in path for x in '*?[]!\\\r\n'):
            raise AcquisitionAbort('nonliteral sparse path')
        patterns.append('/'+path)
    run_git('init','init','--quiet',str(target))
    run_git('remote','-C',str(target),'remote','add','origin',REMOTE)
    for index,(key,value) in enumerate((('remote.origin.promisor','true'),('remote.origin.partialclonefilter','blob:none'),('core.sparseCheckout','true'),('core.sparseCheckoutCone','false'))):
        run_git('config-'+str(index),'-C',str(target),'config','--local',key,value)
    sparse=target/'.git/info/sparse-checkout';sparse.parent.mkdir(exist_ok=True)
    sparse.write_text('\n'.join(patterns)+'\n')
    # One explicit fetch for this distinct fixed repository/commit purpose. Lazy blobs
    # remain disclosed; no retry, branch/tag fetch, REST or archive fallback.
    run_git('fetch','-C',str(target),'fetch','--quiet','--no-tags','--depth=1','--filter=blob:none','origin',sha)
    run_git('checkout','-C',str(target),'checkout','--quiet','--detach','--no-recurse-submodules','FETCH_HEAD')
    if run_git('head','-C',str(target),'rev-parse','HEAD')!=sha: raise AcquisitionAbort('checkout HEAD mismatch')
    run_git('tree-clean','-C',str(target),'diff','--exit-code','HEAD','--')
    actual=set()
    for path in target.rglob('*'):
        rel=path.relative_to(target).as_posix()
        if rel=='.git' or rel.startswith('.git/'): continue
        if path.is_symlink(): raise AcquisitionAbort('materialized symlink')
        if path.is_file(): actual.add(rel)
    if actual!=set(names) or sparse.read_text()!='\n'.join(patterns)+'\n': raise AcquisitionAbort('materialized file set/sparse state mismatch')
    if remaining_ns()<=0: raise AcquisitionAbort('materialization exceeded shared/group work deadline')
    return target


def check_work():
    if PENDING or remaining_ns()<=0: raise AcquisitionAbort('shared setup120 work allowance exhausted')


def materialized_files(root):
    actual=set()
    if root.is_symlink() or not root.is_dir(): raise AcquisitionAbort('materialized root absent or symlink')
    for path in root.rglob('*'):
        rel=path.relative_to(root).as_posix()
        if rel=='.git' or rel.startswith('.git/'): continue
        if path.is_symlink(): raise AcquisitionAbort('materialized symlink: '+rel)
        if path.is_file(): actual.add(rel)
    return actual


def file_record(path):
    raw=path.read_bytes()
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def compose_sources(base_root,tool_root,source_files,base_paths,overlay_paths,budget):
    """Production-called finite composition; tests call this exact function."""
    base_paths=set(base_paths);overlay_paths=set(overlay_paths)
    if base_paths & overlay_paths: raise AcquisitionAbort('base/overlay path overlap')
    if base_paths | overlay_paths != set(source_files): raise AcquisitionAbort('source partition incomplete or extra')
    if materialized_files(base_root)!=base_paths: raise AcquisitionAbort('base materialized file set mismatch')
    destination=tool_root/'source'
    if materialized_files(destination)!=overlay_paths: raise AcquisitionAbort('overlay materialized file set mismatch')
    overlay_records={}
    for name in sorted(overlay_paths):
        budget();record=file_record(destination/name)
        if record!=source_files[name]: raise AcquisitionAbort('overlay bytes mismatch: '+name)
        overlay_records[name]=record
    base_records={}
    for name in sorted(base_paths):
        budget();raw=(base_root/name).read_bytes()
        record={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        if record!=source_files[name]: raise AcquisitionAbort('base bytes mismatch: '+name)
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as output: output.write(raw)
        base_records[name]=record
    budget()
    if materialized_files(destination)!=set(source_files): raise AcquisitionAbort('final source path set mismatch')
    return {'base_files':base_records,'overlay_files':overlay_records,
            'base_count':len(base_records),'overlay_count':len(overlay_records),'source_count':len(source_files)}


def bootstrap(inventory_sha256,queue_expires_epoch):
    global PHASE
    expected={'GITHUB_REPOSITORY':REPO,'GITHUB_EVENT_NAME':'push','GITHUB_REF':REF,
              'GITHUB_REF_TYPE':'branch','GITHUB_RUN_ATTEMPT':'1'}
    if any(os.environ.get(k)!=v for k,v in expected.items()): raise AcquisitionAbort('event/repository/ref/attempt mismatch')
    if (sys.implementation.name!='cpython' or sys.version_info[:3]!=(3,12,3)
        or sys.platform!='linux' or platform.machine()!='x86_64' or sys.flags.optimize
        or not sys.dont_write_bytecode or Path(sys.executable).resolve()!=Path('/usr/bin/python3').resolve()
        or sys.getprofile() is not None or sys.gettrace() is not None):
        raise AcquisitionAbort('requires preinstalled /usr/bin/python3 CPython3.12.3 Linux x64 normal -B')
    if (os.environ.get('ImageOS')!='ubuntu24' or os.environ.get('RUNNER_OS')!='Linux'
        or os.environ.get('RUNNER_ARCH')!='X64' or not os.environ.get('ImageVersion')):
        raise AcquisitionAbort('standard Ubuntu24 x64 runner image identity mismatch')
    os_release=Path('/etc/os-release').read_text()
    if 'ID=ubuntu' not in os_release or 'VERSION_ID="24.04"' not in os_release:
        raise AcquisitionAbort('requires standard Ubuntu24.04')
    if any(os.environ.get(k) for k in ('PYTHONPATH','PYTHONHOME','PYTHONOPTIMIZE')):
        raise AcquisitionAbort('ambient Python injection')
    event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text());sha=os.environ['GITHUB_SHA']
    if (not re.fullmatch('[0-9a-f]{40}',sha) or event.get('deleted') is not False
        or event.get('created') is not True or event.get('after')!=sha
        or event.get('repository',{}).get('full_name')!=REPO):
        raise AcquisitionAbort('new branch push identity mismatch')
    if time.time()>queue_expires_epoch: raise AcquisitionAbort('frozen queue admission expired')
    origin=PROCESS_START_NS
    version=begin_group('base-overlay-acquisition',origin)
    PHASE='tooling'
    target=materialize('tooling',sha,FILES)
    inventory_raw=(target/'diagnostic/ACQUISITION-INVENTORY.json').read_bytes()
    if hashlib.sha256(inventory_raw).hexdigest()!=inventory_sha256: raise AcquisitionAbort('acquisition inventory pin mismatch')
    inventory=json.loads(inventory_raw)
    if (inventory['route']!='explicit-public-git-base-overlay-v1' or inventory['base_commit']!=BASE_SHA
        or inventory['publication_paths']!=FILES or len(FILES)!=16):
        raise AcquisitionAbort('fixed route/publication/base identity mismatch')
    publication_files={}
    for name in FILES:
        check_work();record=file_record(target/name)
        if name not in ('.github/workflows/observe.yml','diagnostic/ACQUISITION-INVENTORY.json') and record!=inventory['files'][name]:
            raise AcquisitionAbort('published tooling/overlay bytes mismatch: '+name)
        publication_files[name]=record
    source=json.loads((target/'diagnostic/SOURCE-INVENTORY.json').read_text())
    base_paths=inventory['base_source_paths'];overlays=inventory['overlay_source_paths']
    if (source['count']!=782 or len(source['files'])!=782 or len(base_paths)!=777 or len(overlays)!=5
        or len(set(base_paths))!=777 or len(set(overlays))!=5
        or set(overlays)!=set(source['candidate_files_sha256'])
        or set(base_paths)&set(overlays) or set(base_paths)|set(overlays)!=set(source['files'])
        or set(FILES)!=({'source/'+n for n in overlays}|{n for n in inventory['all_acquired_paths'] if not n.startswith('source/')})):
        raise AcquisitionAbort('fixed16/777/5/782 partition mismatch')
    repositories={'tooling':{'commit':sha,'paths':FILES,'owned_groups_absent':not group_exists()}}
    PHASE='base'
    base=materialize('source-base',BASE_SHA,base_paths)
    repositories['base']={'commit':BASE_SHA,'paths':base_paths,'owned_groups_absent':not group_exists()}
    composition=compose_sources(base,target,source['files'],base_paths,overlays,check_work)
    actual={}
    if materialized_files(target)!=set(inventory['all_acquired_paths']): raise AcquisitionAbort('final793 materialization file set mismatch')
    if set(inventory['files'])|{'.github/workflows/observe.yml','diagnostic/ACQUISITION-INVENTORY.json'}!=set(inventory['all_acquired_paths']):
        raise AcquisitionAbort('final manifest coverage mismatch')
    for name in sorted(inventory['all_acquired_paths']):
        check_work();record=file_record(target/name)
        if name in inventory['files'] and record!=inventory['files'][name]: raise AcquisitionAbort('final materialized bytes mismatch: '+name)
        actual[name]=record
    if len(actual)!=793: raise AcquisitionAbort('final793 path count mismatch')
    binary=Path('/usr/bin/python3').resolve()
    record={'job_start_monotonic':origin/1e9,'acquisition_finish_monotonic':time.monotonic(),
            'setup_elapsed_seconds':(time.monotonic_ns()-origin)/1e9,
            'queue_expires_epoch':queue_expires_epoch,'admission_epoch':time.time(),
            'identity':{k:os.environ[k] for k in ('GITHUB_REPOSITORY','GITHUB_SHA','GITHUB_REF','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT')},
            'route':'explicit-public-git-base-overlay-v1','git_version':version,
            'python_executable':'/usr/bin/python3','python_resolved':str(binary),
            'python_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
            'python_version':sys.version,'python_version_info':list(sys.version_info[:3]),
            'uname':list(platform.uname()),'os_release':os_release,
            'image':{k:os.environ.get(k) for k in ('ImageOS','ImageVersion','RUNNER_OS','RUNNER_ARCH')},
            'acquisition_inventory_sha256':inventory_sha256,'acquired_files':actual,
            'publication_files':publication_files,'repositories':repositories,'composition':composition,
            'owned_acquisition_group_absent':not group_exists(),
            'candidate_source_files':source['count'],'candidate_source_logical_bytes':source['logical_bytes']}
    check_work()
    if time.time()>queue_expires_epoch: raise AcquisitionAbort('queue admission expired before receipt')
    acquisition_raw={'explicit_fetch_count':2,'repository_commits':{'tooling':sha,'base':BASE_SHA},
                     'all_owned_groups_absent':not group_exists(),'commands':GIT_EVENTS,
                     'streams':{path.name:{'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                                          'base64':base64.b64encode(path.read_bytes()).decode('ascii')} for path in sorted(LOG.iterdir())}}
    with (target/'diagnostic/ACQUISITION-RAW.json').open('x') as out:
        json.dump(acquisition_raw,out,indent=2,sort_keys=True);out.write('\n')
    with (target/'diagnostic/SETUP.json').open('x') as out:
        json.dump(record,out,indent=2,sort_keys=True);out.write('\n')
    check_work()
    signal.setitimer(signal.ITIMER_REAL,0)
