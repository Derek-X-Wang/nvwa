#!/usr/bin/env python3
"""Independent stdlib GLB oracle + process-level preservation controls. No downloads."""
import argparse, hashlib, json, math, pathlib, struct, subprocess, tempfile, time
HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
sha = lambda b: hashlib.sha256(b).hexdigest()
def put(p, value):
    p.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
def decode(blob):
    size, = struct.unpack_from('<I',blob,12)
    doc=json.loads(blob[20:20+size]); binary=blob[28+size:]
    def accessor(index):
        a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']]
        assert a['componentType']==5126 and a['type']=='VEC3' and 'sparse' not in a
        offset=v.get('byteOffset',0)+a.get('byteOffset',0)
        return [struct.unpack_from('<3f',binary,offset+i*v.get('byteStride',12)) for i in range(a['count'])]
    return doc,accessor

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=pathlib.Path,required=True);args=ap.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    binary=HERE/'target/debug/compiled-character-probe'
    package=json.loads((HERE/'fixture-package.json').read_text())
    profile=json.loads((REPO/'assets/character.profile.json').read_text())
    original={p:sha(p.read_bytes()) for p in [REPO/'assets/fixtures/nvwa-humanoid.glb',REPO/'assets/character.profile.json',HERE/'fixture-package.json',HERE/'fixture-input-manifest.json']}
    blob=(REPO/'assets/fixtures/nvwa-humanoid.glb').read_bytes();doc,accessor=decode(blob)
    defaults={p['id']:p['default'] for p in profile['parameters']}
    cases=[('neutral',defaults)]
    for parameter in defaults:
        for value in [.25,.5,1.]:
            cases.append((f'{parameter}-{value}',dict(defaults,**{parameter:value})))
    cases.append(('combination',dict(jaw_width=.35,nose_width=.65,smile=.2,shoulder_width=.4)))
    summaries=[];started=time.monotonic()
    for name,values in cases:
        recipe={'schema_version':1,'case_id':name,'profile_id':profile['id'],'profile_sha256':package['profile_sha256'],'values':values}
        recipe_path=out/f'{name}.recipe.json';result_path=out/f'{name}.result.json';put(recipe_path,recipe)
        command=[str(binary),str(HERE/'fixture-package.json'),str(recipe_path),str(result_path)]
        run=subprocess.run(command,capture_output=True,text=True);assert run.returncode==0,(command,run.stderr)
        receipt=json.loads(result_path.read_text()); maximum=0.; vertices=0
        assert len(receipt['measured_positions'])==9
        for got in receipt['measured_positions']:
            ni,mi,pi=got['node'],got['mesh'],got['primitive'];prim=doc['meshes'][mi]['primitives'][pi]
            base=accessor(prim['attributes']['POSITION']);expected=[list(p) for p in base]
            for ti,t in enumerate(prim.get('targets',[])):
                parameter=next(b['parameter_id'] for b in package['bindings'] if (b['node'],b['mesh'],b['primitive'],b['target'])==(ni,mi,pi,ti))
                for p,d in zip(expected,accessor(t['POSITION'])):
                    for axis in range(3):p[axis]+=values[parameter]*d[axis]
            assert got['positions_f64le_sha256']==sha(b''.join(struct.pack('<3d',*p) for p in expected)),(name,ni,pi,'POSITION mismatch')
            assert got['source_node']==doc['nodes'][ni] and got['source_primitive']==prim
            assert got['bounds_local']['min']==[min(p[a] for p in expected) for a in range(3)]
            assert got['bounds_local']['max']==[max(p[a] for p in expected) for a in range(3)]
            vertices+=len(base);maximum=max(maximum,got['max_displacement_local'])
        if name=='neutral':assert maximum==0
        else:assert maximum>0,(name,'no deformation')
        assert receipt['joint_rest_state']['nodes']==doc['nodes']
        summaries.append({'case_id':name,'status':'passed','vertices':vertices,'max_displacement_local':maximum,'result':str(result_path.relative_to(out)),'result_sha256':sha(result_path.read_bytes())})
    # 0.25 and 0.5 displacements must scale, proving intermediate computation.
    for parameter in defaults:
        low=next(r for r in summaries if r['case_id']==parameter+'-0.25')['max_displacement_local']
        mid=next(r for r in summaries if r['case_id']==parameter+'-0.5')['max_displacement_local']
        high=next(r for r in summaries if r['case_id']==parameter+'-1.0')['max_displacement_local']
        assert math.isclose(mid,high*.5,abs_tol=1e-12) and math.isclose(low,high*.25,abs_tol=1e-12)
    failures=[]
    with tempfile.TemporaryDirectory(prefix='a-invalid-',dir=HERE/'evidence') as td:
        tmp=pathlib.Path(td)
        def reject(name,change_p=None,change_r=None,raw_recipe=None,change_blob=None,change_profile=None):
            p=json.loads(json.dumps(package));r={'schema_version':1,'case_id':name,'profile_id':profile['id'],'profile_sha256':p['profile_sha256'],'values':dict(defaults)}
            p['asset_path']=str(REPO/'assets/fixtures/nvwa-humanoid.glb');p['profile_path']=str(REPO/'assets/character.profile.json');p['source_manifest_path']=str(HERE/'fixture-input-manifest.json')
            if change_blob:
                bad=change_blob(bytearray(blob));f=tmp/'bad.glb';f.write_bytes(bad);p['asset_path']=str(f);p['asset_sha256']=sha(bad)
                new_profile=dict(profile,asset_sha256=p['asset_sha256']);f=tmp/'bad.profile.json';put(f,new_profile);p['profile_path']=str(f);p['profile_sha256']=sha(f.read_bytes());r['profile_sha256']=p['profile_sha256']
            if change_profile:
                pr=json.loads(json.dumps(profile));change_profile(pr);f=tmp/'bad.profile.json';put(f,pr);p['profile_path']=str(f);p['profile_sha256']=sha(f.read_bytes());r['profile_sha256']=p['profile_sha256']
            if change_blob or change_profile:
                mp=tmp/'manifest.json';put(mp,{'sample_class':p['sample_class'],'asset_sha256':p['asset_sha256'],'profile_sha256':p['profile_sha256']});p['source_manifest_path']=str(mp);p['source_manifest_sha256']=sha(mp.read_bytes())
            if change_p:change_p(p)
            if change_r:change_r(r)
            pp=tmp/'package.json';rp=tmp/'recipe.json';op=tmp/'result.json';put(pp,p)
            if raw_recipe is None:put(rp,r)
            else:rp.write_text(raw_recipe)
            command=[str(binary),str(pp),str(rp),str(op)]
            run=subprocess.run(command,capture_output=True,text=True);assert run.returncode==2,(name,run.stdout,run.stderr)
            assert not op.exists(),(name,'created output on failure')
            expected={'non-finite-real-position':'non-finite accessor value','unsupported-sparse-accessor':'unsupported float accessor','non-finite-accessor-bound':'number out of range','inverted-profile-bounds':'invalid/duplicate parameter bounds','missing-primitive-binding':'morph target lacks explicit','invalid-node-binding':'binding node/mesh mismatch'}
            if name in expected:assert expected[name] in run.stderr,(name,run.stderr)
            op.write_bytes(b'PRESERVE-EXISTING-RESULT\n')
            rerun=subprocess.run(command,capture_output=True,text=True)
            assert rerun.returncode==2 and op.read_bytes()==b'PRESERVE-EXISTING-RESULT\n'
            op.unlink();failures.append({'case_id':name,'status':'passed-rejection-control','exit_code':run.returncode,'diagnostic':json.loads(run.stderr),'no_new_output':True,'existing_output_preserved':True})
        reject('wrong-profile-hash',change_r=lambda r:r.update(profile_sha256='0'*64))
        reject('wrong-asset-hash',change_p=lambda p:p.update(asset_sha256='0'*64))
        reject('wrong-manifest-hash',change_p=lambda p:p.update(source_manifest_sha256='0'*64))
        reject('wrong-profile-id',change_r=lambda r:r.update(profile_id='other'))
        reject('invalid-node-binding',change_p=lambda p:p['bindings'][0].update(node=18))
        reject('missing-primitive-binding',change_p=lambda p:p['bindings'].pop())
        reject('duplicate-binding',change_p=lambda p:p['bindings'].append(p['bindings'][0]))
        reject('out-of-range',change_r=lambda r:r['values'].update(jaw_width=1.1))
        reject('unknown-parameter',change_r=lambda r:r['values'].update(unknown=.5))
        reject('missing-parameter',change_r=lambda r:r['values'].pop('jaw_width'))
        reject('inverted-profile-bounds',change_profile=lambda p:p['parameters'][0].update(min=2))
        reject('non-finite-recipe',raw_recipe='{"values":{"jaw_width":NaN}}')
        def nan_position(b):
            json_size,=struct.unpack_from('<I',b,12);a=doc['accessors'][23];v=doc['bufferViews'][a['bufferView']]
            struct.pack_into('<f',b,28+json_size+v.get('byteOffset',0)+a.get('byteOffset',0),float('nan'));return b
        reject('non-finite-real-position',change_blob=nan_position)
        def sparse_position(b):
            n,=struct.unpack_from('<I',b,12);j=json.loads(b[20:20+n]);j['accessors'][23]['sparse']={};payload=json.dumps(j,separators=(',',':')).encode();payload+=b' '*((-len(payload))%4);binary_chunk=b[20+n:];total=12+8+len(payload)+len(binary_chunk)
            return struct.pack('<III',0x46546c67,2,total)+struct.pack('<II',len(payload),0x4e4f534a)+payload+binary_chunk
        reject('unsupported-sparse-accessor',change_blob=sparse_position)
        def nonfinite_bound(b):
            n,=struct.unpack_from('<I',b,12);j=json.loads(b[20:20+n]);j['accessors'][23]['min'][0]='NONFINITE';payload=json.dumps(j,separators=(',',':')).replace('"NONFINITE"','1e999').encode();payload+=b' '*((-len(payload))%4);chunk=b[20+n:]
            return struct.pack('<III',0x46546c67,2,20+len(payload)+len(chunk))+struct.pack('<II',len(payload),0x4e4f534a)+payload+chunk
        reject('non-finite-accessor-bound',change_blob=nonfinite_bound)
        # Valid computation must also refuse an already existing output file.
        recipe=out/'neutral.recipe.json';existing=tmp/'existing.json';existing.write_bytes(b'KEEP\n')
        run=subprocess.run([str(binary),str(HERE/'fixture-package.json'),str(recipe),str(existing)],capture_output=True,text=True)
        assert run.returncode==2 and existing.read_bytes()==b'KEEP\n'
        failures.append({'case_id':'valid-input-existing-output','status':'passed-rejection-control','exit_code':2,'existing_output_preserved':True})
    assert all(sha(p.read_bytes())==h for p,h in original.items())
    summary={'schema_version':1,'sample_class':'nvwa-existing-fixture-control','route_id':'compiled-package','status':'passed','independent_oracle':'Python stdlib direct GLB POSITION/morph decode; all f64 output bytes, bounds and node/primitive identity compared','cases':summaries,'failure_controls':failures,'original_inputs_preserved':True,'private_case_evidence_path':str(out),'duration_seconds':time.monotonic()-started,'approved_makehuman_sample':{'status':'not_run','reason':'approved sample unavailable'},'reference_pipeline_run':False,'graphical_execution_run':False}
    put(out/'summary.json',summary)
    print(json.dumps({'status':'passed','cases':len(summaries),'failure_controls':len(failures),'summary':str(out/'summary.json'),'seconds':summary['duration_seconds']}))
if __name__=='__main__':main()
