"""Exclusive v4 attempt controls on a declared seven-sample synthetic fixture.

The fixture has three supported garment rows and one body/garment triangle.
No actual support traversal, actual candidate, or candidate quality score runs.
"""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import feature_author as a
import feature_policy as f


class ReservationControls(unittest.TestCase):
    def test_one_exclusive_attempt_and_exact_frozen_path(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory).resolve()/'attempt';freeze={'attempt_directory':str(out)}
            a.reserve_attempt(out,freeze)
            with self.assertRaises(ValueError):a.reserve_attempt(out,freeze)
            with self.assertRaises(ValueError):a.reserve_attempt(out.parent/'retry',freeze)
            self.assertFalse((out.parent/'retry').exists())

    def test_missing_freeze_rejects_before_geometry_and_attempt_consumption(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(f,'source_normals') as normals:
            root=Path(directory).resolve()
            with self.assertRaises(ValueError):a.attempt(root/'missing',root,root/'attempt')
            normals.assert_not_called();self.assertFalse((root/'attempt').exists())

    def test_fresh_baseline_failure_rejects_before_reservation(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(a.x,'load_context',side_effect=ValueError('all19 baseline failed')), \
             patch.object(a,'reserve_attempt') as reserve:
            with self.assertRaisesRegex(ValueError,'baseline failed'):
                a.attempt(Path('unused'),Path(directory),Path(directory)/'attempt')
            reserve.assert_not_called()

    def test_unchanged_source_helpers_and_thresholds(self):
        for name in ('positive_scales','triangle_sources','interpolate'):
            self.assertIs(getattr(a,name),getattr(a.reference,name))
        self.assertEqual((a.MARGIN,a.RESIDUAL_FLOOR,a.MAX_DELTA),(.001,.0009999,.02))
        self.assertEqual(a.SAMPLES,a.reference.SAMPLES)


class SyntheticAttemptControls(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name).resolve();self.out=self.root/'attempt'
        source=self.root/'source';(source/'garment').mkdir(parents=True)
        self.original=(b'x_scale 0 1 1\ny_scale 0 2 1\nz_scale 0 3 1\nverts 0\n'+
                       b'0 1 2 1 0 0 .2 .2 -.001\n'*848+b'delete_verts\n')
        (source/'base.obj').write_bytes(b'synthetic base source\n')
        (source/'garment/female_sportsuit01.obj').write_bytes(b'synthetic garment source\n')
        (source/'garment/female_sportsuit01.mhclo').write_bytes(self.original)
        self.neutral={0:[0.,0.,0.],1:[1.,0.,0.],2:[0.,1.,0.],3:[0.,0.,1.]}
        self.mapping=a.engine.parse_mapping(self.original)
        self.freeze={'candidate_id':f.CANDIDATE_ID,'candidate_count':1,'cohort_kind':a.x.c.KIND,
                     'attempt_directory':str(self.out),'authoring_policy_version':4,
                     **{key:'a'*64 for key in ('cohort_manifest_sha256','source_inventory_sha256',
                        'execution_files_sha256','reference_policy_sha256','support_sha256',
                        'baseline_geometry_sha256','feature_policy_sha256')},
                     'previous_rejection':{'path':'/synthetic/prior-rejection','bytes':3,'sha256':'b'*64},
                     'independent_audit':{'sha256':'c'*64}}
        parts=[{'name':name,'source_ids':[0,1,2],'indices':[0,1,2]} for name in ('body','garment')]
        self.context=SimpleNamespace(freeze=self.freeze,policy={},support={
            'position_source_ids':[0,1,2],'position_graph_rings':[[0],[1],[2]],'incident_triangles0':[0]},
            loaded=[(case,{'parts':parts}) for case in a.x.c.CASES],mapping=self.mapping,
            baseline=[{'case':case,'status':'PASS'} for case in a.x.c.CASES],feature_policy=copy.deepcopy(f.POLICY))
        self.patches=[]
        def patcher(target,name,**kw):
            handle=patch.object(target,name,**kw);self.patches.append(handle);self.addCleanup(handle.stop)
            return handle.start()
        patcher(a.x,'load_context',return_value=self.context)
        patcher(a.engine,'SOURCE',new=source)
        patcher(a.engine,'SOURCE_MHCLO_SHA',new=a.digest(source/'garment/female_sportsuit01.mhclo'))
        patcher(a.engine,'raw_cage',return_value=self.neutral)
        patcher(a.engine,'support_closure',return_value=None)
        self.case_check=patcher(a.engine,'candidate_part',return_value=({},[],.002,[1.,1.,1.]))
        # Count override is restricted to this seven-sample synthetic fixture.
        # The real arithmetic/coverage/realized functions still run, including all faces.
        for name in ('validate_constraint_coverage','amplitude_interval','validate_realized_constraints'):
            original=getattr(f,name)
            def seven(*args,_original=original,**kwargs):
                return _original(*args,**{**kwargs,'expected_count':7})
            patcher(f,name,side_effect=seven)

    def run_attempt(self):return a.attempt(self.root/'synthetic-freeze',self.root,self.out)

    def read_receipt(self):return json.loads((self.out/'authoring-receipt.json').read_text())

    def test_small_synthetic_success_keeps_identity_all_faces_and_unscored_state(self):
        receipt=self.run_attempt();manifest=json.loads((self.out/'asset-manifest.json').read_text())
        self.assertEqual(receipt['status'],'ONE_CANDIDATE_FROZEN_NOT_SCORED')
        self.assertTrue(receipt['candidate_created']);self.assertEqual(receipt['scoring'],'NOT-RUN')
        self.assertEqual(receipt['kind'],'nvwa85-current19-feature-authoring-receipt-v4')
        self.assertEqual(manifest['kind'],'nvwa85-current19-feature-offset-asset-manifest-v4')
        self.assertEqual((receipt['logical_sample_count'],receipt['face_constraint_count']),(7,7))
        self.assertEqual(self.case_check.call_count,19)
        self.assertEqual([row['case'] for row in receipt['case_displacement_checks']],list(a.x.c.CASES))
        for key in ('authoring_policy_version','feature_policy_sha256','previous_rejection'):
            self.assertEqual(receipt[key],self.freeze[key]);self.assertEqual(manifest[key],self.freeze[key])
        self.assertEqual(a.digest(self.out/'asset-manifest.json'),receipt['asset_manifest_sha256'])
        self.assertEqual(a.digest(self.out/'female_sportsuit01.mhclo'),receipt['candidate_sha256'])
        self.assertTrue(all(row['realized_side_m']>=f.RESIDUAL_FLOOR for row in receipt['planes']))
        with self.assertRaisesRegex(ValueError,'no second candidate'):self.run_attempt()

    def test_bad_policy_refuses_before_consumption(self):
        self.context.feature_policy['authoring_policy_version']=3
        with self.assertRaisesRegex(ValueError,'policy v4 semantics'):self.run_attempt()
        self.assertFalse(self.out.exists())

    def test_post_reservation_geometry_failure_is_retained_and_consumed(self):
        with patch.object(f,'feature_direction',side_effect=ValueError('synthetic feature refusal')):
            with self.assertRaisesRegex(ValueError,'feature refusal'):self.run_attempt()
        receipt=self.read_receipt()
        self.assertEqual(receipt['status'],'REJECT_AUTHORING_SINGLE_ATTEMPT')
        self.assertFalse(receipt['candidate_created']);self.assertEqual(receipt['scoring'],'NOT-RUN')
        self.assertEqual(receipt['diagnostic']['phase'],'source_feature_direction')
        self.assertEqual(receipt['previous_rejection'],self.freeze['previous_rejection'])
        self.assertFalse((self.out/'female_sportsuit01.mhclo').exists());self.case_check.assert_not_called()
        with self.assertRaisesRegex(ValueError,'no second candidate'):self.run_attempt()

    def test_publication_failure_truthfully_retains_created_candidate(self):
        original_write=Path.write_text
        def failed_manifest(path,*args,**kwargs):
            if path.name=='asset-manifest.json':raise OSError('synthetic manifest write failed')
            return original_write(path,*args,**kwargs)
        with patch.object(Path,'write_text',new=failed_manifest):
            with self.assertRaisesRegex(OSError,'manifest write failed'):self.run_attempt()
        receipt=self.read_receipt()
        self.assertEqual(receipt['status'],'REJECT_AUTHORING_SINGLE_ATTEMPT')
        self.assertTrue(receipt['candidate_created'])
        self.assertEqual(receipt['candidate_sha256'],a.digest(self.out/'female_sportsuit01.mhclo'))
        self.assertEqual(receipt['scoring'],'NOT-RUN')
        with self.assertRaisesRegex(ValueError,'no second candidate'):self.run_attempt()

    def test_second_receipt_write_failure_records_rejection_and_retains_both_artifacts(self):
        original_write=Path.write_text;receipt_writes=0;published={}
        failure=OSError('synthetic one-time final receipt failure')
        def fail_second_receipt(path,*args,**kwargs):
            nonlocal receipt_writes
            if path.name.startswith('.authoring-receipt.') and path.name.endswith('.pending'):
                receipt_writes+=1
                if receipt_writes==2:
                    for name in ('female_sportsuit01.mhclo','asset-manifest.json'):
                        published[name]=(self.out/name).read_bytes()
                    # Simulate a truncated pending write, after both artifacts exist.
                    original_write(path,'{\"partial\":')
                    raise failure
            return original_write(path,*args,**kwargs)
        with patch.object(Path,'write_text',new=fail_second_receipt):
            with self.assertRaises(OSError) as caught:self.run_attempt()
        self.assertIs(caught.exception,failure)
        self.assertEqual(receipt_writes,3) # Initial, failed final success, rejection.
        receipt=self.read_receipt()
        self.assertEqual(receipt['status'],'REJECT_AUTHORING_SINGLE_ATTEMPT')
        self.assertTrue(receipt['candidate_created'])
        self.assertEqual(receipt['error'],str(failure))
        self.assertEqual(receipt['candidate_sha256'],a.digest(self.out/'female_sportsuit01.mhclo'))
        self.assertEqual(receipt['asset_manifest_sha256'],a.digest(self.out/'asset-manifest.json'))
        self.assertEqual(receipt['scoring'],'NOT-RUN')
        self.assertEqual(receipt['previous_rejection'],self.freeze['previous_rejection'])
        for name,raw in published.items():self.assertEqual((self.out/name).read_bytes(),raw)
        self.assertEqual((self.out/'.authoring-receipt.2.pending').read_text(),'{\"partial\":')
        self.assertEqual([path.name for path in self.out.glob('*.pending')],['.authoring-receipt.2.pending'])
        with self.assertRaisesRegex(ValueError,'no second candidate'):self.run_attempt()

    def test_persistent_receipt_failure_preserves_last_complete_receipt_and_error_chain(self):
        original_write=Path.write_text;receipt_writes=0;initial=[]
        publication_failure=OSError('synthetic final receipt storage failure')
        recovery_failure=OSError('synthetic rejection receipt storage failure')
        def fail_later_receipts(path,*args,**kwargs):
            nonlocal receipt_writes
            if path.name.startswith('.authoring-receipt.') and path.name.endswith('.pending'):
                receipt_writes+=1
                if receipt_writes==2:
                    initial.append((self.out/'authoring-receipt.json').read_bytes())
                    original_write(path,'partial final receipt')
                    raise publication_failure
                if receipt_writes==3:
                    original_write(path,'partial rejection receipt')
                    raise recovery_failure
            return original_write(path,*args,**kwargs)
        with patch.object(Path,'write_text',new=fail_later_receipts):
            with self.assertRaises(OSError) as caught:self.run_attempt()
        self.assertIs(caught.exception,publication_failure)
        self.assertIs(caught.exception.__cause__,recovery_failure)
        self.assertEqual((self.out/'authoring-receipt.json').read_bytes(),initial[0])
        self.assertEqual(self.read_receipt()['status'],'AUTHORING_STARTED_ONE_ATTEMPT')
        self.assertTrue((self.out/'female_sportsuit01.mhclo').is_file())
        self.assertTrue((self.out/'asset-manifest.json').is_file())
        self.assertEqual((self.out/'.authoring-receipt.2.pending').read_text(),'partial final receipt')
        self.assertEqual((self.out/'.authoring-receipt.3.pending').read_text(),'partial rejection receipt')
        with self.assertRaisesRegex(ValueError,'no second candidate'):self.run_attempt()

    def test_realized_failure_retains_all_logical_and_face_rows_without_candidate(self):
        original_fit=a.engine.fit_rows
        def changed_fit(mapping,cage):
            fitted,scales=original_fit(mapping,cage)
            if mapping['rows'][0]['offset'][2]>0:
                fitted[0][2]=0. # Saved candidate point now fails its retained face.
            return fitted,scales
        with patch.object(a.engine,'fit_rows',side_effect=changed_fit):
            with self.assertRaisesRegex(ValueError,'realized face'):self.run_attempt()
        receipt=self.read_receipt()
        self.assertEqual(receipt['status'],'REJECT_AUTHORING_SINGLE_ATTEMPT')
        self.assertEqual((receipt['logical_sample_count'],receipt['face_constraint_count']),(7,7))
        self.assertEqual(len(receipt['planes']),7);self.assertEqual(len(receipt['logical_samples']),7)
        self.assertLess(receipt['planes'][0]['realized_side_m'],f.RESIDUAL_FLOOR)
        self.assertFalse(receipt['candidate_created']);self.case_check.assert_not_called()
        self.assertFalse((self.out/'female_sportsuit01.mhclo').exists())


if __name__=='__main__':unittest.main()
