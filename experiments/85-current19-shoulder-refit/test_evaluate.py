"""Synthetic admission/report controls. No actual candidate or corpus is scored."""
import argparse
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import current19 as c
import evaluate as v


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
                     'candidate_sha256':c.digest(self.candidate.read_bytes()),
                     'baseline_geometry_sha256':'b'*64,'independent_audit':{'sha256':'c'*64}}
        self.manifest={'schema_version':1,'kind':'nvwa85-current19-offset-asset-manifest-v1',
                       'status':'ONE_CANDIDATE_FROZEN_NOT_SCORED','candidate_count':1,
                       **{key:self.freeze[key] for key in v.IDENTITY_KEYS},
                       'candidate_sha256':self.freeze['candidate_sha256'],
                       'mhclo_sha256':self.freeze['candidate_sha256'],
                       'original_mhclo_sha256':self.original_sha,'original_obj_sha256':self.obj_sha,
                       'representation':'MHCLO offsets only; original OBJ bytes unchanged',
                       'changed_source_ids':[0]}
        self.receipt={'schema_version':1,'kind':'nvwa85-current19-authoring-receipt-v1',
                      'status':'ONE_CANDIDATE_FROZEN_NOT_SCORED','candidate_count':1,
                      'candidate_created':True,'scoring':'NOT-RUN',
                      **{key:self.freeze[key] for key in v.IDENTITY_KEYS},
                      'candidate_sha256':self.freeze['candidate_sha256'],
                      'baseline_geometry_sha256':self.freeze['baseline_geometry_sha256'],
                      'independent_audit_sha256':'c'*64,
                      'authoring_generator_sha256':c.digest((c.HERE/'author.py').read_bytes()),
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
        return v.authenticate_candidate(self.context,self.candidate,self.receipt_path,self.manifest_path)

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


if __name__=='__main__':unittest.main()
