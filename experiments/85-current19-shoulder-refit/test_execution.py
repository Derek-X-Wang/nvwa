"""Prospective stage freeze controls; no planes, amplitude or candidate compute."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import execution as x


def freeze_fixture(attempt):
    rows=x.execution_files()
    return {'schema_version':1,'kind':x.KIND,'status':x.AUTHORING,'cohort_kind':x.c.KIND,
            'candidate_id':x.CANDIDATE_ID,'candidate_count':1,'attempt_directory':str(attempt),
            'cohort_manifest_sha256':'1'*64,'source_inventory_sha256':'2'*64,
            'baseline_geometry_sha256':'3'*64,'reference_policy_sha256':x.REFERENCE_POLICY_SHA,
            'support_sha256':x.SUPPORT_SHA,'execution_files':rows,
            'execution_files_sha256':x.p.inventory_digest(rows)}


class StageFreezeControls(unittest.TestCase):
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
    def test_wrong_reference_policy(self):self.reject(lambda f:f.update(reference_policy_sha256='0'*64))
    def test_wrong_reference_support(self):self.reject(lambda f:f.update(support_sha256='0'*64))
    def test_relative_attempt(self):self.reject(lambda f:f.update(attempt_directory='relative'))
    def test_full_closure_includes_new_code_and_imported_math(self):
        paths=set(x.required_execution_paths())
        for name in ('execution.py','author.py','scoring.py','test_execution.py','test_author.py'):
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
                  patch.object(x.c,'audit_geometry',return_value={'status':'PASS_CURRENT19_GEOMETRY','failures':[],'results':[]})):
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


if __name__=='__main__':unittest.main()
