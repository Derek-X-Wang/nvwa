#!/usr/bin/env python3
"""Mutation-red controls exercise actual constructor and independent gate."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import candidate as c
import evaluate as e

class CandidateControls(unittest.TestCase):
    records=[]
    @classmethod
    def setUpClass(cls):
        cls.directory=c.ROOT/'.work/m2-neutral-ab/failed-controls'
        cls.directory.mkdir(parents=True,exist_ok=True)
    def reject_bytes(self,mode,reason):
        data,_=c.construct(mode)
        path=self.directory/(mode+'.glb');path.write_bytes(data)
        with self.assertRaisesRegex(ValueError,reason) as rejected:
            e.gate(path)
        self.records.append({'control':mode,'status':'REJECTED','error':str(rejected.exception),'failed_glb_sha256':c.sha(data),
                             'retained_private_path':'.work/m2-neutral-ab/failed-controls/'+mode+'.glb'})
    def test_01_reversed_multiplication(self):self.reject_bytes('reversed_multiplication','source chest direction component gate')
    def test_02_double_correction(self):self.reject_bytes('double_correction','source chest direction component gate')
    def test_03_correct_descendants(self):self.reject_bytes('correct_descendants','untouched channels/root/geometry bytes')
    def test_04_wrong_physical_sides(self):self.reject_bytes('wrong_physical_sides','source chest direction component gate')
    def test_05_duplicated_root(self):self.reject_bytes('duplicated_root','untouched channels/root/geometry bytes')
    def test_06_animated_key0_neutral(self):
        _,_,doc,_,cal,source=c.inputs();source=copy.deepcopy(source)
        source['rest_local_rotations_xyzw']=[list(q) for q in e.source_frames()[1][0]]
        with self.assertRaisesRegex(ValueError,'pinned static source rest') as rejected:c.construct(source=source)
        self.records.append({'control':'animated_key0_neutral','status':'REJECTED','error':str(rejected.exception)})
    def test_07_changed_parent(self):
        _,_,doc,_,_,_=c.inputs();doc=copy.deepcopy(doc)
        doc['nodes'][8]['children'].remove(4);doc['nodes'][9]['children'].append(4)
        with self.assertRaisesRegex(ValueError,'exact pinned target hierarchy') as rejected:c.construct(doc=doc)
        self.records.append({'control':'changed_parent','status':'REJECTED','error':str(rejected.exception)})
    def test_08_changed_chest_frame(self):
        _,_,doc,_,_,_=c.inputs();doc=copy.deepcopy(doc);doc['nodes'][8]['scale']=[1,2,1]
        with self.assertRaisesRegex(ValueError,'exact pinned target hierarchy') as rejected:c.construct(doc=doc)
        self.records.append({'control':'changed_chest_frame','status':'REJECTED','error':str(rejected.exception)})
    def test_09_changed_static_frame(self):
        _,_,_,_,cal,_=c.inputs();cal=copy.deepcopy(cal)
        row=next(r for r in cal['rows'] if r['target']=='upper_arm.L');row['source_frame']=c.math47.I
        with self.assertRaisesRegex(ValueError,'pinned static geometric frames') as rejected:c.construct(calibration=cal)
        self.records.append({'control':'changed_static_frame','status':'REJECTED','error':str(rejected.exception)})
    def test_10_restored_candidate(self):
        path=self.directory/'restored-candidate.glb';path.write_bytes(c.construct()[0]);result=e.gate(path)
        self.assertEqual(result['gate']['keys'],90);self.assertEqual(result['gate']['directions'],180)
        self.records.append({'control':'restored_candidate','status':result['status'],'gate':result['gate']})
    def test_11_additional_upper_arm_roll_is_not_admitted(self):
        import math,struct
        data,_=c.construct();doc,binary=c.export48.decode_glb(data);binary=bytearray(binary)
        channel=next(x for x in doc['animations'][3]['channels'] if x['target']=={'node':4,'path':'rotation'})
        accessor=doc['accessors'][doc['animations'][3]['samplers'][channel['sampler']]['output']]
        view=doc['bufferViews'][accessor['bufferView']];offset=view.get('byteOffset',0)+accessor.get('byteOffset',0)
        rotation=c.math47.rotation(list(struct.unpack_from('<4f',binary,offset)))
        roll=c.math47.rotation([0.,math.sin(.05),0.,math.cos(.05)])
        struct.pack_into('<4f',binary,offset,*c.export48.quaternion(c.math47.mm(rotation,roll)))
        changed=c.export48.pack_glb(doc,bytes(binary));path=self.directory/'extra_per_key_roll.glb';path.write_bytes(changed)
        with self.assertRaisesRegex(ValueError,'exact frozen candidate rotation bytes') as rejected:e.gate(path)
        self.records.append({'control':'extra_per_key_roll','status':'REJECTED','error':str(rejected.exception),'failed_glb_sha256':c.sha(changed)})
    def test_12_known_fk_conventions(self):
        q=[0,0,2**-.5,2**-.5]
        v=e.D.mv(e.D.qr(q),[1,0,0])
        self.assertLess(max(abs(x-y) for x,y in zip(v,[0,1,0])),1e-14)
        meta={'parents':[-1,0],'rest_local_translations':[[0,0,0],[1,0,0]]}
        _,p=e.D.fk(meta,[q,[0,0,0,1]],[2,3,4]);self.assertLess(max(abs(x-y) for x,y in zip(p[1],[2,4,4])),1e-14)
        self.records.append({'control':'known_positive_z90_and_parent_child_transport','status':'PASS'})

if __name__=='__main__':
    import sys
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(CandidateControls)
    outcome=unittest.TextTestRunner(verbosity=2).run(suite)
    output=c.ROOT/'.work/m2-neutral-ab'/('controls-optimized.json' if sys.flags.optimize else 'controls-normal.json')
    output.write_text(json.dumps({'all_passed':outcome.wasSuccessful(),'tests':outcome.testsRun,'controls':CandidateControls.records},indent=2)+'\n')
    raise SystemExit(0 if outcome.wasSuccessful() else 1)
