#!/usr/bin/env python3
"""Exercise comparator failures on a real exported fixture without new exports."""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from compare import ROOT, compare, numeric_delta, read_glb, triangle_counts
import run_pair

PAIR = ROOT / '.work/export-drift' / os.environ.get('NVWA_EXPORT_TEST_PAIR','control')
FIXTURE = PAIR / 'run-1'
PRIVATE = Path(__file__).resolve().parent

def write_glb(path, doc, binary, indent=None):
    encoded=json.dumps(doc,separators=(',',':'),indent=indent).encode()
    encoded+=b' '*((-len(encoded))%4)
    binary+=b'\0'*((-len(binary))%4)
    raw=struct.pack('<4sII',b'glTF',2,12+8+len(encoded)+8+len(binary))
    raw+=struct.pack('<II',len(encoded),0x4e4f534a)+encoded
    raw+=struct.pack('<II',len(binary),0x004e4942)+binary
    path.write_bytes(raw)

@unittest.skipUnless((FIXTURE/'nvwa-humanoid.glb').exists(),'Run isolated control pair first')
class RealFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='comparator-test-',dir=PRIVATE)
        self.output=Path(self.temporary.name)
        for name in ('nvwa-humanoid.glb','nvwa-humanoid.blend','source-structure.json'):
            shutil.copyfile(FIXTURE/name,self.output/name)
        self.doc,self.binary=read_glb(self.output/'nvwa-humanoid.glb')
    def tearDown(self):
        self.temporary.cleanup()
    def finish_mutation(self):
        write_glb(self.output/'nvwa-humanoid.glb',self.doc,self.binary)
        result=compare(FIXTURE,self.output)
        self.assertFalse(result['exact_glb_semantics_equal'])
        return result
    def test_self_control_exact(self):
        result=compare(FIXTURE,FIXTURE)
        self.assertTrue(result['exact_glb_semantics_equal'])
        self.assertTrue(result['all_compared_artifacts_byte_equal'])
        self.assertTrue(all(e['equal'] for e in result['referenced_semantic_accessors']))
    def assert_cli_rejects_bytes_only_change(self, artifact):
        report=self.output/'comparison.json'
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('compare.py')),str(FIXTURE),str(self.output),'--output',str(report),'--require-exact'],capture_output=True,text=True)
        self.assertEqual(result.returncode,1,result.stdout+result.stderr)
        measurement=json.loads(report.read_text())
        self.assertFalse(measurement['files'][artifact]['byte_equal'])
        self.assertFalse(measurement['all_compared_artifacts_byte_equal'])
        self.assertTrue(measurement['exact_glb_semantics_equal'])
    def test_cli_rejects_reserialized_glb(self):
        write_glb(self.output/'nvwa-humanoid.glb',self.doc,self.binary,indent=2)
        self.assert_cli_rejects_bytes_only_change('nvwa-humanoid.glb')
    def test_cli_rejects_blend_only_change(self):
        path=self.output/'nvwa-humanoid.blend'
        raw=bytearray(path.read_bytes())
        raw[36]^=1  # First REND payload byte; preserve native block layout.
        path.write_bytes(raw)
        self.assert_cli_rejects_bytes_only_change('nvwa-humanoid.blend')
    def test_cli_rejects_source_proof_whitespace(self):
        path=self.output/'source-structure.json'
        path.write_bytes(path.read_bytes()+b'\n')
        self.assert_cli_rejects_bytes_only_change('source-structure.json')
    def test_real_pair_byte_verdict_matches_actual_files(self):
        result=compare(FIXTURE,PAIR/'run-2')
        expected=all((FIXTURE/name).read_bytes()==(PAIR/'run-2'/name).read_bytes() for name in ('nvwa-humanoid.glb','nvwa-humanoid.blend','source-structure.json'))
        self.assertEqual(result['all_compared_artifacts_byte_equal'],expected)
        if not result['files']['nvwa-humanoid.glb']['byte_equal']:
            self.assertTrue(result['json_field_differences'] or not result['binary_chunk_equal'])
    def test_channel_interpolation_change_detected(self):
        self.doc['animations'][0]['samplers'][0]['interpolation']='STEP'
        result=self.finish_mutation()
        self.assertTrue(any(e['path']=='/animations/0/samplers/0/interpolation' for e in result['semantic_metadata_differences']))
    def test_skin_joint_order_change_detected(self):
        joints=self.doc['skins'][0]['joints']
        joints[0],joints[1]=joints[1],joints[0]
        result=self.finish_mutation()
        self.assertTrue(any(e['path']=='/skins/0/joints/0' for e in result['semantic_metadata_differences']))
    def test_material_change_detected(self):
        self.doc['materials'][0]['pbrMetallicRoughness']['roughnessFactor']=0.25
        result=self.finish_mutation()
        self.assertTrue(any('/roughnessFactor' in e['path'] for e in result['semantic_metadata_differences']))
    def test_one_binary_normal_change_detected(self):
        idx=self.doc['meshes'][0]['primitives'][0]['attributes']['NORMAL']
        acc=self.doc['accessors'][idx]
        view=self.doc['bufferViews'][acc['bufferView']]
        offset=view.get('byteOffset',0)+acc.get('byteOffset',0)
        raw=bytearray(self.binary)
        old=struct.unpack_from('<f',raw,offset)[0]
        struct.pack_into('<f',raw,offset,old+0.001)
        self.binary=bytes(raw)
        result=self.finish_mutation()
        row=next(e for e in result['referenced_semantic_accessors'] if e['path']=='meshes/0/primitives/0/attributes/NORMAL')
        self.assertEqual(row['changed_components'],1)
    def test_nonfinite_animation_rejected_by_actual_validator(self):
        idx=self.doc['animations'][0]['samplers'][0]['output']
        acc=self.doc['accessors'][idx]
        view=self.doc['bufferViews'][acc['bufferView']]
        offset=view.get('byteOffset',0)+acc.get('byteOffset',0)
        raw=bytearray(self.binary)
        struct.pack_into('<f',raw,offset,float('nan'))
        self.binary=bytes(raw)
        write_glb(self.output/'nvwa-humanoid.glb',self.doc,self.binary)
        with self.assertRaises(AssertionError):
            compare(FIXTURE,self.output)

class ExactnessTests(unittest.TestCase):
    def test_shape_and_tail_differences_reported(self):
        result=numeric_delta([(1.0,2.0),(3.0,)],[(1.0,)])
        self.assertFalse(result['equal'])
        self.assertEqual(result['unpaired_components'],2)
        self.assertEqual(result['changed_components'],2)
        self.assertEqual(len(result['shape_differences']),2)
    def test_signed_zero_is_reported(self):
        result=numeric_delta([(0.0,)], [(-0.0,)])
        self.assertFalse(result['equal'])
        self.assertEqual(result['signed_zero_changes'],1)
    def test_triangle_winding_and_multiplicity_preserved(self):
        a=triangle_counts([(0,),(1,),(2,)])
        self.assertEqual(a,triangle_counts([(1,),(2,),(0,)]))
        self.assertNotEqual(a,triangle_counts([(0,),(2,),(1,)]))
        self.assertNotEqual(a,triangle_counts([(0,),(1,),(2,)]*2))

class HarnessFailureTests(unittest.TestCase):
    def test_comparator_failure_propagates(self):
        with tempfile.TemporaryDirectory(prefix='failure-test-',dir=PRIVATE) as temporary:
            script=Path(temporary)/'broken_comparator.py'
            script.write_text('raise SystemExit(7)\n')
            with patch.object(run_pair,'COMPARATOR',script):
                with self.assertRaises(subprocess.CalledProcessError) as raised:
                    run_pair.run_comparison(Path('left'),Path('right'),Path(temporary)/'result.json')
                self.assertEqual(raised.exception.returncode,7)

if __name__=='__main__':
    unittest.main()
