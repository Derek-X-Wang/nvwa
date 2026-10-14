#!/usr/bin/env python3
"""Measure retained real captures, excluding all transport UI and window chrome."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SCREENS = HERE / 'screens'
TIMES = [0, .123, .5, 1.25, 2.345, 3]

def difference(reference, candidate, rect):
    a = np.asarray(Image.open(reference).convert('RGB').crop(rect), dtype=np.int16)
    b = np.asarray(Image.open(candidate).convert('RGB').crop(rect), dtype=np.int16)
    delta = np.abs(a-b)
    return {'pixel_count': int(a.shape[0]*a.shape[1]),
            'changed_pixels': int(np.any(delta != 0, axis=2).sum()),
            'pixels_over_8_levels': int(np.any(delta > 8, axis=2).sum()),
            'max_channel_difference_0_to_255': int(delta.max()),
            'mean_absolute_channel_difference': float(delta.mean())}

def main():
    rows = []
    for time in TIMES:
        reference = SCREENS / f'reference-wave-{time:.3f}.png'
        assert Image.open(reference).size == (1280, 784)
        row = {'time_seconds': time}
        for variant in ['naive', 'corrected']:
            candidate = SCREENS / f'{variant}-wave-{time:.3f}.png'
            assert Image.open(candidate).size == (1280, 784)
            row[variant] = difference(reference, candidate, (0, 64, 1280, 675))
        rows.append(row)
    rests = {variant: difference(SCREENS / 'reference-rest-smoke.png',
                                SCREENS / f'{variant}-rest-smoke.png', (0, 0, 1280, 611))
             for variant in ['naive', 'corrected']}
    evidence = {}
    for path in sorted(HERE.glob('*.log')):
        for line in path.read_text().splitlines():
            if 'NVWA_EVIDENCE ' in line:
                payload = json.loads(line.split('NVWA_EVIDENCE ', 1)[1])
                assert payload['ready'] and payload['error'] is None and payload['capture_callback']
                assert payload['physical_window'] == {'height':720, 'scale_factor':1.0, 'width':1280}
                assert payload['joints'] == 18 and payload['skins'] == 9
                if 'rest' in path.name:
                    assert payload['active_animations'] == 0 and payload['timeline_count'] == 0
                else:
                    assert payload['active_animations'] == 1 and payload['clip'] == 'wave'
                evidence[path.name] = payload
    assert len(evidence) == 6
    metrics = {'wave_scene_rect_on_raw_window': [0,64,1280,675],
               'rest_scene_rect_on_renderer_png': [0,0,1280,611],
               'wave_samples': rows, 'rest_controls': rests, 'renderer_evidence': evidence,
               'interpretation': 'Pixel deltas describe these captures only; geometry tolerances remain the CPU measurement. No perceptual quality or performance claim.'}
    (HERE / 'visual-metrics.json').write_text(json.dumps(metrics, indent=2)+'\n')
    # Contact sheet uses only cropped raw runtime pixels, at their original scale.
    sheet = Image.new('RGB', (900, 6*360), '#111821')
    draw = ImageDraw.Draw(sheet)
    for row, time in enumerate(TIMES):
        for column, variant in enumerate(['reference', 'naive', 'corrected']):
            raw = Image.open(SCREENS / f'{variant}-wave-{time:.3f}.png').convert('RGB')
            crop = raw.crop((500,240,800,570))
            sheet.paste(crop, (column*300, row*360+30))
            draw.text((column*300+10,row*360+8),f'{variant} | wave {time:.3f} s', fill='white')
    sheet.save(HERE / 'comparison.png')
    result = {'wave_samples': rows, 'rest_controls': rests, 'verified_renderer_receipts': len(evidence)}
    (HERE / 'analysis-run-output.json').write_text(json.dumps(result, indent=2)+'\n')
    hashes = {str(path.relative_to(HERE)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(HERE.rglob('*')) if path.is_file() and path.name != 'SHA256SUMS.json'}
    (HERE / 'SHA256SUMS.json').write_text(json.dumps(hashes, indent=2)+'\n')
    print('Verified 6 renderer receipts, 18 paused wave samples, and 3 rest captures.')

if __name__ == '__main__':
    main()
