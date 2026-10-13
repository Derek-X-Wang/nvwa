"""Post-run CPU-only summary of the three frozen actual native launches."""
import hashlib
import json
import math
from pathlib import Path
import statistics
import struct
import sys
import time
from reconcile_native import reconcile, rows

ROOT=Path(__file__).resolve().parents[2]
PACKET=ROOT/'.work/m11-perf/native'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def relative(p): return str(p.relative_to(ROOT))
def stats(values):
    ordered=sorted(values)
    return {'count':len(values),'min':min(values),'median':statistics.median(values),
            'p95_nearest_rank':ordered[max(0,math.ceil(.95*len(ordered))-1)],'max':max(values)} if values else None
def elapsed_interval(low,high,launch,allowance_ns=0):
    return [(low-launch['launch_after_monotonic_ns']-allowance_ns)/1e9,
            (high-launch['launch_before_monotonic_ns']+allowance_ns)/1e9]

def main():
    frozen=json.loads((PACKET/'candidate-freeze.json').read_text())
    resolution_ns=time.clock_getres(time.CLOCK_MONOTONIC)*1e9
    summary={'status':'PARTIAL actual native display/GPU/memory; fully cold and stall cause NOT-RUN',
        'root_lifecycle':json.loads((ROOT/'.work/m11-perf/lifecycle-root-readback.json').read_text()),
        'root_lifecycle_sha256':sha(ROOT/'.work/m11-perf/lifecycle-root-readback.json'),
        'candidate_freeze_sha256':sha(PACKET/'candidate-freeze.json'),
        'CLOCK_MONOTONIC_reported_resolution_ns':resolution_ns,
        'clock_limit':'Calibration and launch brackets plus conservative2CLOCK_MONOTONIC ticks+2ns logged-double quantization allowance; not a bound on undocumented driver/CA timestamp accuracy',
        'runs':{},'raw_artifacts_sha256':{}}
    for case in ['baseline-1','diagnostic-1','diagnostic-warm']:
        directory=PACKET/'runs'/case
        receipt=json.loads((directory/'process-receipt.json').read_text())
        launch=json.loads((directory/'pid.json').read_text())
        identity=json.loads((directory/'identity.json').read_text())
        assert receipt['status']=='EXIT-VERIFIED' and receipt['exit_code']==0
        assert receipt['pid']==launch['pid']==identity['pid']
        memory=[x['sample'] for x in receipt['observations'] if x['event']=='memory_sample']
        assert memory and all(x['pid']==identity['pid'] and x['birth_sec']==identity['birth_sec'] and x['birth_usec']==identity['birth_usec'] and x['expected_birth_checked'] for x in memory)
        text=(directory/'stderr.log').read_text(); data=rows(text)
        run={'pid':receipt['pid'],'identity':identity,'exit_status':receipt['status'],'exit_code':receipt['exit_code'],
            'elapsed_wrapper_seconds':receipt['elapsed_seconds'],'launch_CLOCK_MONOTONIC_bracket_ns':[launch['launch_before_monotonic_ns'],launch['launch_after_monotonic_ns']],
            'launch_bracket_width_ns':launch['launch_after_monotonic_ns']-launch['launch_before_monotonic_ns'],
            'variant':'accepted unchanged release' if case=='baseline-1' else 'diagnostic wrapper/local wgpu-hal patch/3readbacks',
            'binary_sha256':frozen['baseline']['sha256'] if case=='baseline-1' else frozen['candidate']['sha256'],
            'memory':{'sample_count':len(memory),'scope':'exact PID/birth snapshots; RSS and footprint overlap; separate kernel reported lifetime maximum; do not add GPU allocation',
                      'sampled_RSS_bytes':stats([x['rss_bytes'] for x in memory]),
                      'sampled_physical_footprint_bytes':stats([x['physical_footprint_bytes'] for x in memory]),
                      'kernel_reported_lifetime_max_physical_footprint_bytes':max(x['kernel_lifetime_max_physical_footprint_bytes'] for x in memory),
                      'first_sample_monotonic_ns':memory[0]['sample_begin_ns'],'last_sample_monotonic_ns':memory[-1]['sample_end_ns']},
            'start_end_inventory':[x for x in receipt['observations'] if x['event'] in ['before_launch','after_cleanup']],
            'production_CPU_cadence':'NOT-RUN: NVWA_EVIDENCE INFO record absent from captured stdout/stderr',
            'captures':{}}
        for p in sorted((PACKET/'captures'/case).glob('*.png')):
            width,height=struct.unpack('>II',p.read_bytes()[16:24])
            tag=p.stem
            callback=next((x for x in data if x['event']=='screenshot_gpu_readback_callback' and x['fields']['tag']==tag),None)
            item={'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'width':width,'height':height,
                  'filesystem_mtime_ns':p.stat().st_mtime_ns,'mtime_scope':'filesystem wall metadata only; not screenshot/display boundary',
                  'callback':callback,'content_observation':'requires supplied root/visual artifact inspection receipt'}
            if callback:
                item['readback_callback_since_external_launch_interval_seconds']=elapsed_interval(callback['monotonic_before_ns'],callback['monotonic_after_ns'],launch,2*resolution_ns)
            run['captures'][tag]=item
        if data:
            rec=reconcile(text,receipt['pid'])
            first=rec['first_observed_valid_drawable']
            displays=[x for x in data if x['event']=='drawable_presented_callback']
            prior=[x for x in displays if x['index']<first['index']]
            assert sorted(x['index'] for x in prior)==list(range(1,first['index']))
            assert all(not x['valid_presented_time'] and x['presented_host_seconds']==0 for x in prior)
            first_interval=first['converted_CLOCK_MONOTONIC_interval_ns']
            run['first_valid_reported_surface_display']={
                'callback':first,'prior_dense_callback_indices_zero_time':[x['index'] for x in sorted(prior,key=lambda x:x['index'])],
                'CLOCK_MONOTONIC_interval_ns':first_interval,
                'since_external_launch_bracket_seconds':elapsed_interval(*first_interval,launch),
                'since_external_launch_interval_with_reported_clock_resolution_allowance_seconds':elapsed_interval(*first_interval,launch,2*resolution_ns+2),
                'scope':'actual Metal drawable reported onscreen time; skipped prior callbacks; no assertion about displayed content',
                'valid_display_callback_count':len(displays)-len(rec['invalid_display_callbacks']),
                'zero_time_display_callback_count':len(rec['invalid_display_callbacks'])}
            gpu=rec['valid_gpu_command_samples']
            run['GPU_command_duration_ms_by_kind']={kind:stats([x['duration_ms'] for x in gpu if x['kind']==kind]) for kind in sorted(set(x['kind'] for x in gpu))}
            run['GPU_samples']={'valid_count':len(gpu),'invalid_count':len(rec['invalid_gpu_command_samples']),
                                'zero_duration_count':sum(x['duration_ms']==0 for x in gpu),
                                'scope':'bounded selected existing completed Metal command buffers, not frame/pass durations; zero durations retained; no sum or frame-latency inference'}
            allocations=[x['metal_device_current_allocated_bytes'] for x in data if 'metal_device_current_allocated_bytes' in x]
            run['Metal_device_current_allocated_bytes']=stats(allocations)
            offsets=[(x['callback_monotonic_before_ns']+x['callback_monotonic_after_ns'])/2-x['ca_host_seconds']*1e9 for x in data if 'callback_monotonic_before_ns' in x]
            run['observed_CA_to_CLOCK_MONOTONIC_midpoint_offset_ns']=stats(offsets)
            run['main_CPU_markers']=[x for x in data if x['event'] in ['before_build_app','after_build_app','first_main_post_update','first_runtime_ready_observation','first_render_system_returned','animation_observation_after_ready_plus_2s','app_run_returned']]
            run['reconciler_output_sha256']=sha(PACKET/(case+'-reconciled.json'))
        else:
            run['first_valid_reported_surface_display']='NOT-RUN accepted baseline has no observer'
            run['GPU_command_duration_ms_by_kind']='NOT-RUN accepted baseline has no observer'
            run['Metal_device_current_allocated_bytes']='NOT-RUN accepted baseline has no observer'
        for p in sorted(directory.glob('*')):
            if p.is_file():summary['raw_artifacts_sha256'][relative(p)]=sha(p)
        for p in sorted((PACKET/'captures'/case).glob('*')):
            if p.is_file():summary['raw_artifacts_sha256'][relative(p)]=sha(p)
        summary['runs'][case]=run
    summary['limits']=['No more native launches:3-run budget exhausted','Fully cold OS/file/Metal/shader state NOT-RUN','Process-warm contrast only; no causal attribution for startup difference','First surface content NOT-RUN; readback and foreground content separate','Production CPU cadence NOT-RUN; INFO records absent','No continuous RSS/device allocation peak claim; kernel reported lifetime footprint maximum separately labeled','Accepted baseline and diagnostic variants have different instrumentation overhead']
    inspections=PACKET/'image-inspections.json'
    if inspections.exists():
        notes=json.loads(inspections.read_text())
        for item in notes['captures'].values(): assert sha(Path(item['path']))==item['sha256']
        for item in notes['host_window_captures'].values(): assert sha(Path(item['path']))==item['sha256']
        summary['post_run_image_inspections']=notes
        for case,run in summary['runs'].items():
            for tag,item in run['captures'].items():
                item['content_observation']=notes['captures'][case+'/'+tag+'.png']['observed_content']
                item['inspection_method']='post-run tools.view_image; retained hash-bound observation receipt'
            run['host_window_capture']=notes['host_window_captures'][case]
        summary['status']='PARTIAL actual native display/GPU/memory and real-character pixels; fully cold/stall cause/CPU cadence remain NOT-RUN'
    output=PACKET/'actual-native-summary.json'
    output.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'output':str(output),'sha256':sha(output),'runs':{k:{'pid':v['pid'],'memory_samples':v['memory']['sample_count'],'first_display':v['first_valid_reported_surface_display']} for k,v in summary['runs'].items()}},indent=2))
if __name__=='__main__': main()
