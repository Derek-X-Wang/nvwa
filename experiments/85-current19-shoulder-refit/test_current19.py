"""Synthetic stream identity controls; actual source/FK/geometry is NOT-RUN here."""
import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
import current19 as c

RUN='synthetic-controls-not-capture'


def record(case):
    recipe=c.expected(case)
    if case==c.ANCHOR:
        work=c.strict_load((c.ROOT/c.WORK_PATH).read_bytes())
    else:
        work={'profile':{'id':recipe['profile_id'],'backend':recipe['backend'],
                         'asset_path':c.V1_ASSET_PATH,'asset_sha256':c.V1_ASSET_SHA},
              'character':{'profile_id':recipe['profile_id'],'parameters':recipe['parameters'],'diagnostic_pose':'neutral'},
              'revision':1,'timeline':[{'id':recipe['timeline_id'],'clip_id':recipe['clip_id'],
                                       'start_seconds':0,'duration_seconds':4,'speed':1,'looping':False}]}
    return {'kind':'sample','run_id':RUN,'case':case,'request':recipe,'work':work,
            'snapshot':{'schema_version':1,'mode':'motion','generation':2 if case==c.ANCHOR else 1,'revision':work['revision'],
                        'diagnostic_pose':'neutral','character_entity':'rootv0',
                        'profile_id':recipe['profile_id'],'backend':recipe['backend'],
                        'asset_id':recipe['backend']['asset_id'],'parameters':recipe['parameters'],
                        'sample':{'serial':1,'clip_id':recipe['clip_id'],
                                  'timeline_id':recipe['timeline_id'],'playing':False,'completed':False,
                                  'position_seconds':recipe['seconds'],'source_seconds':recipe['seconds']},
                        'bones':[{'name':str(i),'parent':None,**{field:[float(j%5==0) for j in range(16)]
                                  for field in ('rest','posed','inverse_bind','skin','canonical_rest','canonical_posed',
                                                'frame_gauge','local_rest','local_posed')}} for i in range(53)],
                        'parts':[{'name':name,'display_entity':name+'v0','mesh_handle':name+'mesh'}
                                 for name in ('body','garment')]}}


def rows():
    return [copy.deepcopy(record(case)) for case in c.CASES]+[
        {'kind':'complete','run_id':RUN,'samples':19,'cases':list(c.CASES)}]


def encoded(data):
    return [c.PREFIX+json.dumps(row,separators=(', ', ' : '))+'\n' for row in data]


class StreamControls(unittest.TestCase):
    def collect(self,data,out):
        return c.collect(encoded(data),out,RUN)

    def reject(self,mutate):
        data=rows();mutate(data)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises((ValueError,KeyError,TypeError,IndexError)):
                self.collect(data,Path(d))

    def test_lossless19_and_separate_identity(self):
        with tempfile.TemporaryDirectory() as d:
            entries=self.collect(rows(),Path(d))
            self.assertEqual(len(entries),19)
            self.assertEqual(gzip.decompress((Path(d)/entries[-1]['path']).read_bytes()),
                             encoded(rows())[-2][len(c.PREFIX):].encode())
            self.assertNotEqual(c.expected(c.ANCHOR),c.expected(c.case_name((0,c.ARM,16))))

    def test_missing(self):self.reject(lambda x:x.pop(3))
    def test_duplicate(self):self.reject(lambda x:x.insert(1,copy.deepcopy(x[0])))
    def test_misordered(self):self.reject(lambda x:x.__setitem__(slice(0,2),x[1::-1]))
    def test_mixed_run(self):self.reject(lambda x:x[0].update(run_id='other'))
    def test_request_time(self):self.reject(lambda x:x[0]['request'].update(seconds=2))
    def test_snapshot_time(self):self.reject(lambda x:x[0]['snapshot']['sample'].update(source_seconds=2))
    def test_bool_k(self):self.reject(lambda x:x[0]['request'].update(k=False))
    def test_wrong_profile(self):self.reject(lambda x:x[-2]['snapshot'].update(profile_id='nvwa-mpfb-b1-motion-v1'))
    def test_wrong_backend(self):self.reject(lambda x:x[-2]['snapshot']['backend'].update(schema_version=2))
    def test_wrong_entry(self):self.reject(lambda x:x[-2]['snapshot']['sample'].update(timeline_id='probe-entry'))
    def test_legacy_copied_as19(self):
        def change(x):
            x[-2]=copy.deepcopy(x[8]);x[-2]['case']=c.ANCHOR
        self.reject(change)
    def test_work_camera(self):self.reject(lambda x:x[-2]['work']['stage']['camera'].update(distance=1))
    def test_wrong_work_revision(self):self.reject(lambda x:x[0]['work'].update(revision=2))
    def test_missing_v1_asset_path(self):self.reject(lambda x:x[0]['work']['profile'].pop('asset_path'))
    def test_wrong_v1_asset_path(self):self.reject(lambda x:x[0]['work']['profile'].update(asset_path='characters/other/manifest.json'))
    def test_missing_v1_asset_hash(self):self.reject(lambda x:x[0]['work']['profile'].pop('asset_sha256'))
    def test_wrong_v1_asset_hash(self):self.reject(lambda x:x[0]['work']['profile'].update(asset_sha256='0'*64))
    def test_wrong_actual_parameters(self):self.reject(lambda x:x[-2]['snapshot']['parameters'].update(jaw_drop=1))
    def test_wrong_completion(self):self.reject(lambda x:x[-1].update(samples=18))
    def test_postcomplete(self):self.reject(lambda x:x.append(copy.deepcopy(x[0])))
    def test_nonfinite(self):self.reject(lambda x:x[0]['snapshot'].update(extra=float('nan')))
    def test_duplicate_json_key(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'duplicate JSON key'):
                c.collect([c.PREFIX+'{"kind":"sample","kind":"sample"}'],Path(d),RUN)

    def test_missing_character_entity(self):self.reject(lambda x:x[0]['snapshot'].pop('character_entity'))
    def test_wrong_character_entity_type(self):self.reject(lambda x:x[0]['snapshot'].update(character_entity=4))
    def test_wrong_pose(self):self.reject(lambda x:x[0]['snapshot'].update(diagnostic_pose='elbow'))
    def test_missing_display_entity(self):self.reject(lambda x:x[0]['snapshot']['parts'][0].pop('display_entity'))
    def test_wrong_mesh_handle_type(self):self.reject(lambda x:x[0]['snapshot']['parts'][0].update(mesh_handle={} ))
    def test_local_posed_invalid_strings(self):self.reject(lambda x:x[0]['snapshot']['bones'][0].update(local_posed=['invalid']*16))
    def test_local_rest_wrong_size(self):self.reject(lambda x:x[0]['snapshot']['bones'][0].update(local_rest=[1]*15))
    def test_missing_local_posed(self):self.reject(lambda x:x[0]['snapshot']['bones'][0].pop('local_posed'))
    def test_each_bone_matrix_finite_schema(self):
        for field in ('rest','posed','inverse_bind','skin','canonical_rest','canonical_posed',
                      'frame_gauge','local_rest','local_posed'):
            with self.subTest(field=field):
                self.reject(lambda x:x[0]['snapshot']['bones'][0].update({field:[True]*16}))


class GeometryAggregationControls(unittest.TestCase):
    def test_all19_checked_after_early_and_late_failure(self):
        visited=[]
        def check(record):
            visited.append(record['case'])
            if record['case'] in (c.CASES[0],c.CASES[-1]):raise ValueError('synthetic red')
            return {'synthetic_geometry':'NOT-RUN'}
        report=c.audit_geometry(rows()[:-1],check)
        self.assertEqual(visited,list(c.CASES))
        self.assertEqual([r['case'] for r in report['failures']],[c.CASES[0],c.CASES[-1]])
        self.assertEqual(report['status'],'REJECT_CURRENT19_GEOMETRY')
    def test_budget_marks_unrun_and_rejects(self):
        report=c.audit_geometry(rows()[:-1],lambda _:self.fail('no budget'),budget_seconds=0)
        self.assertEqual(len(report['results']),19)
        self.assertTrue(all(r['status']=='NOT-RUN_BUDGET_EXHAUSTED' for r in report['results']))


if __name__=='__main__':unittest.main()
