"""Prospective stage freeze controls; no planes, amplitude or candidate compute."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import feature_execution as x

REJECTION_PATH=None


def freeze_fixture(attempt):
    rows=x.execution_files()
    return {'schema_version':1,'kind':x.KIND,'status':x.AUTHORING,'cohort_kind':x.c.KIND,
            'candidate_id':x.CANDIDATE_ID,'candidate_count':1,'attempt_directory':str(attempt),
            'cohort_manifest_sha256':'1'*64,'source_inventory_sha256':'2'*64,
            'baseline_geometry_sha256':'3'*64,'reference_policy_sha256':x.REFERENCE_POLICY_SHA,
            'support_sha256':x.SUPPORT_SHA,'execution_files':rows,
            'authoring_policy_version':4,'feature_policy_sha256':x.c.digest(x.FEATURE_POLICY_PATH.read_bytes()),
            'previous_rejection':{'path':str(REJECTION_PATH),
                'bytes':x.PREVIOUS_REJECTION_BYTES,'sha256':x.PREVIOUS_REJECTION_SHA},
            'execution_files_sha256':x.p.inventory_digest(rows)}


def synthetic_previous_rejection(test,root):
    """Small declared control; production path/hash pins are tested separately."""
    receipt={'schema_version':1,'kind':'nvwa85-current19-authoring-receipt-v1',
        'status':'REJECT_AUTHORING_SINGLE_ATTEMPT',
        'candidate_id':'nvwa-current19-shoulder-rest-refit-v1','cohort_kind':x.c.KIND,
        'candidate_created':False,'candidate_count':1,'scoring':'NOT-RUN',
        'cohort_manifest_sha256':'1'*64,'source_inventory_sha256':'2'*64,
        'execution_files_sha256':'3'*64}
    raw=json.dumps(receipt).encode();path=root/'v3-rejected-receipt.json';path.write_bytes(raw)
    summary={key:receipt[key] for key in
        ('cohort_manifest_sha256','source_inventory_sha256','execution_files_sha256')}
    summary['authoring_receipt_sha256']=x.c.digest(raw)
    summary_raw=json.dumps(summary).encode();summary_path=root/'summary.json';summary_path.write_bytes(summary_raw)
    handle=patch(__name__+'.REJECTION_PATH',path);handle.start();test.addCleanup(handle.stop)
    for name,value in (('PREVIOUS_REJECTION_BYTES',len(raw)),
                       ('PREVIOUS_REJECTION_SHA',x.c.digest(raw)),
                       ('PREVIOUS_SUMMARY_PATH',summary_path),('PREVIOUS_SUMMARY_SHA',x.c.digest(summary_raw))):
        handle=patch.object(x,name,value);handle.start();test.addCleanup(handle.stop)


class StageFreezeControls(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        synthetic_previous_rejection(self,Path(temp.name).resolve())
    def reject(self,change):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();freeze=freeze_fixture(root/'one-attempt');change(freeze)
            path=root/'freeze.json';path.write_text(json.dumps(freeze))
            with self.assertRaises((ValueError,KeyError,TypeError)):
                x.verify_freeze(path,(x.AUTHORING,))

    def test_exact_prospective_source_freeze(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();freeze=freeze_fixture(root/'one-attempt')
            path=root/'freeze.json';path.write_text(json.dumps(freeze))
            self.assertEqual(x.verify_freeze(path,(x.AUTHORING,)),freeze)
    def test_missing_freeze(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):x.verify_freeze(Path(d).resolve()/'absent',(x.AUTHORING,))
    def test_wrong_stage(self):self.reject(lambda f:f.update(status=x.SCORING))
    def test_wrong_cohort(self):self.reject(lambda f:f.update(cohort_kind='current18-plus-original-anchor-v1'))
    def test_wrong_candidate(self):self.reject(lambda f:f.update(candidate_id='nvwa-shoulder-rest-refit-v1'))
    def test_second_candidate(self):self.reject(lambda f:f.update(candidate_count=2))
    def test_bool_count(self):self.reject(lambda f:f.update(candidate_count=True))
    def test_missing_execution_file(self):self.reject(lambda f:f['execution_files'].pop())
    def test_rehashed_missing_file(self):
        def change(f):f['execution_files'].pop();f['execution_files_sha256']=x.p.inventory_digest(f['execution_files'])
        self.reject(change)
    def test_modified_imported_source_hash(self):self.reject(lambda f:f['execution_files'][0].update(sha256='0'*64))
    def test_rehashed_new_source_or_contract_hash_changes_reject(self):
        for name in x.NEW_FILES:
            def change(f):
                row=next(row for row in f['execution_files'] if row['path'].endswith('/'+name))
                row['sha256']='0'*64
                f['execution_files_sha256']=x.p.inventory_digest(f['execution_files'])
            with self.subTest(file=name):self.reject(change)

    def test_policy_semantics_cannot_be_reauthorized_by_new_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();freeze=freeze_fixture(root/'attempt')
            policy=x.c.strict_load(x.FEATURE_POLICY_PATH.read_bytes())
            policy['constraints']['margin_m']=.0005
            path=root/'policy.json';path.write_text(json.dumps(policy))
            freeze['feature_policy_sha256']=x.c.digest(path.read_bytes())
            freeze_path=root/'freeze.json';freeze_path.write_text(json.dumps(freeze))
            with patch.object(x,'FEATURE_POLICY_PATH',path):
                with self.assertRaisesRegex(ValueError,'semantics differ'):
                    x.verify_freeze(freeze_path,(x.AUTHORING,))

    def test_wrong_reference_policy(self):self.reject(lambda f:f.update(reference_policy_sha256='0'*64))
    def test_wrong_reference_support(self):self.reject(lambda f:f.update(support_sha256='0'*64))
    def test_wrong_feature_policy(self):self.reject(lambda f:f.update(feature_policy_sha256='0'*64))
    def test_wrong_feature_version(self):self.reject(lambda f:f.update(authoring_policy_version=3))
    def test_bool_feature_version(self):self.reject(lambda f:f.update(authoring_policy_version=True))
    def test_swapped_rejection(self):self.reject(lambda f:f['previous_rejection'].update(sha256='0'*64))
    def test_wrong_rejection_path(self):self.reject(lambda f:f['previous_rejection'].update(path='/tmp/receipt.json'))
    def test_wrong_rejection_size(self):self.reject(lambda f:f['previous_rejection'].update(bytes=1))
    def test_relative_attempt(self):self.reject(lambda f:f.update(attempt_directory='relative'))
    def test_full_closure_includes_new_code_and_imported_math(self):
        paths=set(x.required_execution_paths())
        for name in ('execution.py','author.py','scoring.py',*x.NEW_FILES):
            self.assertIn('experiments/85-current19-shoulder-refit/'+name,paths)
        for path in (x.REFERENCE_POLICY_PATH,x.SUPPORT_PATH):
            self.assertIn(path.relative_to(x.c.ROOT).as_posix(),paths)
        self.assertTrue(set(x.p.capture_paths())<=paths)


class IndependentAuditControls(unittest.TestCase):
    def fixture(self,root):
        cases=[{'case':case,'status':'PASS'} for case in x.c.CASES]
        report={'status':'PASS_INDEPENDENT_CURRENT19_DATA_AUDIT','all19_complete':True,
                'candidate_read':False,'quality_acceptance':False,'results':cases,
                'manifest_sha256':'1'*64,'run_id':'synthetic-stage-control',
                'production_raw_provenance_admission_rerun':{'status':'PASS','records':19,
                    'manifest_sha256':'1'*64,'source_inventory_sha256':'2'*64}}
        raw=json.dumps(report).encode();audit=root/'independent.json';audit.write_bytes(raw)
        geometry=root/'geometry-audit.json';geometry.write_bytes(b'synthetic geometry receipt only')
        freeze={'cohort_manifest_sha256':'1'*64,'source_inventory_sha256':'2'*64,
                'baseline_geometry_sha256':x.c.digest(geometry.read_bytes()),
                'independent_audit':{'path':str(audit),'bytes':len(raw),'sha256':x.c.digest(raw)}}
        return freeze,report,audit

    def check(self,change,expect_failure=True):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();freeze,report,audit=self.fixture(root)
            change(freeze,report)
            raw=json.dumps(report).encode();audit.write_bytes(raw)
            freeze['independent_audit'].update(bytes=len(raw),sha256=x.c.digest(raw))
            records=[{'case':case,'run_id':'synthetic-stage-control','snapshot':{}} for case in x.c.CASES]
            with (patch.object(x.p,'authenticate',return_value=records),
                  patch.object(x,'Baseline') as constructor,
                  patch.object(x.c,'audit_geometry',return_value={'status':'PASS_CURRENT19_GEOMETRY','failures':[],'results':[{'case':case,'status':'PASS'} for case in x.c.CASES]})):
                constructor.return_value.mapping={}
                if expect_failure:
                    with self.assertRaises((ValueError,KeyError,TypeError)):
                        x.authenticate_current(root,freeze)
                else:self.assertEqual(len(x.authenticate_current(root,freeze)[0]),19)
    def test_exact_audit_crosslinks_control_only(self):self.check(lambda f,r:None,False)
    def test_wrong_independent_manifest(self):self.check(lambda f,r:r.update(manifest_sha256='0'*64))
    def test_wrong_independent_source(self):self.check(lambda f,r:r['production_raw_provenance_admission_rerun'].update(source_inventory_sha256='0'*64))
    def test_incomplete_independent_cases(self):self.check(lambda f,r:r['results'].pop())
    def test_one_failed_independent_case(self):self.check(lambda f,r:r['results'][0].update(status='REJECT'))
    def test_independent_candidate_already_read(self):self.check(lambda f,r:r.update(candidate_read=True))


class PreviousRejectionControls(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        synthetic_previous_rejection(self,Path(temp.name).resolve())

    def test_consumed_actual_v3_receipt_is_bound(self):
        row={'path':str(REJECTION_PATH),'bytes':x.PREVIOUS_REJECTION_BYTES,
             'sha256':x.PREVIOUS_REJECTION_SHA}
        self.assertFalse(x.verify_previous_rejection(row)['candidate_created'])

    def test_parent_bound_canonical_copy_of_exact_receipt_is_admitted(self):
        copy_path=REJECTION_PATH.parent/'copied-v3-receipt.json'
        copy_path.write_bytes(REJECTION_PATH.read_bytes())
        row={'path':str(copy_path),'bytes':x.PREVIOUS_REJECTION_BYTES,
             'sha256':x.PREVIOUS_REJECTION_SHA}
        self.assertFalse(x.verify_previous_rejection(row)['candidate_created'])

    def test_summary_cannot_replace_actual_receipt(self):
        raw=x.PREVIOUS_SUMMARY_PATH.read_bytes()
        with self.assertRaisesRegex(ValueError,'binding differs'):
            x.verify_previous_rejection({'path':str(x.PREVIOUS_SUMMARY_PATH),
                'bytes':len(raw),'sha256':x.c.digest(raw)})

    def test_rehashed_wrong_v3_receipt_identity_is_refused(self):
        original=x.c.strict_load(REJECTION_PATH.read_bytes())
        summary_original=x.c.strict_load(x.PREVIOUS_SUMMARY_PATH.read_bytes())
        for key,value in (('kind','nvwa85-current19-feature-authoring-receipt-v4'),
                          ('status','ONE_CANDIDATE_FROZEN_NOT_SCORED'),
                          ('candidate_created',True),('candidate_count',True),
                          ('cohort_kind','old-hybrid'),('scoring','PASS')):
            receipt=dict(original);receipt[key]=value;raw=json.dumps(receipt).encode()
            REJECTION_PATH.write_bytes(raw)
            summary=dict(summary_original);summary['authoring_receipt_sha256']=x.c.digest(raw)
            summary_raw=json.dumps(summary).encode();x.PREVIOUS_SUMMARY_PATH.write_bytes(summary_raw)
            with patch.object(x,'PREVIOUS_REJECTION_BYTES',len(raw)), \
                 patch.object(x,'PREVIOUS_REJECTION_SHA',x.c.digest(raw)), \
                 patch.object(x,'PREVIOUS_SUMMARY_SHA',x.c.digest(summary_raw)):
                row={'path':str(REJECTION_PATH),'bytes':len(raw),'sha256':x.c.digest(raw)}
                with self.subTest(key=key):
                    with self.assertRaisesRegex(ValueError,'identity differs'):x.verify_previous_rejection(row)

    def test_changed_actual_rejection_is_refused(self):
        row={'path':str(REJECTION_PATH),'bytes':x.PREVIOUS_REJECTION_BYTES,
             'sha256':x.PREVIOUS_REJECTION_SHA}
        original=Path.read_bytes
        def read(path):
            return b'changed' if path==REJECTION_PATH else original(path)
        with patch.object(Path,'read_bytes',read):
            with self.assertRaisesRegex(ValueError,'bytes differ'):x.verify_previous_rejection(row)


class ProductionBindingControl(unittest.TestCase):
    def test_actual_consumed_v3_identity_stays_exact(self):
        self.assertEqual(x.PREVIOUS_REJECTION_BYTES,2146411)
        self.assertEqual(x.PREVIOUS_REJECTION_SHA,
            '10c8394cdb980d347a3c8bfbf0c034b858efdbf6bd13ba7750b804192759fd99')
        summary=x.c.strict_load(x.PREVIOUS_SUMMARY_PATH.read_bytes())
        self.assertEqual(summary['authoring_receipt_sha256'],x.PREVIOUS_REJECTION_SHA)
        self.assertEqual(summary['candidate_id'],'nvwa-current19-shoulder-rest-refit-v1')
        self.assertEqual(summary['status'],'REJECT_AUTHORING_SINGLE_ATTEMPT')
        self.assertFalse(summary['candidate_created'])


if __name__=='__main__':unittest.main()
