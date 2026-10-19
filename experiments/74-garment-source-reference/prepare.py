"""Authenticate historical witness/controls and prepare private original-tool inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/70-b1-garment-defect'))
from diagnose import Source, analyze, read_record, unique


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--stage', type=Path, required=True)
    p.add_argument('--captures', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    source = Source(ROOT / 'assets/characters/mpfb-b1-v1')
    receipt_path = ROOT / 'experiments/53-character-comparison/delivery/mpfb-extraction-receipt.json'
    receipt = json.loads(receipt_path.read_text())
    for entry in receipt['files']:
        rel = Path(entry['path']).relative_to('.work/character-approved-20261016')
        path = a.stage / rel
        require(path.is_file() and not path.is_symlink() and path.stat().st_size == entry['bytes'] and digest(path) == entry['sha256'],
                'approved extraction changed: ' + str(rel))
    source_hashes = {}
    for rel, expected in {
        'mpfb-addon/entities/clothes/mhclo.py': '909ea98e31e04dfe8eb7c54849f74aa7365be0676a102c8c30e0e6c64b3eb9d8',
        'mpfb-addon/services/clothesservice.py': '20b60daeb862e35652035b9e94d1830f1bd2d86706b1e6056f0f2cee43c8d40b',
        'mpfb-addon/services/objectservice.py': '4a90898fc83d237446355d2c9b8f30b90f056be0d2325b3989b30b341d075211',
        'system-assets/clothes/female_sportsuit01/female_sportsuit01.mhclo': '6df057d3116db93afbbbb6d692f92cce84aa16db699f47dd14e825d07c6fd42f',
        'system-assets/clothes/female_sportsuit01/female_sportsuit01.obj': 'fd529bb8dd6a994c1e9a3fb2fd8b236f52c0cc7cebb1f6fd9328953d9df6d6ff',
    }.items():
        source_hashes[rel] = digest(a.stage / rel)
        require(source_hashes[rel] == expected, 'source hash mismatch: ' + rel)
    cases, reports = [], []
    for label, clip, k, wanted_red in [('arm0', 'b1_arm_rehearsal_v1', 0, False), ('arm2', 'b1_arm_rehearsal_v1', 16, True), ('knee2', 'b1_knee_flex_v1', 16, False)]:
        path = a.captures / f't+1__{clip}__k{k:02}.json.gz'
        record, sha = read_record(path)
        expected = dict(torso_length=1., jaw_drop=0., clip_id=clip, seconds=k / 8)
        report = analyze(record, source, expected)
        red = report['geometry']['posed_over_fitted_rest_area'] > 10
        require(red == wanted_red, 'historical shoulder/control signal changed: ' + label)
        s = record['snapshot']
        garment = next(x for x in s['parts'] if x['name'] == 'garment')
        body = next(x for x in s['parts'] if x['name'] == 'body')
        cases.append(dict(case=label, expected=expected, sha256=sha, path=str(path.resolve()), bones=s['bones'],
                          cage=unique(body, 'rest_positions', 19158),
                          garment_rest=unique(garment, 'rest_positions', 1797),
                          garment_posed=unique(garment, 'positions', 1797)))
        reports.append(dict(case=label, input_sha256=sha, diagnostic_exit_code=3 if red else 0, report=report))
    packet = dict(schema_version=1, cases=cases, triangles=source.triangles, source_hashes=source_hashes,
                  author_recipe='UNKNOWN', official_reference_executed=False)
    (a.out / 'inputs.json').write_text(json.dumps(packet, allow_nan=False))
    evidence = dict(schema_version=1, source_hashes=source_hashes, historical_replay=reports,
                    addon_extraction_files_verified=len(receipt['files']), extraction_receipt_sha256=digest(receipt_path),
                    prepared_input_sha256=digest(a.out / 'inputs.json'),
                    official_reference_executed=False, quality='HOLD')
    (a.out / 'preparation.json').write_text(json.dumps(evidence, indent=2, allow_nan=False) + '\n')
    print(json.dumps({r['case']: r['diagnostic_exit_code'] for r in reports}))


if __name__ == '__main__':
    main()
