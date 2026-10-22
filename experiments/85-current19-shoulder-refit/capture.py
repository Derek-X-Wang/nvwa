#!/usr/bin/env python3
"""One parent-authorized actual current19 process; preserve rejected bytes too."""
import argparse
import json
import os
import platform
from pathlib import Path
import subprocess
import queue
import threading
import time
import sys
import uuid
import current19 as c
import provenance as p
from geometry_checks import Baseline


def write(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def consume_process(command,env,cwd,out,run_id,timeout_seconds=600):
    """Actual bounded producer/readline/EOF/wait path, also used by lifecycle tests."""
    entries=[];failure=None;events=queue.Queue(maxsize=1);stop=threading.Event()
    started=time.monotonic();deadline=started+timeout_seconds
    with (out/'producer-stderr.log').open('x') as stderr:
        child=subprocess.Popen(command,cwd=cwd,env=env,stdout=subprocess.PIPE,
                               stderr=stderr,text=True,encoding='utf-8')
        def publish(value):
            while not stop.is_set():
                try:events.put(value,timeout=.1);return
                except queue.Full:pass
        def reader():
            try:
                for line in child.stdout:
                    if stop.is_set():return
                    publish(line)
                publish(None)
            except Exception as error:publish(error)
        thread=threading.Thread(target=reader,daemon=True,name='nvwa85-owned-stdout-reader')
        thread.start()
        def lines():
            while True:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise TimeoutError('producer stdout/EOF deadline exceeded')
                try:event=events.get(timeout=remaining)
                except queue.Empty:raise TimeoutError('producer stdout/EOF deadline exceeded')
                if event is None:return
                if isinstance(event,Exception):raise event
                yield event
        try:
            c.collect(lines(),out,run_id,entries)
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('producer process deadline exceeded')
            c.need(child.wait(timeout=remaining)==0,'actual producer failed')
        except Exception as error:failure=str(error)
        finally:
            stop.set()
            if child.poll() is None:child.terminate()
            try:child.wait(timeout=2)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=2)
            thread.join(timeout=2)
            if not thread.is_alive():child.stdout.close()
            else:failure=(failure+'; ' if failure else '')+'owned stdout reader did not exit'
    return {'entries':entries,'producer_exit_code':child.returncode,'failure':failure,
            'producer_pid':child.pid,'reader_exited':not thread.is_alive(),
            'timeout_seconds':timeout_seconds,'elapsed_seconds':time.monotonic()-started}


def run(args):
    c.need(args.binary.is_file() and os.access(args.binary,os.X_OK),'executable producer required')
    c.need(args.asset_root.resolve()==(c.ROOT/'assets').resolve(),'only frozen checkout assets permitted')
    c.need(not args.out.exists(),'unique capture directory required')
    authorization=c.strict_load(args.authorization.read_bytes())
    c.need(authorization['status']=='FROZEN_FOR_CURRENT19_CAPTURE' and
           authorization['cohort_kind']==c.KIND,'parent capture GO missing')
    before=p.source_inventory(args.binary)
    build_raw=args.build_receipt.read_bytes();build=c.strict_load(build_raw)
    c.need(authorization['build_receipt_sha256']==c.digest(build_raw) and
           authorization['source_inventory_sha256']==before['inventory_sha256'] and
           authorization['binary']==before['binary'],'frozen capture inputs differ')
    run_id='nvwa85-current19-'+str(uuid.uuid4())
    env=os.environ.copy()
    env.update(B1_85_ASSET_ROOT=str(args.asset_root.resolve()),B1_85_RUN_ID=run_id)
    identity={'schema_version':1,'cohort_kind':c.KIND,'run_id':run_id,'capture_run_id':run_id,
              'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),
              'source_dirty_paths':subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=c.ROOT,text=True).splitlines(),
              'host':{'system':platform.system(),'machine':platform.machine(),'node':platform.node()},
              'target':'aarch64-apple-darwin','toolchain':{tool:subprocess.check_output([tool,'--version'],cwd=c.ROOT,text=True).strip() for tool in ('rustc','cargo')},
              'python':sys.version,'command':[str(args.binary.resolve())],
              'collector_argv':[sys.executable,*sys.argv],
              'capture_environment':{'B1_85_ASSET_ROOT':env['B1_85_ASSET_ROOT'],'B1_85_RUN_ID':run_id},
              'binary':before['binary'],'source_inventory_sha256':before['inventory_sha256'],
              'build_run_id':build['build_run_id'],'build_command':build['command'],
              'build_config':build['build_config'],'compiled_source_sha256':build['source_files_sha256'],
              'build_receipt_sha256':c.digest(build_raw),
              'capture_authorization_sha256':c.digest(args.authorization.read_bytes()),
              'graphics':'NOT-RUN'}
    p.check_build(build,before,identity)
    validator=Baseline()
    at_run=p.source_inventory(args.binary)
    c.need(before==at_run,'source/binary changed before producer launch')
    args.out.mkdir(parents=True)
    write(args.out/'source-before.json',before);write(args.out/'source-at-run.json',at_run)
    (args.out/'build-receipt.json').write_bytes(build_raw)
    identity['source_before_sha256']=c.digest((args.out/'source-before.json').read_bytes())
    write(args.out/'identity.json',identity)
    (args.out/'capture-authorization.json').write_bytes(args.authorization.read_bytes())
    producer=consume_process([str(args.binary.resolve())],env,c.ROOT,args.out,run_id)
    entries=producer['entries'];failure=producer['failure']
    if failure is None:
        # The complete actual structural19+completion is retained before any geometry audit.
        raw_records=((args.out/'raw'/f'{i:02d}.json').read_bytes() for i in range(20))
        records=(record for _,_,record in c.replay_stream(raw_records,run_id))
        audit=c.audit_geometry(records,validator)
        if audit['failures']:failure='current19 geometry audit rejected '+str(len(audit['failures']))+' slots'
    else:audit={'status':'NOT-RUN_STRUCTURAL_CAPTURE_REJECTED','results':[],'failures':[],
                'candidate_read':False,'quality_acceptance':False}
    write(args.out/'geometry-audit.json',audit)
    after=p.source_inventory(args.binary);write(args.out/'source-after.json',after)
    if before!=after:failure='source/binary changed during capture'+(': '+failure if failure else '')
    result={'schema_version':1,'cohort_kind':c.KIND,'run_id':run_id,
            'status':'PASS_CURRENT19_BASELINE' if failure is None else 'REJECT_CURRENT19_BASELINE',
            'source_inventory_sha256':before['inventory_sha256'],'source_unchanged':before==at_run==after,
            'historical_raw_identity_reused':False,'historical_exact18':'NOT-RUN_MISSING18',
            'quality_acceptance':False,'cases':entries,'failure':failure,'graphics':'NOT-RUN',
            'producer_exit_code':producer['producer_exit_code'],
            'producer_lifecycle':{k:v for k,v in producer.items() if k not in ('entries','failure')},
            'retained_raw_records':[p.receipt_row(args.out,str(path.relative_to(args.out)))
                                    for path in sorted((args.out/'raw').glob('*.json'))],
            'receipts':{key:p.receipt_row(args.out,name) for key,name in p.RECEIPTS.items()}}
    write(args.out/'manifest.json',result)
    if failure is None:
        # Same readback seam required by future author/scoring. Stored checks alone do not admit.
        try:
            records=p.authenticate(args.out,c.digest((args.out/'manifest.json').read_bytes()),before['inventory_sha256'])
            c.need(len(records)==19,'readback omitted current sample')
        except (ValueError,KeyError,TypeError,OSError,IndexError) as error:
            failure='admission readback failed: '+str(error)
            result.update(status='REJECT_CURRENT19_BASELINE',failure=failure)
            write(args.out/'manifest.json',result)
    print(json.dumps({'status':result['status'],'cases':len(entries),'failure':failure}))
    return 0 if failure is None else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('binary','build-receipt','asset-root','authorization','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    try:sys.exit(run(parser.parse_args()))
    except (ValueError,KeyError,TypeError,OSError,IndexError) as error:
        print(json.dumps({'status':'REJECT_CURRENT19_BASELINE','failure':str(error)}))
        sys.exit(2)
