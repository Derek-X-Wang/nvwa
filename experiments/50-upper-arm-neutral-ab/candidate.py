#!/usr/bin/env python3
"""One frozen two-channel intervention. Standard library only, no inference."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
UPPER = {'upper_arm.L':4, 'upper_arm.R':7}

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

export48 = module('export48', 'experiments/48-genuine-fixture-work/export.py')
math47 = module('math47', 'experiments/47-fixture-rig-calibration/calibrate.py')

def need(ok, message):
    if not ok:
        raise ValueError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def inputs():
    contract = json.loads((HERE/'CONTRACT.json').read_text())
    for path, digest in contract['input_sha256'].items():
        need(sha((ROOT/path).read_bytes()) == digest, 'input pin '+path)
    paths = list(contract['input_sha256'])
    base = (ROOT/paths[0]).read_bytes()
    doc, binary = export48.decode_glb(base)
    calibration = json.loads((ROOT/'experiments/47-fixture-rig-calibration/calibration.json').read_text())
    source = json.loads((ROOT/'experiments/41-real-short-motion/source-skeleton.json').read_text())
    return contract, base, doc, binary, calibration, source

def assumptions(doc, calibration, source):
    _, _, pinned, _, cal, meta = inputs()
    need(doc['nodes'] == pinned['nodes'], 'exact pinned target hierarchy and static TRS')
    need(source == meta, 'pinned static source rest, never animated key0')
    need(calibration == cal, 'pinned static geometric frames')
    need(calibration['basis'] == math47.I, 'physical identity axes')
    need(all(q == [0,0,0,1] for q in source['rest_local_rotations_xyzw']), 'identity static source rest')
    parents = {}
    for i, node in enumerate(doc['nodes']):
        for child in node.get('children', []):
            need(child not in parents, 'single target parent')
            parents[child] = i
    # The entire static chain from chest through the scene root must be identity
    # rotation and unit scale. This is intentionally not a general rig formula.
    index = 8
    while True:
        node = doc['nodes'][index]
        need(node.get('rotation',[0,0,0,1]) == [0,0,0,1], 'identity neutral chest frame')
        need(node.get('scale',[1,1,1]) == [1,1,1], 'unit neutral chest ancestor scales')
        if index not in parents:
            break
        index = parents[index]
    rows = {r['target']:r for r in calibration['rows']}
    for name, index in UPPER.items():
        row = rows[name]
        need(parents[index] == 8 and row['target_parent']=='chest', 'immediate chest parent')
        need(row['guide'] == [0,0,1] and row['source_rest_gauge']==row['source_frame'], 'static chest-frame conventions')
        need(row['source']=={'upper_arm.L':'RightArm','upper_arm.R':'LeftArm'}[name], 'physical sides')
    return rows

def construct(mode='candidate', doc=None, calibration=None, source=None):
    need(mode in {'candidate','wrong_physical_sides','reversed_multiplication','double_correction','correct_descendants','duplicated_root'}, 'named fixed construction mode')
    _, _, d, binary, cal, meta = inputs()
    doc = d if doc is None else doc
    cal = cal if calibration is None else calibration
    meta = meta if source is None else source
    rows = assumptions(doc, cal, meta)
    out = copy.deepcopy(doc)
    data = bytearray(binary)
    corrections = {}
    clip = out['animations'][3]
    for name, index in UPPER.items():
        row = rows[name]
        if mode == 'wrong_physical_sides':
            row = rows['upper_arm.R' if name.endswith('L') else 'upper_arm.L']
        c = math47.mm(row['source_frame'], math47.tr(row['target_frame']))
        math47.validate_rotation(c)
        corrections[name] = c
        channel = next(c for c in clip['channels'] if c['target']=={'node':index,'path':'rotation'})
        accessor = out['accessors'][clip['samplers'][channel['sampler']]['output']]
        view = out['bufferViews'][accessor['bufferView']]
        start = view.get('byteOffset',0)+accessor.get('byteOffset',0)
        need(accessor['count']==90 and accessor['componentType']==5126 and accessor['type']=='VEC4', 'exact 90 quaternion channel')
        previous = None
        for key in range(90):
            q = list(struct.unpack_from('<4f',binary,start+key*16))
            r = math47.rotation(q)
            result = math47.mm(r,c) if mode=='reversed_multiplication' else math47.mm(c,r)
            if mode=='double_correction': result=math47.mm(c,result)
            q = export48.quaternion(result)
            if previous is not None and sum(x*y for x,y in zip(previous,q))<0: q=[-x for x in q]
            struct.pack_into('<4f',data,start+key*16,*q)
            previous=q
        if mode=='correct_descendants':
            for descendant in (index-1,index-2):
                ch=next(x for x in clip['channels'] if x['target']=={'node':descendant,'path':'rotation'})
                a=out['accessors'][clip['samplers'][ch['sampler']]['output']];v=out['bufferViews'][a['bufferView']]
                offset=v.get('byteOffset',0)+a.get('byteOffset',0)
                for key in range(90):
                    q=struct.unpack_from('<4f',binary,offset+key*16)
                    struct.pack_into('<4f',data,offset+key*16,*export48.quaternion(math47.mm(c,math47.rotation(list(q)))))
    if mode=='duplicated_root':
        ch=next(x for x in clip['channels'] if x['target']=={'node':17,'path':'translation'})
        a=out['accessors'][clip['samplers'][ch['sampler']]['output']];v=out['bufferViews'][a['bufferView']]
        offset=v.get('byteOffset',0)+a.get('byteOffset',0)
        for key in range(90):
            q=struct.unpack_from('<3f',binary,offset+key*12)
            struct.pack_into('<3f',data,offset+key*12,*[2*x for x in q])
    return export48.pack_glb(out,bytes(data)), corrections

def candidate_asset(path):
    # The immutable prior evaluator deliberately only admits baseline bytes.
    # This explicit adapter admits the caller's *new* file hash for this load;
    # all parser/FK/skin assertions remain the unchanged prior implementation.
    ev=module('independent49','experiments/49-runtime-pose-parity/offline/evaluator.py')
    ev.GLB_SHA=sha(Path(path).read_bytes())
    return ev.Asset(path)

def export(path, work_path):
    data, corrections=construct()
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(data)
    work=json.loads((ROOT/'experiments/48-genuine-fixture-work/artifacts/genuine44-calibrated47.nvwa.json').read_text())
    work['profile']['id']='nvwa-experiment50-upper-arm-neutral-ab'
    work['character']['profile_id']=work['profile']['id']
    work['profile']['asset_path']='generated/genuine44-upper-arm-neutral50.glb'
    work['profile']['asset_sha256']=sha(data)
    work_path.write_text(json.dumps(work,indent=2)+'\n')
    return corrections
