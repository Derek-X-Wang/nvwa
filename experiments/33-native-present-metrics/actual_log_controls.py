"""CPU verifier mutations of actual rows; no app launch or GPU execution."""
import json
from pathlib import Path
from reconcile_native import reconcile, rows

packet=Path(__file__).resolve().parents[2]/'.work/m11-perf/native'
controls=[]
for case,pid in [('diagnostic-1',70636),('diagnostic-warm',72779)]:
    text=(packet/'runs'/case/'stderr.log').read_text()
    data=rows(text)
    gpu=next(x for x in data if x['event']=='command_completed' and x['valid_completed_gpu_span'])
    display=next(x for x in data if x['event']=='drawable_presented_callback' and x['valid_presented_time'])
    actual='\n'.join('NVWA_METAL_PROBE '+json.dumps(x) for x in data)
    reconcile(text,pid)
    for name,row,change in [
        ('GPU_completed_status_raw_mismatch',gpu,{'status_raw':5}),
        ('GPU_zero_start_raw_mismatch',gpu,{'gpu_start_host_seconds':0}),
        ('display_zero_time_raw_mismatch',display,{'presented_host_seconds':0}),
        ('display_calibration_reversed',display,{'callback_monotonic_after_ns':1}),
        ('mixed_PID',gpu,{'pid':pid+1}),
    ]:
        target='NVWA_METAL_PROBE '+json.dumps(row)
        mutated='NVWA_METAL_PROBE '+json.dumps({**row,**change})
        assert target in actual
        try:
            reconcile(actual.replace(target,mutated,1),pid)
            raise RuntimeError('mutant accepted: '+name)
        except AssertionError as error:
            controls.append({'case':case,'control':name,'mutant':'REJECTED','reason':str(error),
                             'scope':'CPU mutation of actual raw row, not GPU execution'})
        reconcile(actual,pid)
        controls[-1]['restored_actual_raw']='ACCEPTED'
result={'status':'VERIFIED10actual-log verifier mutation red/restored-green controls','controls':controls}
(packet/'actual-log-red-green-controls.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'controls':len(controls),'status':'VERIFIED'}))
