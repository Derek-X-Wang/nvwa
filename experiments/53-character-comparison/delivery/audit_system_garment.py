"""Audit the approved ZIP and extract only the selected garment dependency files."""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import hashlib
import json
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[3]
STAGE = ROOT / '.work/character-approved-20261016'
REPORT = Path(__file__).resolve().parent
archive = STAGE / 'downloads/makehuman_system_assets_cc0.zip'
expected_sha = 'b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107'
assert archive.stat().st_size == 280737770
assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected_sha
prefix = 'clothes/female_sportsuit01/'
selected = [prefix + 'female_sportsuit01' + suffix for suffix in
            ['.mhclo', '.obj', '.mhmat', '_diffuse.png', '_normal.png', '_ao.png']]
with zipfile.ZipFile(archive) as z:
    seen = set()
    for entry in z.infolist():
        path = PurePosixPath(entry.filename)
        assert not path.is_absolute() and '..' not in path.parts and '\\' not in entry.filename
        assert not stat.S_ISLNK(entry.external_attr >> 16)
        assert not entry.flag_bits & 1, 'Encrypted entries are outside approved scope'
        assert entry.filename.casefold() not in seen
        seen.add(entry.filename.casefold())
    assert len(z.infolist()) == 517
    assert sum(x.file_size for x in z.infolist()) == 298739872
    texts = {path: z.read(path).decode('utf8') for path in selected if path.endswith(('.obj', '.mhclo', '.mhmat'))}
    for path, text in texts.items():
        assert 'explicitly released as CC0 in september 2020' in text
    mhclo = texts[prefix + 'female_sportsuit01.mhclo']
    material = texts[prefix + 'female_sportsuit01.mhmat']
    obj = texts[prefix + 'female_sportsuit01.obj']
    assert 'obj_file female_sportsuit01.obj' in mhclo
    assert 'material female_sportsuit01.mhmat' in mhclo
    assert not any(x.startswith(('vertexboneweights', 'rig ', 'rig_file ', 'armature ')) for x in mhclo.splitlines())
    assert not any(x.startswith('mtllib ') for x in obj.splitlines())
    edges = []
    for key in ['obj_file', 'material']:
        value = next(x.split(None, 1)[1] for x in mhclo.splitlines() if x.startswith(key + ' '))
        assert prefix + value in selected
        edges.append({'from': prefix + 'female_sportsuit01.mhclo', 'key': key, 'to': prefix + value, 'present': True})
    for line in material.splitlines():
        if not line or line.startswith('#'):
            continue
        key, *values = line.split()
        if key.lower().endswith('texture'):
            assert len(values) == 1
            assert prefix + values[0] in selected
            edges.append({'from': prefix + 'female_sportsuit01.mhmat', 'key': key,
                          'to': prefix + values[0], 'present': True})
    extracted = []
    for path in selected:
        body = z.read(path)  # ZIP CRC is checked for every selected file.
        target = STAGE / 'system-assets' / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert target.read_bytes() == body
        else:
            target.write_bytes(body)
        entry = {'archive_path': path, 'path': str(target.relative_to(ROOT)), 'bytes': len(body),
                 'sha256': hashlib.sha256(body).hexdigest(), 'crc_verified': True,
                 'license': 'CC0-1.0',
                 'license_evidence': 'Explicit CC0 header in this file' if path in texts else
                 'Named texture dependency of explicitly CC0 material; official whole-asset item is CC0. No independent embedded PNG license assertion.'}
        if path in texts:
            entry['license_header'] = '\n'.join(line for line in texts[path].splitlines()[:18] if line.startswith('#'))
        extracted.append(entry)
    legacy = [{'key': 'shader', 'reference': 'data/shaders/glsl/litsphere'},
              {'key': 'shaderParam litsphereTexture', 'reference': 'data/litspheres/lit_matte.png'}]
    for ref in legacy:
        assert ref['reference'] not in z.namelist()
        ref['present_in_system_pack'] = False
    result = {'schema_version': 1, 'status': 'garment-geometry-and-three-texture-dependencies-audited',
              'archive_sha256': expected_sha, 'archive_bytes': archive.stat().st_size,
              'archive_entries': 517, 'all_archive_expanded_file_bytes': 298739872,
              'zip_traversal_symlink_encryption_case_collision_check': 'passed',
              'all_archive_crc_checked': False, 'selected_file_crc_checked': True,
              'selected_garment': 'female_sportsuit01', 'files': extracted,
              'selected_extracted_file_bytes': sum(x['bytes'] for x in extracted),
              'dependency_edges': edges, 'custom_weights_or_rig_references': [],
              'legacy_makehuman_shader_references': legacy,
              'appearance_boundary': 'Legacy MakeHuman GLSL shader and litsphere are absent. MPFB MhMaterial parser explicitly leaves shader/litsphere handling as TODO. No complete MakeHuman material appearance parity is claimed; use bounded Blender material or neutral material for geometry comparison. No extra download authorized.',
              'license_authors_from_headers': ['Data Collection AB', 'Joel Palmius', 'Jonas Hauquier'],
              'system_zip_standalone_license_text_present': False,
              'retained_legal_text': 'experiments/53-character-comparison/downloads/licenses/mpfb-LICENSE.ASSETS.md',
              'official_item_license_evidence': 'https://static.makehumancommunity.org/assets/assetpacks/makehuman_system_assets.html',
              'thumbnail_extracted': False, 'other_pack_assets_extracted': False,
              'upstream_code_executed_by_download_worker': False,
              'completed_at': datetime.now(timezone.utc).isoformat()}
    (REPORT / 'system-garment-extraction-receipt.json').write_text(json.dumps(result, indent=2)+'\n')
    print('audited selected files', len(extracted), result['selected_extracted_file_bytes'], 'bytes')
