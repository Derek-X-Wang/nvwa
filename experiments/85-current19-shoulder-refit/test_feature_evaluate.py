"""Synthetic admission/report controls. No actual candidate or corpus is scored."""
import argparse
import copy
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import current19 as c
import feature_evaluate as v


class CandidateAdmissionControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.source=self.root/'source';(self.source/'garment').mkdir(parents=True)
        self.original=(b'x_scale 0 1 1\ny_scale 0 1 1\nz_scale 0 1 1\nverts 0\n'
                       b'0 1 1 1 0 0 0 0 0\n0 1 1 1 0 0 0 0 0\ndelete_verts\n')
        (self.source/'garment/female_sportsuit01.mhclo').write_bytes(self.original)
        obj=b'synthetic topology reference only\n'
        (self.source/'garment/female_sportsuit01.obj').write_bytes(obj)
        self.original_sha=c.digest(self.original)
        self.obj_sha=c.digest(obj)
        for target,key,value in ((v.e,'SOURCE',self.source),
                                 (v.e,'SOURCE_MHCLO_SHA',self.original_sha),
                                 (v,'OBJ_SHA',self.obj_sha)):
            handle=patch.object(target,key,value);handle.start();self.addCleanup(handle.stop)
        self.attempt=self.root/'attempt';self.attempt.mkdir()
        self.candidate=self.attempt/'female_sportsuit01.mhclo'
        self.receipt_path=self.attempt/'authoring-receipt.json'
        self.manifest_path=self.attempt/'asset-manifest.json'
        lines=v.e.parse_mapping(self.original)['lines'][:]
        lines[4]='0 1 1 1 0 0 0 0 .001\n'
        self.candidate.write_bytes(''.join(lines).encode())
        self.freeze={'status':v.x.SCORING,'attempt_directory':str(self.attempt),
                     **{key:'a'*64 for key in v.IDENTITY_KEYS},
                     'candidate_id':v.x.CANDIDATE_ID,'cohort_kind':c.KIND,
                     'authoring_policy_version':4,
                     'previous_rejection':{'path':str(self.root/'synthetic-v3-rejection.json'),
                       'bytes':v.x.PREVIOUS_REJECTION_BYTES,'sha256':v.x.PREVIOUS_REJECTION_SHA},
                     'candidate_sha256':c.digest(self.candidate.read_bytes()),
                     'baseline_geometry_sha256':'b'*64,'independent_audit':{'sha256':'c'*64}}
        self.manifest={'schema_version':1,'kind':'nvwa85-current19-feature-offset-asset-manifest-v4',
                       'status':'ONE_CANDIDATE_FROZEN_NOT_SCORED','candidate_count':1,
                       **{key:self.freeze[key] for key in v.IDENTITY_KEYS},
                       'candidate_sha256':self.freeze['candidate_sha256'],
                       'mhclo_sha256':self.freeze['candidate_sha256'],
                       'original_mhclo_sha256':self.original_sha,'original_obj_sha256':self.obj_sha,
                       'representation':'MHCLO offsets only; original OBJ bytes unchanged',
                       'changed_source_ids':[0],'logical_sample_count':581,'face_constraint_count':1162}
        self.receipt={'schema_version':1,'kind':'nvwa85-current19-feature-authoring-receipt-v4',
                      'status':'ONE_CANDIDATE_FROZEN_NOT_SCORED','candidate_count':1,
                      'candidate_created':True,'scoring':'NOT-RUN','logical_sample_count':581,'face_constraint_count':1162,
                      **{key:self.freeze[key] for key in v.IDENTITY_KEYS},
                      'candidate_sha256':self.freeze['candidate_sha256'],
                      'baseline_geometry_sha256':self.freeze['baseline_geometry_sha256'],
                      'independent_audit_sha256':'c'*64,
                      'authoring_generator_sha256':c.digest((c.HERE/'feature_author.py').read_bytes()),
                      'attempt_directory':str(self.attempt),
                      'case_displacement_checks':[{'case':case,'max_rest_displacement_m':.001}
                                                  for case in c.CASES]}
        self.context=SimpleNamespace(freeze=self.freeze,policy={'position_source_ids':[0]},
                                     mapping=v.e.parse_mapping(self.original),
                                     loaded=[(case,{}) for case in c.CASES],
                                     baseline=[{'case':case,'status':'PASS'} for case in c.CASES])
        self.seal()

    def seal(self):
        self.manifest_path.write_text(json.dumps(self.manifest))
        self.freeze['asset_manifest_sha256']=c.digest(self.manifest_path.read_bytes())
        self.receipt['asset_manifest_sha256']=self.freeze['asset_manifest_sha256']
        self.receipt_path.write_text(json.dumps(self.receipt))
        self.freeze['authoring_receipt_sha256']=c.digest(self.receipt_path.read_bytes())

    def admit(self):
        # Small source-admission fixture has no geometric topology; full production
        # constraint validation is tested separately below on declared plane fixtures.
        with patch.object(v,'validate_receipt_constraints'):
            return v.authenticate_candidate(self.context,self.candidate,self.receipt_path,self.manifest_path)

    def test_real_constraint_admission_is_mandatory_after_source_validation(self):
        with patch.object(v,'validate_receipt_constraints',side_effect=ValueError('constraint witness rejected')) as check:
            with self.assertRaisesRegex(ValueError,'constraint witness rejected'):
                v.authenticate_candidate(self.context,self.candidate,self.receipt_path,self.manifest_path)
            check.assert_called_once()

    def test_manifest_counts_missing_each_or_both_are_refused(self):
        for keys in (('logical_sample_count',),('face_constraint_count',),
                     ('logical_sample_count','face_constraint_count')):
            saved=self.manifest.copy()
            for key in keys:self.manifest.pop(key)
            self.seal()
            with self.subTest(keys=keys):
                with self.assertRaisesRegex(ValueError,'manifest constraint count'):self.admit()
            self.manifest=saved

    def test_manifest_counts_empty_boolean_zero_or_mismatch_are_refused(self):
        for key in ('logical_sample_count','face_constraint_count'):
            for value in ('',None,True,0,580):
                before=self.manifest[key];self.manifest[key]=value;self.seal()
                with self.subTest(key=key,value=value):
                    with self.assertRaisesRegex(ValueError,'manifest constraint count'):self.admit()
                self.manifest[key]=before

    def test_saved_offset_bytes_pass_real_source_validator(self):
        mapping,changed=self.admit()
        self.assertEqual(changed,[0])
        self.assertNotEqual(mapping,self.context.mapping)

    def test_partial_or_failed_baseline_rejects_before_artifact_read(self):
        for baseline in (self.context.baseline[:-1],
                         [dict(row,status='REJECT' if row['case']==c.ANCHOR else 'PASS')
                          for row in self.context.baseline]):
            self.context.baseline=baseline
            with patch.object(v,'frozen_read') as read:
                with self.assertRaisesRegex(ValueError,'all19 fresh baseline'):self.admit()
                read.assert_not_called()

    def test_each_missing_or_changed_frozen_artifact_rejects(self):
        for path in (self.candidate,self.receipt_path,self.manifest_path):
            raw=path.read_bytes()
            with self.subTest(artifact=path.name,change='missing'):
                path.unlink()
                with self.assertRaises(OSError):self.admit()
                path.write_bytes(raw)
            with self.subTest(artifact=path.name,change='changed'):
                path.write_bytes(raw+b' ')
                with self.assertRaisesRegex(ValueError,'bytes differ'):self.admit()
                path.write_bytes(raw)

    def test_malformed_frozen_hashes_reject_before_artifact_admission(self):
        for key in ('candidate_sha256','authoring_receipt_sha256','asset_manifest_sha256'):
            old=self.freeze[key]
            with self.subTest(key=key):
                self.freeze[key]='not-a-hash'
                with self.assertRaises(ValueError):self.admit()
                self.freeze[key]=old

    def test_failed_or_scored_receipt_and_wrong_manifest_schema_reject(self):
        for key,value in (('status','REJECT_AUTHORING_SINGLE_ATTEMPT'),
                          ('candidate_created',False),('candidate_count',True),
                          ('scoring','PASS'),('kind','old-hybrid-receipt')):
            original=self.receipt[key]
            with self.subTest(key=key):
                self.receipt[key]=value;self.seal()
                with self.assertRaises(ValueError):self.admit()
                self.receipt[key]=original
        self.seal()
        self.manifest['schema_version']=True;self.seal()
        with self.assertRaisesRegex(ValueError,'receipt schema'):self.admit()

    def test_cohort_source_execution_and_baseline_crosslinks_reject(self):
        for document,keys in ((self.receipt,v.IDENTITY_KEYS+('baseline_geometry_sha256',
                                    'independent_audit_sha256','authoring_generator_sha256',
                                    'attempt_directory')),(self.manifest,v.IDENTITY_KEYS)):
            for key in keys:
                original=document[key]
                with self.subTest(document='receipt' if document is self.receipt else 'manifest',key=key):
                    document[key]='wrong';self.seal()
                    with self.assertRaises(ValueError):self.admit()
                    document[key]=original
        self.seal()

    def test_manifest_change_list_and_displacement_coverage_are_checked(self):
        self.manifest['changed_source_ids']=[1];self.seal()
        with self.assertRaisesRegex(ValueError,'changed offset IDs'):self.admit()
        self.manifest['changed_source_ids']=[0]
        self.receipt['case_displacement_checks'].pop();self.seal()
        with self.assertRaisesRegex(ValueError,'omit/reorder'):self.admit()

    def test_source_helper_weight_outside_support_and_topology_tamper_reject(self):
        baseline=self.candidate.read_bytes()
        for line,field,value in ((4,0,'1'),(4,3,'.9'),(5,8,'.001')):
            lines=baseline.decode().splitlines(keepends=True)
            tokens=lines[line].split();tokens[field]=value;lines[line]=' '.join(tokens)+'\n'
            raw=''.join(lines).encode();self.candidate.write_bytes(raw)
            sha=c.digest(raw)
            self.freeze['candidate_sha256']=sha
            self.receipt['candidate_sha256']=sha
            self.manifest.update(candidate_sha256=sha,mhclo_sha256=sha)
            self.seal()
            with self.subTest(line=line,field=field):
                with self.assertRaises(ValueError):self.admit()
        self.candidate.write_bytes(baseline)
        sha=c.digest(baseline);self.freeze['candidate_sha256']=sha
        self.receipt['candidate_sha256']=sha;self.manifest.update(candidate_sha256=sha,mhclo_sha256=sha)
        self.seal()
        (self.source/'garment/female_sportsuit01.obj').write_bytes(b'changed topology')
        with self.assertRaisesRegex(ValueError,'topology bytes'):self.admit()

    def test_wrong_attempt_path_and_symlink_reject(self):
        elsewhere=self.root/'female_sportsuit01.mhclo'
        elsewhere.write_bytes(self.candidate.read_bytes())
        with self.assertRaisesRegex(ValueError,'exact frozen attempt'):
            v.authenticate_candidate(self.context,elsewhere,self.receipt_path,self.manifest_path)
        self.candidate.unlink();self.candidate.symlink_to(elsewhere)
        with self.assertRaisesRegex(ValueError,'exact frozen attempt'):self.admit()


class ExecutionOrderControls(unittest.TestCase):
    def test_baseline_failure_prevents_candidate_and_control_read(self):
        args=argparse.Namespace(out=Path('/nonexistent-current19-control-output'),
                                freeze=Path('unused'),corpus=Path('unused'))
        with patch.object(v.x,'load_context',side_effect=ValueError('case19 reconstruction failed')), \
             patch.object(v,'authenticate_candidate') as candidate, \
             patch.object(v,'evaluate') as score:
            with self.assertRaisesRegex(ValueError,'case19 reconstruction failed'):v.run(args)
            candidate.assert_not_called();score.assert_not_called()

    def test_cli_missing_freeze_rejects_without_candidate_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            argv=[]
            for name in ('freeze','corpus','candidate','authoring-receipt','asset-manifest','fresh','retained','out'):
                argv+=['--'+name,str(root/name)]
            with patch.object(v,'authenticate_candidate') as candidate:
                self.assertEqual(v.main(argv),2)
                candidate.assert_not_called()

    def test_control_success_cannot_override_candidate_failure(self):
        context=SimpleNamespace(
            freeze={key:'a'*64 for key in v.IDENTITY_KEYS+('candidate_sha256',
                    'authoring_receipt_sha256','asset_manifest_sha256','baseline_geometry_sha256')},
            loaded=[(case,{}) for case in c.CASES],mapping={},policy={},
            baseline=[{'case':case,'status':'PASS'} for case in c.CASES])
        def score(name,*_):
            return {'case':name,'failures':['new_proper_crossing:body_pairs'] if name==c.CASES[0] else [],
                    'fixed_default_ROI':{'baseline':{'body_first':20},'candidate':{'body_first':20}}}
        with patch.object(v,'frozen_read'),patch.object(v.e,'camera_for',return_value=(None,None)), \
             patch.object(v,'old_rejection_control',return_value={'status':'PASS_RED_CAPABLE_OLD_REJECTION'}), \
             patch.object(v.e,'candidate_part',return_value=({},[],.001,[1,1,1])), \
             patch.object(v.e,'score_case',side_effect=score) as scorer:
            report=v.evaluate(context,{},[0],Path('synthetic-camera'),Path('synthetic-control'))
        self.assertEqual(scorer.call_count,19)
        self.assertEqual(report['status'],'REJECT')
        self.assertEqual(report['failures'][0]['failures'],['new_proper_crossing:body_pairs'])
        self.assertEqual(report['failures'][-1],{'case':c.ANCHOR,
                         'failures':['no_measurable_default_ROI_benefit']})
        self.assertFalse(report['quality_acceptance'])
        self.assertIn('NOT-RUN',report['normals_tangents_actual_upload_GPU_Web_CLI'])

    def test_incomplete_baseline_never_reaches_candidate_math(self):
        context=SimpleNamespace(loaded=[(case,{}) for case in c.CASES],baseline=[])
        with patch.object(v.e,'candidate_part') as candidate:
            with self.assertRaisesRegex(ValueError,'all19 fresh baseline'):
                v.evaluate(context,{},[],Path('unused'),Path('unused'))
            candidate.assert_not_called()

    def test_pinned_old_control_bytes_checked_before_shared_crossing_seam(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);fresh=root/'capture.json';fresh.write_bytes(b'synthetic anchor')
            target=root/'retained-shoulder-source80/one-target-v1/target.json'
            target.parent.mkdir(parents=True);target.write_bytes(b'synthetic target')
            witness=root/'retained-shoulder-source80/one-target-evaluation-v1/fresh-new-pair-witness.json'
            witness.parent.mkdir(parents=True);witness.write_bytes(b'synthetic witness')
            with patch.object(v,'FRESH_SHA',c.digest(fresh.read_bytes())), \
                 patch.object(v,'TARGET_SHA',c.digest(target.read_bytes())), \
                 patch.object(v,'WITNESS_SHA',c.digest(witness.read_bytes())), \
                 patch.object(v.e,'old_rejection_control',side_effect=ValueError('known rejected new pair escaped scoring crossing seam')) as shared:
                with self.assertRaisesRegex(ValueError,'known rejected new pair'):
                    v.old_rejection_control(fresh,root)
                shared.assert_called_once_with(fresh,root)
                witness.write_bytes(b'tampered')
                with self.assertRaisesRegex(ValueError,'pair witness bytes differ'):
                    v.old_rejection_control(fresh,root)
                self.assertEqual(shared.call_count,1)


class ConstraintAdmissionControls(unittest.TestCase):
    """581 metadata rows over three synthetic positions, never actual geometry."""
    def setUp(self):
        self.samples=[];self.planes=[]
        for ordinal in range(581):
            sample={'logical_sample0':ordinal,'triangle0':ordinal//7,'sample0':ordinal%7,
                'barycentric':list(v.original_author.SAMPLES[ordinal%7]),'sources':[0,1,2],
                'nearest_face_ids':[10,11]}
            self.samples.append(sample)
            for face,normal in ((10,[0.,0.,1.]),(11,[0.,1.,0.])):
                self.planes.append({**{key:sample[key] for key in v.feature.SAMPLE_KEYS},
                    'body_triangle0':face,'plane':{'body_triangle0':face,'point':[0.,0.,0.],
                        'normal':normal},'d_m':0.,'slope':1/math.sqrt(2),'realized_side_m':.001})
        direction=[0.,1/math.sqrt(2),1/math.sqrt(2)]
        source_planes={sid:{'normal':direction,'source_feature':[sid]} for sid in range(3)}
        directions={sid:direction for sid in range(3)}
        lower,upper=v.feature.amplitude_interval(self.samples,self.planes,directions)
        offsets=[v.e.f32(lower*component) for component in direction]
        self.realized=[offsets[:] for _ in range(3)]
        v.feature.validate_realized_constraints(self.samples,self.planes,self.realized)
        self.trace={'directions':directions,'source_planes':source_planes,'scales':[1.,1.,1.],
            'source_ids':[0,1,2],'original_mapping':{'rows':[{'offset':[0.,0.,0.]} for _ in range(3)]},
            'candidate_mapping':{'rows':[{'offset':offsets[:]} for _ in range(3)]}}
        self.receipt={'logical_samples':copy.deepcopy(self.samples),
            'planes':copy.deepcopy(self.planes),'logical_sample_count':581,
            'face_constraint_count':1162,'amplitude_m':lower,'lower_m':lower,'upper_m':upper,
            'source_planes':{str(sid):copy.deepcopy(plane) for sid,plane in source_planes.items()},
            'interval':{'lower_m':lower,'upper_m':upper,'logical_sample_count':581,
                'face_constraint_count':1162,'source_planes':3,'source_displacement_cap_m':.020}}

    def admit(self):
        v.validate_constraint_records(self.receipt,self.samples,self.planes,self.realized,self.trace)

    def test_all_face_saved_residuals_are_checked(self):self.admit()

    def test_omitted_face_even_with_self_consistent_claim_is_refused(self):
        self.receipt['logical_samples'][0]['nearest_face_ids']=[10]
        self.receipt['planes'].pop(1);self.receipt['face_constraint_count']-=1
        with self.assertRaisesRegex(ValueError,'independent nearest-face'):self.admit()

    def test_missing_plane_with_unchanged_claim_is_refused(self):
        self.receipt['planes'].pop(1);self.receipt['face_constraint_count']-=1
        with self.assertRaisesRegex(ValueError,'omitted nearest face'):self.admit()

    def test_logical_duplicates_preserved_as_separate_ids(self):
        self.receipt['logical_samples'][1]['logical_sample0']=0
        with self.assertRaises(ValueError):self.admit()

    def test_boolean_and_wrong_counts_are_refused(self):
        for key,value in (('logical_sample_count',True),('logical_sample_count',580),
                          ('face_constraint_count',True),('face_constraint_count',581)):
            before=self.receipt[key];self.receipt[key]=value
            with self.subTest(key=key,value=value):
                with self.assertRaisesRegex(ValueError,'count differs'):self.admit()
            self.receipt[key]=before

    def test_plane_geometry_source_and_distance_tamper_refused(self):
        for key,value in (('body_triangle0',12),('d_m',.1),('sources',[1,0,2]),
                          ('barycentric',[0.,1.,0.]),('plane',{'body_triangle0':10,
                              'point':[0.,0.,.0001],'normal':[0.,0.,1.]})):
            row=self.receipt['planes'][0];before=row[key];row[key]=value
            with self.subTest(key=key):
                with self.assertRaises(ValueError):self.admit()
            row[key]=before

    def test_ideal_pass_one_actual_face_below_saved_floor_rejects(self):
        self.assertTrue(all(row['d_m']+self.receipt['amplitude_m']*row['slope']>=.001 for row in self.planes))
        self.realized=[[0.,.0009998,.001] for _ in range(3)]
        for value in (.0009998,.001):
            for row in self.receipt['planes']:
                if row['body_triangle0']==11:row['realized_side_m']=value
            with self.assertRaisesRegex(ValueError,'saved-text actual face'):self.admit()

    def test_saved_record_cannot_lie_about_actual_residual(self):
        self.receipt['planes'][0]['realized_side_m']=.002
        with self.assertRaisesRegex(ValueError,'saved-text actual face'):self.admit()

    def test_forged_finite_slope_with_real_saved_positions_is_refused(self):
        self.receipt['planes'][0]['slope']=123456.
        with self.assertRaisesRegex(ValueError,'independent face constraint differs: slope'):self.admit()

    def test_jointly_forged_lower_amplitude_upper_and_interval_is_refused(self):
        original_positions=copy.deepcopy(self.realized)
        self.receipt.update(amplitude_m=.019,lower_m=.019,upper_m=1e6)
        self.receipt['interval'].update(lower_m=.019,upper_m=1e6)
        self.receipt['planes'][0]['slope']=123456.
        with self.assertRaisesRegex(ValueError,'independent complete interval'):self.admit()
        self.assertEqual(self.realized,original_positions)

    def test_self_consistent_nonminimal_original_lower_endpoint_is_refused(self):
        self.receipt.update(amplitude_m=.002,lower_m=.002)
        with self.assertRaisesRegex(ValueError,'lower-endpoint'):self.admit()

    def test_forged_source_direction_is_refused(self):
        self.receipt['source_planes']['0']['normal']=[0.,0.,1.]
        with self.assertRaisesRegex(ValueError,'source feature planes'):self.admit()

    def test_every_interval_metadata_field_is_independently_checked(self):
        for key,value in (('lower_m',.002),('upper_m',100.),('logical_sample_count',580),
                          ('face_constraint_count',1161),('source_planes',2),
                          ('source_displacement_cap_m',.021)):
            before=self.receipt['interval'][key];self.receipt['interval'][key]=value
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError,'complete interval'):self.admit()
            self.receipt['interval'][key]=before

    def test_saved_offset_must_be_original_lower_endpoint_f32_displacement(self):
        self.trace['candidate_mapping']['rows'][2]['offset'][2]=v.e.f32(.0011)
        with self.assertRaisesRegex(ValueError,'saved candidate offset differs'):self.admit()

    def test_amplitude_is_positive_original_lower_endpoint(self):
        for key,value in (('amplitude_m',0.),('lower_m',.0009),('upper_m',.0009),
                          ('amplitude_m',float('nan'))):
            old=self.receipt[key];self.receipt[key]=value
            with self.assertRaisesRegex(ValueError,'lower-endpoint'):self.admit()
            self.receipt[key]=old

    def test_reconstruction_derives_nearest_sets_from_original_geometry(self):
        body=[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]]
        part={'source_ids':[0,1,2],'indices':[0,1,2]}
        context=SimpleNamespace(mapping={},support={'incident_triangles0':[0],
            'position_graph_rings':[[0],[1],[2]],'position_source_ids':[0,1,2]},
            loaded=[('synthetic',{'parts':[dict(part,name='garment'),dict(part,name='body')]})])
        fitted=[[0.,0.,.001],[.1,0.,.001],[0.,.1,.001]]
        with patch.object(v.e,'raw_cage',return_value=body), \
             patch.object(v.e,'fit_rows',return_value=(fitted,None)), \
             patch.object(v.original_author,'positive_scales',return_value=[1.,1.,1.]), \
             patch.object(v,'validate_constraint_records') as validate:
            v.validate_receipt_constraints(context,{'logical_samples':[]},{})
        expected=validate.call_args.args[1];planes=validate.call_args.args[2]
        self.assertEqual(len(expected),7);self.assertEqual(len(planes),7)
        self.assertTrue(all(row['nearest_face_ids']==[0] for row in expected))
        self.assertTrue(all(row['plane']['body_source_ids']==[0,1,2] for row in planes))
        trace=validate.call_args.args[4]
        self.assertEqual([list(trace['directions'][sid]) for sid in range(3)],
                         [[0.,0.,1.],[0.,0.,.75],[0.,0.,.25]])
        self.assertEqual([row['slope'] for row in planes[:3]],[1.,.75,.25])


class SmallTraceIntegrationControls(unittest.TestCase):
    """Three synthetic rows and seven samples through the complete production seam."""
    def setUp(self):
        self.neutral={0:[0.,0.,0.],1:[1.,0.,0.],2:[0.,1.,0.],3:[0.,0.,1.]}
        raw=(b'x_scale 0 1 1\ny_scale 0 2 1\nz_scale 0 3 1\nverts 0\n'+
             b'0 1 2 1 0 0 .2 .2 -.001\n'*3+b'delete_verts\n')
        mapping=v.e.parse_mapping(raw);fitted,_=v.e.fit_rows(mapping,self.neutral)
        body=[[0,1,2]];smooth=v.feature.source_normals(self.neutral,body)
        source_planes={sid:v.feature.feature_direction(fitted[sid],self.neutral,body,smooth)
                       for sid in range(3)}
        directions={sid:v.original_author.scale(source_planes[sid]['normal'],weight)
                    for sid,weight in enumerate((1.,.75,.25))}
        samples=[];planes=[]
        for sample0,bary in enumerate(v.original_author.SAMPLES):
            point=v.original_author.interpolate(fitted,bary)
            direction=v.original_author.interpolate([directions[sid] for sid in range(3)],bary)
            v.feature.append_constraints(samples,planes,0,sample0,bary,[0,1,2],point,direction,
                                         self.neutral,body,smooth)
        lower,upper=v.feature.amplitude_interval(samples,planes,directions,expected_count=7)
        scales=v.original_author.positive_scales(mapping,self.neutral)
        lines=mapping['lines'][:]
        for sid in range(3):
            row=mapping['rows'][sid]
            values=[v.e.f32(old+lower*directions[sid][axis]/scales[axis])
                    for axis,old in enumerate(row['offset'])]
            tokens=lines[row['line0']].split();tokens[6:9]=[format(value,'.9g') for value in values]
            lines[row['line0']]=' '.join(tokens)+'\n'
        self.candidate=v.e.parse_mapping(''.join(lines).encode())
        realized,_=v.e.fit_rows(self.candidate,self.neutral)
        v.feature.validate_realized_constraints(samples,planes,realized,expected_count=7)
        self.receipt={'logical_samples':samples,'planes':planes,'logical_sample_count':7,
            'face_constraint_count':7,'amplitude_m':lower,'lower_m':lower,'upper_m':upper,
            'source_planes':{str(sid):plane for sid,plane in source_planes.items()},
            'interval':{'lower_m':lower,'upper_m':upper,'logical_sample_count':7,
                'face_constraint_count':7,'source_planes':3,'source_displacement_cap_m':.020}}
        part={'source_ids':[0,1,2],'indices':[0,1,2]}
        self.context=SimpleNamespace(mapping=mapping,support={'incident_triangles0':[0],
            'position_graph_rings':[[0],[1],[2]],'position_source_ids':[0,1,2]},
            loaded=[('synthetic',{'parts':[dict(part,name='body'),dict(part,name='garment')]})])
        # Only fixture cardinality changes. Every production mathematical validator runs.
        handles=[patch.object(v.e,'raw_cage',return_value=self.neutral),
                 patch.object(v.feature,'LOGICAL_SAMPLE_COUNT',7)]
        for name in ('validate_constraint_coverage','amplitude_interval','validate_realized_constraints'):
            original=getattr(v.feature,name)
            def seven(*args,_original=original,**kwargs):
                return _original(*args,**{**kwargs,'expected_count':7})
            handles.append(patch.object(v.feature,name,side_effect=seven))
        for handle in handles:handle.start();self.addCleanup(handle.stop)

    def admit(self):v.validate_receipt_constraints(self.context,self.receipt,self.candidate)

    def test_real_feature_ring_interval_and_saved_offsets_admit(self):self.admit()

    def test_forged_slope_and_interval_rejected_with_saved_mapping_unchanged(self):
        before=copy.deepcopy(self.candidate)
        self.receipt.update(amplitude_m=.019,lower_m=.019,upper_m=1e6)
        self.receipt['interval'].update(lower_m=.019,upper_m=1e6)
        self.receipt['planes'][0]['slope']=123456.
        with self.assertRaisesRegex(ValueError,'complete interval'):self.admit()
        self.assertEqual(self.candidate,before)

    def test_finite_slope_forgery_rejected_after_full_reconstruction(self):
        self.receipt['planes'][0]['slope']*=2
        with self.assertRaisesRegex(ValueError,'independent face constraint differs: slope'):self.admit()

    def test_nonminimal_consistent_amplitude_rejected_after_full_reconstruction(self):
        self.receipt['amplitude_m']=self.receipt['lower_m']=.019
        with self.assertRaisesRegex(ValueError,'lower-endpoint'):self.admit()

    def test_changed_saved_offset_still_clearing_planes_is_refused(self):
        self.candidate['rows'][0]['offset'][2]=v.e.f32(.01)
        realized,_=v.e.fit_rows(self.candidate,self.neutral)
        v.feature.validate_realized_constraints(self.receipt['logical_samples'],self.receipt['planes'],realized)
        with self.assertRaisesRegex(ValueError,'saved candidate offset differs'):self.admit()


if __name__=='__main__':unittest.main()
