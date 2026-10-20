#!/usr/bin/env python3
"""Synthetic controls of actual authoring math/gate; never runtime/source proof."""
import copy
import unittest
from derive_target import closest_triangle, quaternion, rotate, verify_capture, InvalidEvidence, RejectedTarget, raw_f32_hash, jhash, expected_bounds

class AuthoringControls(unittest.TestCase):
    def test_closest_triangle_all_voronoi_regions(self):
        tri=([0.,0.,0.],[1.,0.,0.],[0.,1.,0.])
        cases=[([.2,.3,2],[.2,.3,0]), ([-1,-1,0],[0,0,0]),([2,-1,0],[1,0,0]),([-1,2,0],[0,1,0]),([.3,-1,0],[.3,0,0]),([-1,.3,0],[0,.3,0]),([1,1,0],[.5,.5,0])]
        for p,expected in cases:
            with self.subTest(p=p):
                q,b=closest_triangle(p,*tri)
                self.assertLess(max(abs(a-c) for a,c in zip(q,expected)),1e-12)
                self.assertAlmostEqual(sum(b),1);self.assertTrue(all(w>=0 for w in b))
    def test_degenerate_triangle_rejects(self):
        with self.assertRaises(RejectedTarget):closest_triangle([1,1,1],[0,0,0],[0,0,0],[1,0,0])
    def test_actual_frame_rotation_roundtrip(self):
        m=[0.,1.,0.,0.,-1.,0.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.]
        q=quaternion(m);v=rotate(q,[1.,0.,0.]);self.assertLess(max(abs(a-b) for a,b in zip(v,[0.,1.,0.])),1e-12)
        self.assertLess(max(abs(a-b) for a,b in zip(rotate([-q[0],-q[1],-q[2],q[3]],v),[1,0,0])),1e-12)
    def fixture(self):
        import hashlib
        sha=hashlib.sha256(b'{}').hexdigest()
        pos=[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]];norm=[[0.,0.,1.]]*3;inds=[0,1,2];transform=[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.]
        part={'name':'body','display_entity':'synthetic-body','mesh_handle':'synthetic-mesh','display_transform':transform,'positions':pos,'normals':norm,'indices':inds,'tangents':None,'source_ids':[0,1,2]}
        attrs=[{'id':str(i),'name':name,'format':'Float32x3','values':3,'raw_bytes_sha256':raw_f32_hash(rows)} for i,(name,rows) in enumerate([('Vertex_Position',pos),('Vertex_Normal',norm)])]
        mesh={'positions_sha256_le_f32':raw_f32_hash(pos),'normals_sha256_le_f32':raw_f32_hash(norm),'vertex_colors_sha256_le_f32':None,'vertex_count':3,'index_count':3,'index_format':'U32','primitive_topology':'TriangleList','indices_sha256':jhash(inds),'complete_rendered_attributes':attrs}
        actual={'role':'body','entity':'synthetic-body','production_mesh_handle':'synthetic-mesh','actual_render_mesh_handle':'synthetic-mesh','display_transform':transform,'buffers':mesh,'changed_mesh_exact_bounds':None,'inherited_production_no_frustum_culling':True,'actual_aabb':None,'computed_mesh_aabb':expected_bounds(pos),'material_handle':'synthetic-material','material_debug_sha256':'c'*64,'visibility':'Some(Inherited)'}
        buffer={'role':'body','entity':'synthetic-body','mesh_handle':'synthetic-mesh','display_transform':transform,'positions':pos,'normals':norm,'indices':inds,'uv_0':None}
        diagnostic={'palette':'Textured','targets':[{'role':'body','entity':'synthetic-body','mesh_handle':'synthetic-mesh','material_handle':'synthetic-material','isolation_hidden':False,'coverage_culling_policy_preserved':True,'production_material':{},'render_material':{},'visibility_original':'Some(Inherited)','visibility_actual':'Some(Inherited)'}]}
        pub={'target_sha256':None,'mode':'baseline','camera':{},'work_sha256':sha,'generation':1,'parts':[actual]};key='a'*64;w={'update_epoch':4,'publication':{'key_sha256':key,'actual':pub}}
        s={'mode':'baseline','target_active':False,'target_authored':None,'pre_visibility_publication_matches':True,'publication_key_sha256':key,'actual_render_publication':pub,'pre_visibility_witness':w,'Last_independent_witness':{**copy.deepcopy(w),'pre_visibility_publication_matches':True}}
        import hashlib
        sha=hashlib.sha256(b'{}').hexdigest();f={'endpoint':'web','request_id':'synthetic-only','work_sha256':sha,'identity':{'camera':{}},'camera':{},'base':{},'capture_update_epoch':4,'stable_updates':2,'source_diagnostic':s,'full_base':{'generation':1,'parts':[part]},'buffers':[buffer],'diagnostic':diagnostic}
        r={'endpoint':'web','phase':'ready','current':True,'acknowledged':True,'request_succeeded':True,'request_id':'synthetic-only','work_json':'{}','work_sha256':sha,'captured_identity':f['identity'],'camera':{},'base':{},'source_diagnostic':s,'capture_update_epoch':4,'stable_updates':2}
        c={'stage_rules':{'combined':{'source_equals':{'mode':'baseline','target_active':False,'target_authored':None,'pre_visibility_publication_matches':True},'required_source_keys':['publication_key_sha256','actual_render_publication','pre_visibility_witness','Last_independent_witness']}}}
        return {'report':r,'frame':f},c
    def test_called_source_gate_rejects_unbound_publication_metadata(self):
        for field,value in [('camera',{'wrong':True}),('generation',999),('work_sha256','bad'),('parts',[])]:
            e,c=self.fixture();source=e['frame']['source_diagnostic'];source['actual_render_publication'][field]=value
            for key in ('pre_visibility_witness','Last_independent_witness'):source[key]['publication']['actual']=source['actual_render_publication']
            with self.subTest(field=field),self.assertRaises(InvalidEvidence):verify_capture(e,'combined','synthetic-only',c)
    def test_called_source_gate_rejects_actual_part_binding_and_buffer_mutations(self):
        cases=[('entity','wrong'),('production_mesh_handle','wrong'),('actual_render_mesh_handle','wrong'),('display_transform',[0.]*16),('changed_mesh_exact_bounds',True),('inherited_production_no_frustum_culling',False),('material_handle','wrong')]
        for field,value in cases:
            e,c=self.fixture();source=e['frame']['source_diagnostic'];source['actual_render_publication']['parts'][0][field]=value
            for key in ('pre_visibility_witness','Last_independent_witness'):source[key]['publication']['actual']=source['actual_render_publication']
            with self.subTest(field=field),self.assertRaises(InvalidEvidence):verify_capture(e,'combined','synthetic-only',c)
        e,c=self.fixture();source=e['frame']['source_diagnostic'];source['actual_render_publication']['parts'][0]['buffers']['complete_rendered_attributes'][0]['raw_bytes_sha256']='b'*64
        for key in ('pre_visibility_witness','Last_independent_witness'):source[key]['publication']['actual']=source['actual_render_publication']
        with self.assertRaises(InvalidEvidence):verify_capture(e,'combined','synthetic-only',c)
    def test_quaternion_rejects_unit_column_shear(self):
        with self.assertRaises(InvalidEvidence):quaternion([1.,0.,0.,0.,.6,.8,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.])
    def test_called_source_gate_rejects_missing_stability_wrong_epoch_publication_and_target(self):
        original,c=self.fixture();verify_capture(original,'combined','synthetic-only',c)
        for mutation in ('stable','epoch','publication','target','request','work'):
            e=copy.deepcopy(original)
            if mutation=='stable':e['frame']['stable_updates']=1;e['report']['stable_updates']=1
            if mutation=='epoch':e['frame']['source_diagnostic']['pre_visibility_witness']['update_epoch']=3
            if mutation=='publication':e['frame']['source_diagnostic']['Last_independent_witness']['publication']['key_sha256']='b'*64
            if mutation=='target':e['frame']['source_diagnostic']['actual_render_publication']['target_sha256']='b'*64
            if mutation=='request':e['frame']['request_id']='different'
            if mutation=='work':e['report']['work_json']='{ }'
            with self.subTest(mutation=mutation),self.assertRaises(InvalidEvidence):verify_capture(e,'combined','synthetic-only',c)

if __name__=='__main__':unittest.main()
