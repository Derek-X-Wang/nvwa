import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import unittest
ROOT=Path(__file__).resolve().parents[2]
EXP=Path(__file__).resolve().parent

def load(name):
    spec=importlib.util.spec_from_file_location(name,EXP/(name+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class Inputs(unittest.TestCase):
    def test_frozen_experiments_unchanged(self):
        for name,item in json.loads((EXP/'FROZEN-INPUTS.json').read_text()).items():
            data=(ROOT/name).read_bytes();self.assertEqual(len(data),item['bytes']);self.assertEqual(hashlib.sha256(data).hexdigest(),item['sha256'])
    def test_fixed_work_changes_only_saved_selection_and_revision(self):
        source=json.loads((ROOT/'experiments/65-b1-appearance-quality/evidence/inputs/short-front.nvwa.json').read_text())
        fixed=json.loads((EXP/'works/short-front.nvwa.json').read_text());appearance=fixed['character'].pop('appearance')
        self.assertEqual(appearance['type'],'b1_cc0');self.assertTrue(all(appearance[k] for k in ['skin','eyes','hair']))
        self.assertEqual(appearance['asset_set_sha256'],hashlib.sha256((ROOT/'assets/appearances/mpfb-b1-cc0-v1/manifest.json').read_bytes()).hexdigest())
        self.assertEqual(fixed.pop('revision'),source.pop('revision')+1);source['character'].pop('appearance');self.assertEqual(fixed,source)
    def test_shoulder_work_has_only_the_declared_jaw_selection_revision_delta(self):
        source=json.loads((ROOT/'experiments/65-b1-appearance-quality/evidence/inputs/long-front.nvwa.json').read_text());fixed=json.loads((EXP/'works/long-front-shoulder.nvwa.json').read_text())
        self.assertEqual(source['character']['parameters']['jaw_drop'],1.)
        self.assertEqual(fixed['character']['parameters'],{'torso_length':1.,'jaw_drop':0.})
        fixed['character']['parameters']['jaw_drop']=1.
        self.assertEqual(fixed.pop('revision'),source.pop('revision')+1)
        fixed['character'].pop('appearance');source['character'].pop('appearance');self.assertEqual(fixed,source)
    def test_reference_camera_matches_existing_frozen_capture(self):
        record=json.loads((EXP/'works/reference-short-front.json').read_text());source=ROOT/record['source'];self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),record['source_sha256'])
        self.assertEqual(record['camera'],json.loads(source.read_text())['camera']);self.assertEqual(record['camera']['viewport_size_pixels'],[1280,720])
    def test_shoulder_reference_is_exact_frozen65_long_front_not_short_front(self):
        record=json.loads((EXP/'works/reference-long-front.json').read_text());source=ROOT/record['source'];actual=json.loads(source.read_text())
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),record['source_sha256'])
        self.assertEqual(record['camera'],actual['camera']);self.assertEqual(record['shape'],{'torso_length':1,'jaw_drop':1})
        self.assertEqual(record['camera']['global_transform'][13],1.6997191905975342)
        short=json.loads((EXP/'works/reference-short-front.json').read_text())
        self.assertNotEqual(record['camera']['global_transform'],short['camera']['global_transform'])
        for key in ['projection','msaa','viewport_size_pixels']:self.assertEqual(record['camera'][key],short['camera'][key])
    def test_eye_source_corner_map_and_f32_uv_policy(self):
        record=json.loads((EXP/'works/eye-source-map.json').read_text());source=ROOT/record['source'];self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),record['source_sha256'])
        f32=lambda x:struct.unpack('f',struct.pack('f',x))[0]
        tex=[];faces=[];count=0
        for line in source.read_text().splitlines():
            f=line.split()
            if not f:continue
            if f[0]=='v':count+=1
            if f[0]=='vt':tex.append([f32(float(f[1])),f32(1.-f32(float(f[2])))])
            if f[0]=='f':faces.append([tuple(int(n)-1 for n in token.split('/')) for token in f[1:]])
        pairs=[]
        for face in faces:
            for pair in face:
                if pair not in pairs:pairs.append(pair)
        triangles=[]
        for face in faces:
            for index in range(1,len(face)-1):triangles += [pairs.index(face[0]),pairs.index(face[index]),pairs.index(face[index+1])]
        self.assertEqual(count,96);self.assertEqual(pairs[0][0],8);self.assertEqual(len(triangles)//3,172)
        self.assertEqual([list(p) for p in pairs],record['source_uv_pairs']);self.assertEqual(triangles,record['indices']);self.assertEqual([tex[t] for _,t in pairs],record['uv_0'])
    def test_manifests_are_standalone_and_no_extra_dependency(self):
        import tomllib
        manifest=tomllib.loads((EXP/'Cargo.toml').read_text());old=tomllib.loads((ROOT/'experiments/66-b1-appearance-work/Cargo.toml').read_text())
        self.assertEqual(manifest['dependencies'],old['dependencies']);self.assertIn('workspace',manifest)
        lock=tomllib.loads((EXP/'Cargo.lock').read_text());self.assertTrue(any(p['name']==manifest['package']['name'] for p in lock['package']))
    def test_pinned_witness_counts_match_frozen_existing_reference(self):
        record=json.loads((ROOT/'experiments/65-b1-appearance-quality/evidence/native/records/n65-sf-reference.json').read_text())
        actual={p['name']:(p['vertex_count'],p['index_count']) for p in record['body_parts']}
        self.assertEqual(load('check_captures').PART_COUNTS,actual)
    def test_build_source_closure_has_production_and_fixed_sources(self):
        closure=load('build').closure()
        for name in ['crates/nvwa-runtime/src/appearance/mod.rs','crates/nvwa-runtime/src/appearance/geometry.rs','crates/nvwa-studio/src/lib.rs','experiments/68-b1-eye-render-diagnosis/src/diagnostic.rs','assets/appearances/mpfb-b1-cc0-v1/manifest.json']:
            self.assertIn(name,closure)

if __name__=='__main__':unittest.main()
