"""Offline controls. Synthetic B records are never Web/runtime/image evidence."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from PIL import Image
from source_check import EXP, ROOT, B_HASHES, RGBA, replay, source, numeric
from validate import validate, hashes

FIXTURE=Path('/Users/derekxwang/.codex/work-products/nvwa/2026-10-19-source-export-followup/retained-hairline-export79/actual/h79e80-auto-v2/capture.json')
FIXTURE_SHA='d79f44812cd6b840bd8d4f15d71b9f4d886ccc05bce062ea5be5232916c6f4d2'
_CACHE=None

def records():
    global _CACHE
    if _CACHE is None:
        raw=FIXTURE.read_bytes();numeric.require(hashlib.sha256(raw).hexdigest()==FIXTURE_SHA,'fixed historical capture authentication failed')
        a=json.loads(raw)
        b=copy.deepcopy(a);b['report']['request_id']=b['frame']['request_id']='synthetic-short01-B'
        c=b['frame']['candidate'];e=replay(b['frame']['full_base'],'b');obj,_,_=source('b')
        c.update(variant='BShort01',source_vertices=2984,render_vertices=3177,triangles=3678,
                 source_uv_pairs=[list(x) for x in obj['pairs']],rest_source_positions=e['rest'],rest_source_normals=e['rest_normals'],
                 full_positive_source_weights=[[[j,w] for j,w in row] for row in e['weights']],source_scales=e['scales'],
                 decoded_rgba_sha256=RGBA['b'],actual_aabb={'synthetic':True})
        hair=next(h for h in b['frame']['buffers'] if h['role']=='hair')
        hair.update(positions=e['positions'],normals=e['normals'],uv_0=e['uv_0'],indices=e['indices'],source_map=json.loads((EXP/'works/b-short01-source-map.json').read_text()))
        hair['bound_image']['decoded_rgba_sha256']=RGBA['b']
        for key in ['positions','normals']:
            c['published_'+key+'_sha256']=hashes.mesh_array_sha256(e[key])
            c['pre_visibility_publication'][key+'_sha256']=c['published_'+key+'_sha256']
        hair['positions_sha256']=c['published_positions_sha256']
        c['pre_visibility_publication'].update(variant='BShort01',image_rgba_sha256=RGBA['b'])
        a2=copy.deepcopy(a);a2['report']['request_id']=a2['frame']['request_id']='synthetic-A-restored'
        a2['frame']['stable_updates']+=1
        _CACHE=[a,b,a2]
    return copy.deepcopy(_CACHE)

class Source(unittest.TestCase):
    def test_source_identity_counts_and_exact_diffuse(self):
        info=json.loads((EXP/'SOURCE.json').read_text())
        self.assertEqual(info['files'],B_HASHES)
        m=(EXP/'candidate/short01/short01.mhclo').read_text()
        self.assertIn('uuid 766436e9-63ed-4f6a-afa9-99f3acff70a8',m);self.assertIn('basemesh hm08',m)
        entry=json.loads((EXP/'candidate/short01/makehuman_system_assets.json').read_text())['short01']
        self.assertEqual(info['identity']['pack_entry'],entry);self.assertEqual(entry['license'],'CC0');self.assertEqual(entry['type'],'hair')
        self.assertIn('diffuseTexture short01_diffuse.png',(EXP/'candidate/short01/short01.mhmat').read_text())
        im=Image.open(EXP/'candidate/short01/short01_diffuse.png').convert('RGBA')
        self.assertEqual(im.size,(2048,2048));self.assertEqual(hashlib.sha256(im.tobytes()).hexdigest(),RGBA['b'])
        obj,rows,scales=source('b')
        self.assertEqual((obj['count'],obj['uv_rows'],obj['faces'],len(obj['indices'])//3,len(obj['pairs'])),(2984,3177,1839,3678,3177))
        self.assertEqual(sum(any(c<0 for c in coeff) for ids,coeff,offset in rows),501)
        self.assertEqual(sum(c<0 for ids,coeff,offset in rows for c in coeff),549)
        self.assertEqual({i for i,t in obj['pairs']},set(range(2984)))

    def test_source_specific_record_replay_and_exact_restoration_pass(self):
        self.assertEqual(validate(records())['result'],'PASS')

    def test_every_other_surface_work_camera_bones_policy_change_rejects(self):
        for field in ['camera','full_base','appearance','base','identity','diagnostic','work_sha256']:
            r=records();r[1]['frame'][field]=None
            with self.assertRaises((ValueError,TypeError,KeyError),msg=field):validate(r)
        for role in ['body','garment','eyes']:
            r=records();next(x for x in r[1]['frame']['buffers'] if x['role']==role)['positions'][0][0]+=.001
            with self.assertRaises(ValueError,msg=role):validate(r)
        for field in ['actual_image_sampler','actual_image_policy','original_standard_material_debug','display_transform','bones']:
            r=records();r[1]['frame']['candidate'][field]=None
            with self.assertRaises(ValueError,msg=field):validate(r)
        r=records();next(x for x in r[1]['frame']['buffers'] if x['role']=='hair')['bound_image']['sampler']='changed'
        with self.assertRaises(ValueError):validate(r)

    def test_false_b_identity_and_b_upload_source_changes_reject(self):
        for field in ['rest_source_positions','rest_source_normals','source_uv_pairs','full_positive_source_weights']:
            r=records();r[1]['frame']['candidate'][field]=r[1]['frame']['candidate'][field][:-1]
            with self.assertRaises(ValueError,msg=field):validate(r)
        for field in ['positions','normals','uv_0','indices']:
            r=records();hair=next(x for x in r[1]['frame']['buffers'] if x['role']=='hair');hair[field]=hair[field][:-1]
            with self.assertRaises(ValueError,msg=field):validate(r)
        for field in ['rest_source_positions','rest_source_normals']:
            r=records();r[1]['frame']['candidate'][field][0][0]=float('nan')
            with self.assertRaises(ValueError,msg=field):validate(r)
        r=records();r[1]['frame']['candidate']['decoded_rgba_sha256']=RGBA['a']
        with self.assertRaises(ValueError):validate(r)
        r=records();r[1]['frame']['candidate']['source_vertices']=865
        with self.assertRaises(ValueError):validate(r)
        r=records();r[1]['frame']['candidate']['full_positive_source_weights'][0][0][1]*=.9
        with self.assertRaises(ValueError):validate(r)
        # Self-consistent new B position hashes are still rejected by source replay.
        r=records();c=r[1]['frame']['candidate'];hair=next(x for x in r[1]['frame']['buffers'] if x['role']=='hair');hair['positions'][0][0]=numeric.f32(hair['positions'][0][0]+.001)
        digest=hashes.mesh_array_sha256(hair['positions']);hair['positions_sha256']=c['published_positions_sha256']=c['pre_visibility_publication']['positions_sha256']=digest
        with self.assertRaises(ValueError):validate(r)

    def test_source_unit_and_signed_controls_detect_changed_fit(self):
        base=records()[0]['frame']['full_base'];b=replay(base,'b')
        bad=replay(base,'b',clamp_signed=True)
        self.assertGreater(max(abs(x-y) for a,c in zip(b['rest'],bad['rest']) for x,y in zip(a,c)),1e-6)
        def twice_converted_offsets(which):
            obj,rows,scales=source(which)
            return obj,[(ids,c,[x*.1 for x in offset]) for ids,c,offset in rows],scales
        numeric.source=twice_converted_offsets
        try:bad=numeric.replay(base,'b')
        finally:numeric.source=source
        self.assertGreater(max(abs(x-y) for a,c in zip(b['rest'],bad['rest']) for x,y in zip(a,c)),1e-6)
        self.assertTrue(all(all(w>0 for j,w in row) and abs(sum(w for j,w in row)-1)<1e-12 for row in b['weights']))

    def test_failed_a_restoration_rejects(self):
        r=records();r[2]['frame']['candidate']['decoded_rgba_sha256']=RGBA['b']
        with self.assertRaises(ValueError):validate(r)
        r=records();r[2]['frame']['camera']=None
        with self.assertRaises(ValueError):validate(r)

if __name__=='__main__':unittest.main()
