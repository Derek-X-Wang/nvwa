#!/usr/bin/env python3
"""Compare every JSON field and decoded accessor, retaining real differences."""
import argparse
import collections
import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True  # Import the frozen validator without writing beside it.
sys.path.insert(0, str(ROOT / 'tools/blender'))
from validate_fixture import accessor, read_glb, validate

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def scalar_equal(x,y):
    return x == y and not (isinstance(x,float) and isinstance(y,float) and x == 0 and math.copysign(1,x) != math.copysign(1,y))

def differences(a, b, path=''):
    if type(a) is not type(b):
        return [{'path': path, 'left': a, 'right': b}]
    if isinstance(a, dict):
        result = []
        for key in sorted(a.keys() | b.keys()):
            child = path + '/' + key.replace('~','~0').replace('/','~1')
            if key not in a or key not in b:
                result.append({'path': child, 'left': a.get(key), 'right': b.get(key), 'missing': 'left' if key not in a else 'right'})
            else:
                result.extend(differences(a[key], b[key], child))
        return result
    if isinstance(a, list):
        result = []
        if len(a) != len(b):
            result.append({'path': path+'/length', 'left': len(a), 'right': len(b)})
        for i, (x, y) in enumerate(zip(a, b)):
            result.extend(differences(x, y, path+'/'+str(i)))
        for i in range(min(len(a),len(b)),max(len(a),len(b))):
            result.append({'path': path+'/'+str(i), 'left': a[i] if i<len(a) else None, 'right': b[i] if i<len(b) else None, 'missing': 'left' if i>=len(a) else 'right'})
        return result
    return [] if scalar_equal(a,b) else [{'path': path, 'left': a, 'right': b}]

def accessor_usage(doc):
    usage = {i: [] for i in range(len(doc['accessors']))}
    for i, skin in enumerate(doc.get('skins', [])):
        if 'inverseBindMatrices' in skin:
            usage[skin['inverseBindMatrices']].append(f'skins/{i}/inverseBindMatrices')
    for i, mesh in enumerate(doc.get('meshes', [])):
        for j, primitive in enumerate(mesh['primitives']):
            base = f'meshes/{i}/primitives/{j}'
            if 'indices' in primitive:
                usage[primitive['indices']].append(base+'/indices')
            for key, index in primitive['attributes'].items():
                usage[index].append(base+'/attributes/'+key)
            for k, target in enumerate(primitive.get('targets', [])):
                for key, index in target.items():
                    usage[index].append(base+f'/targets/{k}/'+key)
    for i, animation in enumerate(doc.get('animations', [])):
        for j, sampler in enumerate(animation['samplers']):
            for key in ('input', 'output'):
                usage[sampler[key]].append(f'animations/{i}/{animation.get("name")}/samplers/{j}/{key}')
    return usage

def reference_map(doc):
    return {path: index for index, paths in accessor_usage(doc).items() for path in paths}

def metadata(doc):
    """Replace only known accessor references, preserving all other GLB fields."""
    result = copy.deepcopy(doc)
    for key in ('accessors', 'bufferViews', 'buffers'):
        result.pop(key, None)
    for mesh in result.get('meshes', []):
        for primitive in mesh['primitives']:
            if 'indices' in primitive:
                primitive['indices'] = 'DECODED_SEPARATELY'
            primitive['attributes'] = {key: 'DECODED_SEPARATELY' for key in primitive['attributes']}
            primitive['targets'] = [{key: 'DECODED_SEPARATELY' for key in target} for target in primitive.get('targets', [])]
    for skin in result.get('skins', []):
        if 'inverseBindMatrices' in skin:
            skin['inverseBindMatrices'] = 'DECODED_SEPARATELY'
    for animation in result.get('animations', []):
        for sampler in animation['samplers']:
            sampler['input'] = sampler['output'] = 'DECODED_SEPARATELY'
    return result

def numeric_delta(x, y):
    delta = [(row, col, u, v) for row, (xr, yr) in enumerate(zip(x, y)) for col, (u, v) in enumerate(zip(xr, yr)) if not scalar_equal(u,v)]
    unpaired = sum(abs(len(u)-len(v)) for u,v in zip(x,y)) + sum(len(row) for row in x[len(y):]) + sum(len(row) for row in y[len(x):])
    shapes = [{'row':i,'left_width':len(x[i]) if i<len(x) else None,'right_width':len(y[i]) if i<len(y) else None} for i in range(max(len(x),len(y))) if i>=min(len(x),len(y)) or len(x[i])!=len(y[i])]
    xhash,yhash = sha(json.dumps(x).encode()),sha(json.dumps(y).encode())
    return {'equal': xhash == yhash, 'left_count': len(x), 'right_count': len(y), 'changed_components': len(delta)+unpaired, 'unpaired_components':unpaired, 'shape_differences':shapes, 'signed_zero_changes': sum(u==v==0 for _,_,u,v in delta), 'max_absolute_delta': max((abs(u-v) for _,_,u,v in delta), default=0), 'max_absolute_delta_scope':'paired scalar values; unpaired components reported separately', 'first_deltas': delta[:8], 'left_decoded_sha256': xhash, 'right_decoded_sha256': yhash}

def triangle_counts(rows):
    assert len(rows) % 3 == 0
    # Secondary equivalence check only. Raw order and exact numeric deltas remain.
    triangles = [tuple(row[0] for row in rows[i:i+3]) for i in range(0,len(rows),3)]
    return collections.Counter(min(t, t[1:]+t[:1], t[2:]+t[:2]) for t in triangles)

def semantic_accessors(a, ab, b, bb):
    maps = [reference_map(doc) for doc in (a,b)]
    result = []
    for path in sorted(maps[0].keys() | maps[1].keys()):
        entry = {'path': path}
        if path not in maps[0] or path not in maps[1]:
            entry['missing'] = 'left' if path not in maps[0] else 'right'
        else:
            i,j = maps[0][path], maps[1][path]
            x,y = accessor(a,ab,i), accessor(b,bb,j)
            descriptors = [{key:value for key,value in doc['accessors'][index].items() if key not in ('bufferView','byteOffset')} for doc,index in ((a,i),(b,j))]
            entry.update(left_index=i,right_index=j,descriptor_differences=differences(*descriptors),**numeric_delta(x,y))
            if path.endswith('/indices'):
                tx,ty = triangle_counts(x),triangle_counts(y)
                entry.update(oriented_triangle_multiset_equal=tx==ty, left_only_oriented_triangles=sum((tx-ty).values()), right_only_oriented_triangles=sum((ty-tx).values()))
        result.append(entry)
    return result

def blend_blocks(path):
    raw = path.read_bytes()
    assert raw[:7] == b'BLENDER', 'Only uncompressed native .blend supported'
    pointer_bytes = {'-':8,'_':4}[chr(raw[7])]
    endian = {'v':'<','V':'>'}[chr(raw[8])]
    fmt = endian + '4sI' + ('Q' if pointer_bytes==8 else 'I') + 'II'
    offset = 12
    result = []
    while offset < len(raw):
        code,size,address,sdna,count = struct.unpack_from(fmt,raw,offset)
        header_bytes = struct.calcsize(fmt)
        payload = raw[offset+header_bytes:offset+header_bytes+size]
        assert len(payload)==size
        result.append({'code':code.decode('ascii').rstrip('\0'),'size':size,'old_address':address,'sdna':sdna,'count':count,'payload':payload})
        offset += header_bytes+size
    assert offset==len(raw)
    return raw[:12].decode('ascii'),result

def blend_comparison(left,right):
    ah,a = blend_blocks(left)
    bh,b = blend_blocks(right)
    by_code = collections.defaultdict(lambda: {'blocks':0,'changed_payload_blocks':0,'changed_payload_bytes':0,'changed_old_address_headers':0})
    structural = []
    for i,(x,y) in enumerate(zip(a,b)):
        fields = ['code','size','sdna','count']
        if any(x[k]!=y[k] for k in fields):
            structural.append({'index':i,'left':{k:x[k] for k in fields},'right':{k:y[k] for k in fields}})
        tally=by_code[x['code']]
        tally['blocks']+=1
        tally['changed_old_address_headers']+=int(x['old_address']!=y['old_address'])
        tally['changed_payload_blocks']+=int(x['payload']!=y['payload'])
        tally['changed_payload_bytes']+=sum(u!=v for u,v in zip(x['payload'],y['payload']))+abs(len(x['payload'])-len(y['payload']))
    for i in range(min(len(a),len(b)),max(len(a),len(b))):
        structural.append({'index':i,'left':{k:a[i][k] for k in ('code','size','sdna','count')} if i<len(a) else None,'right':{k:b[i][k] for k in ('code','size','sdna','count')} if i<len(b) else None,'missing':'left' if i>=len(a) else 'right'})
    return {'headers':[ah,bh],'block_counts':[len(a),len(b)],'structural_header_differences':structural,'by_code':dict(by_code),'limit':'BHead layout and exact payload byte comparison only. Internal pointers, save paths and all .blend scene semantics are not decoded; no claim of complete .blend equivalence.'}

def compare(left, right):
    paths = [left/'nvwa-humanoid.glb', right/'nvwa-humanoid.glb']
    docs_bins = [read_glb(path) for path in paths]
    (a, ab), (b, bb) = docs_bins
    validations = [validate(path) for path in paths]
    usages = [accessor_usage(doc) for doc in (a, b)]
    accessor_results = []
    for i in range(max(len(a['accessors']), len(b['accessors']))):
        entry = {'index': i, 'left_usage': usages[0].get(i), 'right_usage': usages[1].get(i)}
        if i >= min(len(a['accessors']), len(b['accessors'])):
            entry['missing'] = True
        else:
            x, y = accessor(a, ab, i), accessor(b, bb, i)
            entry.update(**numeric_delta(x,y))
        accessor_results.append(entry)
    files = {}
    for name in ('nvwa-humanoid.glb','nvwa-humanoid.blend','source-structure.json'):
        x,y = (left/name).read_bytes(), (right/name).read_bytes()
        files[name] = {'left_sha256': sha(x), 'right_sha256': sha(y), 'left_bytes': len(x), 'right_bytes': len(y), 'byte_equal': x==y}
    result = {'files': files, 'json_field_differences': differences(a,b), 'binary_chunk_equal': ab==bb, 'binary_chunk_sha256': [sha(ab),sha(bb)], 'accessors': accessor_results, 'validations': validations, 'source_structure_differences': differences(json.loads((left/'source-structure.json').read_text()),json.loads((right/'source-structure.json').read_text()))}
    result['all_compared_artifacts_byte_equal'] = all(entry['byte_equal'] for entry in files.values())
    result['exact_glb_semantics_equal'] = not result['json_field_differences'] and all(e.get('equal') for e in accessor_results)
    result['referenced_semantic_accessors'] = semantic_accessors(a,ab,b,bb)
    result['semantic_metadata_differences'] = differences(metadata(a),metadata(b))
    result['unreferenced_accessors'] = [[i for i,paths in usage.items() if not paths] for usage in usages]
    result['blend_blocks'] = blend_comparison(left/'nvwa-humanoid.blend',right/'nvwa-humanoid.blend')
    profile=json.loads((ROOT/'assets/character.profile.json').read_text())
    for validation in validations:
        assert [(m['id'],m['morph_index']) for m in validation['morphs']] == [(p['id'],p['morph_index']) for p in profile['parameters']]
        assert [{key:clip[key] for key in ('id','animation_index','duration_seconds')} for clip in validation['clips']] == profile['clips']
    result['published_profile_indices_and_durations_match_both_exports'] = True
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('left',type=Path)
    parser.add_argument('right',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--require-exact',action='store_true',help='Fail unless GLB, .blend and source-structure.json are each byte-identical')
    args = parser.parse_args()
    result = compare(args.left,args.right)
    encoded=json.dumps(result,indent=2)+'\n'
    if args.output:
        args.output.write_text(encoded)
    print(json.dumps({'byte_equal': {k:v['byte_equal'] for k,v in result['files'].items()},'all_compared_artifacts_byte_equal':result['all_compared_artifacts_byte_equal'],'json_differences':len(result['json_field_differences']),'changed_accessors':[e['index'] for e in result['accessors'] if not e.get('equal')],'exact_glb_semantics_equal':result['exact_glb_semantics_equal']},indent=2))
    if args.require_exact and not result['all_compared_artifacts_byte_equal']:
        sys.exit(1)

if __name__=='__main__':
    main()
