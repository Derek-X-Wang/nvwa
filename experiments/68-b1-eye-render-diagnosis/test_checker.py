"""Synthetic tool regressions; these are not runtime/render/asset evidence."""
import copy
import json
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('checker_under_test', Path(__file__).with_name('check_captures.py'))
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)
IDENTITY = [1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.]
WHITE = 'LinearRgba(LinearRgba { red: 1.0, green: 1.0, blue: 1.0, alpha: 1.0 })'
CYAN = 'Srgba(Srgba { red: 0.0, green: 1.0, blue: 1.0, alpha: 1.0 })'
MAGENTA = 'Srgba(Srgba { red: 1.0, green: 0.0, blue: 1.0, alpha: 1.0 })'

def render_material(before, role, palette):
    after = before.copy()
    if palette != 'Textured' and role in ('body', 'eyes'):
        after['unlit'] = True
        if palette == 'RoleTint':
            after['base_color'] = CYAN if role == 'body' else MAGENTA
        after['full_standard_material_debug'] = before['full_standard_material_debug'].replace('base_color: '+before['base_color'], 'base_color: '+after['base_color']).replace('unlit: false', 'unlit: true')
    return after

def envelope(identifier, mode='Combined', palette='Textured', endpoint='native', witness=False, seconds=2):
    # Counts match the pinned admitted topology only in shoulder fixtures.
    sample = {'source_seconds':seconds,'position_seconds':seconds,'playing':False,'clip_id':'b1_arm_rehearsal_v1','serial':1}
    shape = {'torso_length':1. if witness else -1.,'jaw_drop':0.}
    targets, buffers, parts, summaries = [], [], [], []
    for role in ('body','garment','eyes','hair'):
        count, index_count = CHECKER.PART_COUNTS[role] if witness and role in CHECKER.PART_COUNTS else (3,3)
        positions = [[0.,0.,0.]] * count
        normals = [[0.,0.,1.]] * count
        triangles = [0,1,2] * (index_count//3)
        buffer = {'role':role,'entity':'entity-'+role,'mesh_handle':'mesh-'+role,'positions':positions,'normals':normals,'uv_0':None if role=='garment' else [[0.,0.]]*count,'indices':triangles,'display_transform':IDENTITY.copy()}
        buffers.append(buffer)
        before = {'base_color_texture':'image-'+role,'alpha_mode':'Mask(0.5)','cull_mode':'Some(Back)','double_sided':False,'roughness':0.7,'metallic':0.,'base_color':WHITE,'unlit':False,'full_standard_material_debug':'StandardMaterial { base_color: '+WHITE+', unlit: false, other_fields: retained }'}
        hidden = (mode=='BodyOnly' and role!='body') or (mode=='EyeOnly' and role!='eyes')
        targets.append({'role':role,'entity':'entity-'+role,'mesh_handle':'mesh-'+role,'material_handle':'material-'+role,'coverage_culling_policy_preserved':True,'production_material':before,'render_material':render_material(before,role,palette),'isolation_hidden':hidden,'visibility_original':'Some(Inherited)','visibility_actual':'Some(Hidden)' if hidden else 'Some(Inherited)','inherited_visibility':not hidden,'view_visibility':not hidden})
        if role in CHECKER.PART_COUNTS:
            parts.append({'name':role,'display_entity':'entity-'+role,'mesh_handle':'mesh-'+role,'positions':positions,'normals':normals,'tangents':[[1.,0.,0.,1.]]*count,'rest_positions':positions,'rest_normals':normals,'full_joint_influences':[[[0,1.]]]*count,'source_ids':list(range(count)),'indices':triangles,'display_transform':IDENTITY.copy(),'model_to_world':IDENTITY.copy()})
            summaries.append({'name':role,'vertices':count,'indices':index_count})
    diagnostic = {'mode':mode,'palette':palette,'production_appearance_controller_enabled':True,'visibility_prepared_before_postupdate':True,'targets':targets}
    identity = {'environment':{'lights':'fixed'}}
    base = {'sample':sample,'parameters':shape,'bones_sha256':'bones','parts':summaries}
    frame = {'endpoint':endpoint,'fixed_case':'long_front_shoulder' if witness else 'short_front','request_id':identifier,'identity':identity,'work_sha256':'fixed-work','camera':{'active':True,'global_transform':IDENTITY.copy(),'projection':'fixed-projection','sub_camera_view':'Some(fixed-subview)','viewport':[1280,720],'msaa':'Sample4'},'base':base,'full_base':{'sample':sample,'parameters':shape,'parts':parts,'bones':[{'name':str(n),'skin':IDENTITY.copy()} for n in range(53)]},'buffers':buffers,'diagnostic':diagnostic}
    return {'report':{'endpoint':endpoint,'phase':'ready','acknowledged':True,'current':True,'request_succeeded':True,'request_id':identifier,'captured_identity':identity,'work_sha256':'fixed-work','diagnostic':diagnostic},'frame':frame}

def matrix(endpoint='native'):
    return [envelope('matrix-'+str(i),mode,palette,endpoint) for i,(mode,palette) in enumerate((m,p) for m in CHECKER.MODES for p in CHECKER.PALETTES)]

class EyeAcceptance(unittest.TestCase):
    def test_complete_native_and_web_three_by_three_sets_pass_separately(self):
        for endpoint in ('native','web'):
            result=CHECKER.compare(matrix(endpoint));self.assertTrue(result['complete_matrix']);self.assertEqual(result['endpoint'],endpoint)
    def test_review_single_combined_fixture_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'capture set'):CHECKER.compare([envelope('single')])
    def test_review_body_only_visible_eyes_counterexample_rejects(self):
        values=matrix();target=values[3]['frame']['diagnostic']['targets'][2];self.assertEqual(target['role'],'eyes');target['isolation_hidden']=False
        with self.assertRaisesRegex(ValueError,'isolation'):CHECKER.compare(values)
    def test_missing_duplicate_controls_and_duplicate_ids_reject(self):
        for change in ('missing','duplicate_control','duplicate_id','mixed_endpoint'):
            values=matrix()
            if change=='missing':values.pop()
            elif change=='duplicate_control':values[-1]=envelope('different-id')
            elif change=='duplicate_id':values[-1]['report']['request_id']=values[-1]['frame']['request_id']=values[0]['frame']['request_id']
            else:values[-1]['frame']['endpoint']=values[-1]['report']['endpoint']='web'
            with self.subTest(change=change),self.assertRaises(ValueError):CHECKER.compare(values)
    def test_stale_unacknowledged_mismatched_and_incomplete_roles_reject(self):
        for change in ('stale','unacknowledged','id','missing_role','duplicate_role','missing_buffer','wrong_handle'):
            values=matrix();bad=values[-1]
            if change=='stale':bad['report']['current']=False
            elif change=='unacknowledged':bad['report']['acknowledged']=False
            elif change=='id':bad['frame']['request_id']='wrong'
            elif change=='missing_role':bad['frame']['diagnostic']['targets'].pop()
            elif change=='duplicate_role':bad['frame']['diagnostic']['targets'][-1]['role']='eyes'
            elif change=='missing_buffer':bad['frame']['buffers'].pop()
            else:bad['frame']['buffers'][0]['mesh_handle']='wrong'
            with self.subTest(change=change),self.assertRaises(ValueError):CHECKER.compare(values)
    def test_palette_requires_correct_unlit_tint_and_preserved_other_fields(self):
        for change in ('missing_unlit','wrong_tint','tint_alpha','coverage','hidden_visible','changed_debug_field'):
            values=matrix();target=values[-1]['frame']['diagnostic']['targets'][0]
            if change=='missing_unlit':target['render_material']['unlit']=False
            elif change=='wrong_tint':target['render_material']=render_material(target['production_material'],'eyes','RoleTint')
            elif change=='tint_alpha':target['render_material']['base_color']=CYAN.replace('alpha: 1.0','alpha: 0.0')
            elif change=='coverage':target['render_material']['alpha_mode']='Opaque'
            elif change=='hidden_visible':target['view_visibility']=True
            else:target['render_material']['full_standard_material_debug']+=' undeclared'
            with self.subTest(change=change),self.assertRaises(ValueError):CHECKER.compare(values)
    def test_geometry_camera_and_missing_subcamera_reject(self):
        for change in ('geometry','camera','subcamera'):
            values=matrix();bad=values[-1]['frame']
            if change=='geometry':bad['buffers'][0]['positions'][0]=[99.,0.,0.]
            elif change=='camera':bad['camera']['projection']='changed'
            else:bad['camera']['sub_camera_view']=''
            with self.subTest(change=change),self.assertRaises(ValueError):CHECKER.compare(values)

class ShoulderAcceptance(unittest.TestCase):
    def pair(self):return [envelope('shoulder0',witness=True,seconds=0),envelope('shoulder2',witness=True,seconds=2)]
    def test_complete_pair_with_admitted_counts_and_all_arrays_passes(self):
        result=CHECKER.witness(self.pair());self.assertTrue(result['complete_pair']);self.assertTrue(result['full_arrays_retained'])
    def test_actual_raw_aggregate_rows_pass_unchanged_without_sum_one_assumption(self):
        fixture=json.loads(Path(__file__).with_name('raw-influence-golden.json').read_text())
        self.assertEqual(fixture['source_capture_sha256'],'9cde54133d6b24eca8dfa155105c5c9ae7c9d2085e769d5978c22e8cfc184ef6')
        self.assertEqual({(r['role'],r['render_vertex']) for r in fixture['records']},{('body',4459),('garment',422)})
        values=self.pair()
        for record in fixture['records']:
            raw=record['raw_positive_aggregates']
            self.assertEqual(sum(w for _,w in raw),record['sum_as_f64'])
            self.assertGreater(abs(sum(w for _,w in raw)-1.),1e-5)
            for value in values:
                part=next(p for p in value['frame']['full_base']['parts'] if p['name']==record['role'])
                part['full_joint_influences'][record['render_vertex']]=copy.deepcopy(raw)
        retained=copy.deepcopy(values)
        self.assertTrue(CHECKER.witness(values)['complete_pair'])
        self.assertEqual(values,retained)  # Checker must not normalize exported arrays.
    def test_malformed_raw_positive_aggregate_rows_still_reject(self):
        for row in ([],[[0,0.]],[[0,-1.]],[[0,float('nan')]],[[0,float('inf')]],
                    [[0,1.],[0,0.1]],[[53,1.]],[[True,1.]],[[0,1e308],[1,1e308]]):
            values=self.pair();values[1]['frame']['full_base']['parts'][0]['full_joint_influences'][0]=row
            with self.subTest(row=row),self.assertRaises(ValueError):CHECKER.witness(values)
    def test_review_empty_parts_single_source0_fixture_rejects(self):
        value=envelope('empty-0',witness=True,seconds=0);value['frame']['full_base']['parts']=[]
        with self.assertRaisesRegex(ValueError,'capture set'):CHECKER.witness([value])
    def test_missing_duplicate_or_mixed_time_pair_rejects(self):
        for change in ('missing','duplicate_time','duplicate_id','mixed_endpoint'):
            values=self.pair()
            if change=='missing':values.pop()
            elif change=='duplicate_time':values[1]=envelope('distinct0',witness=True,seconds=0)
            elif change=='duplicate_id':values[1]['report']['request_id']=values[1]['frame']['request_id']='shoulder0'
            else:values[1]['report']['endpoint']=values[1]['frame']['endpoint']='web'
            with self.subTest(change=change),self.assertRaises(ValueError):CHECKER.witness(values)
    def test_missing_duplicate_empty_truncated_and_inconsistent_body_garment_arrays_reject(self):
        for change in ('missing_body','duplicate_garment','empty_parts','empty_positions','truncated_normals','truncated_indices','truncated_weights','empty_weight_row','bad_source_ids','bad_index','bad_binding','wrong_count'):
            values=self.pair();bad=values[1]['frame'];part=bad['full_base']['parts'][1]
            if change=='missing_body':bad['full_base']['parts'].pop(0)
            elif change=='duplicate_garment':bad['full_base']['parts'][0]['name']='garment'
            elif change=='empty_parts':bad['full_base']['parts']=[]
            elif change=='empty_positions':part['positions']=[]
            elif change=='truncated_normals':part['normals']=part['normals'][:-1]
            elif change=='truncated_indices':part['indices']=part['indices'][:-3]
            elif change=='truncated_weights':part['full_joint_influences']=part['full_joint_influences'][:-1]
            elif change=='empty_weight_row':part['full_joint_influences'][0]=[]
            elif change=='bad_source_ids':part['source_ids']=part['source_ids'][:-1]
            elif change=='bad_index':part['indices'][0]=999999
            elif change=='bad_binding':part['display_entity']='wrong'
            else:bad['base']['parts'][1]['vertices']=1
            with self.subTest(change=change),self.assertRaises(ValueError):CHECKER.witness(values)
    def test_noncombined_palette_and_nonfinite_arrays_reject(self):
        values=self.pair();values[1]=envelope('wrong-palette',mode='EyeOnly',palette='UnlitTextured',witness=True,seconds=2)
        with self.assertRaises(ValueError):CHECKER.witness(values)
        values=self.pair();values[1]['frame']['full_base']['parts'][1]['rest_positions'][0]=[float('nan'),0.,0.]
        with self.assertRaises(ValueError):CHECKER.witness(values)

if __name__=='__main__':unittest.main()
