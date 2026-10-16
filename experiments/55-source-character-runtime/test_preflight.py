"""LOCAL CONTROLS only. Tiny files below are neither MakeHuman nor candidate execution."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import run

class PreflightControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.sample_path = self.root / 'sample.json'
        self.approval_path = self.root / 'approval.json'
        self.candidate = self.root / 'absent-candidate'
        self.receipt = self.root / 'receipt.json'
        roles = ['basemesh', 'vertex_groups', 'target_manifest', 'macro_manifest',
                 'target', 'rig', 'weights', 'body_proxy', 'garment', 'reference']
        files = []
        for role in roles:
            p = self.root / (role + '.control')
            p.write_text('HANDWRITTEN LOCAL CONTROL ' + role)
            files.append(dict(role=role, path=p.name, sha256=run.digest(p),
                              license='LOCAL-CONTROL', source_url='control:handwritten'))
        self.sample = dict(schema_version=1, sample_class='makehuman-approved-sample',
                           approved=True, parameter_schema='paired-local-targets-v1', reference_manifest_sha256='a' * 64,
                           basis='control-only', units='control-only', transforms={'control': True},
                           files=files, cases=[dict(case_id=k, kind=k, recipe={})
                           for k in ['neutral', 'body', 'face', 'combined']])
        self.approval = dict(schema_version=1, route_id='source-runtime',
                             local_source_read_approved=True, candidate_commit=run.PIN,
                             candidate_path=str(self.candidate.resolve()), offline_build_approved=True,
                             candidate_tree_sha256='b' * 64)

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, mutate_sample=None, mutate_approval=None, **overrides):
        if mutate_sample:
            mutate_sample(self.sample)
        self.sample_path.write_text(json.dumps(self.sample))
        self.approval['sample_manifest_sha256'] = run.digest(self.sample_path)
        if mutate_approval:
            mutate_approval(self.approval)
        self.approval_path.write_text(json.dumps(self.approval))
        values = dict(approval=str(self.approval_path), approval_sha256=run.digest(self.approval_path),
                      sample=str(self.sample_path), sample_sha256=run.digest(self.sample_path),
                      candidate=str(self.candidate), receipt=str(self.receipt))
        values.update(overrides)
        argv = [word for key, value in values.items() for word in ['--' + key.replace('_', '-'), value]]
        with contextlib.redirect_stdout(io.StringIO()):
            code = run.main(argv)
        result = json.loads(self.receipt.read_text())
        self.assertEqual(code, 2)
        self.assertEqual(result['status'], 'not_run')
        self.assertFalse(result['actual_candidate_code_executed'])
        self.assertFalse(result['native_graphical_executed'])
        self.assertFalse(result['web_graphical_executed'])
        self.assertFalse(result['reference_pipeline_executed'])
        return result['reason']

    def test_absent_approval(self):
        self.assertIn('unavailable', self.invoke(approval=str(self.root / 'absent.json')))
    def test_wrong_approval_digest(self):
        self.assertIn('SHA-256 mismatch', self.invoke(approval_sha256='0' * 64))
    def test_missing_approval_digest(self):
        self.assertIn('required', self.invoke(approval_sha256=''))
    def test_wrong_commit_approval(self):
        self.assertIn('commit mismatch', self.invoke(mutate_approval=lambda a: a.update(candidate_commit='0' * 40)))
    def test_wrong_candidate_path(self):
        self.assertIn('path mismatch', self.invoke(mutate_approval=lambda a: a.update(candidate_path='/other')))
    def test_source_not_approved(self):
        self.assertIn('not approved', self.invoke(mutate_approval=lambda a: a.update(local_source_read_approved=False)))
    def test_wrong_sample_digest(self):
        self.assertIn('sample digests differ', self.invoke(sample_sha256='0' * 64))
    def test_fixture_substitution(self):
        self.assertIn('makehuman-approved-sample', self.invoke(mutate_sample=lambda s: s.update(sample_class='nvwa-existing-fixture-control')))
    def test_unapproved_sample(self):
        self.assertIn('no explicit approval', self.invoke(mutate_sample=lambda s: s.update(approved=False)))
    def test_missing_data_roles(self):
        self.assertIn('data roles missing', self.invoke(mutate_sample=lambda s: s.update(files=[])))
    def test_missing_input_bytes(self):
        (self.root / 'target.control').unlink()
        self.assertIn('file unavailable', self.invoke())
    def test_tampered_input_bytes(self):
        (self.root / 'target.control').write_text('changed')
        self.assertIn('digest mismatch', self.invoke())
    def test_escaping_input_path(self):
        self.assertIn('within sample', self.invoke(mutate_sample=lambda s: s['files'][0].update(path='../outside')))
    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as outside:
            p = Path(outside) / 'body'; p.write_text('control')
            (self.root / 'basemesh.control').unlink()
            (self.root / 'basemesh.control').symlink_to(p)
            self.assertIn('symlink escapes', self.invoke())
    def test_missing_provenance(self):
        self.assertIn('provenance missing', self.invoke(mutate_sample=lambda s: s['files'][0].pop('license')))
    def test_missing_basis(self):
        self.assertIn('identity missing', self.invoke(mutate_sample=lambda s: s.pop('basis')))
    def test_missing_reference_identity(self):
        self.assertIn('reference manifest digest missing', self.invoke(mutate_sample=lambda s: s.pop('reference_manifest_sha256')))
    def test_missing_common_case(self):
        self.assertIn('distinct neutral', self.invoke(mutate_sample=lambda s: s['cases'].pop()))
    def test_missing_candidate(self):
        self.assertIn('candidate source unavailable', self.invoke())
    def test_missing_inventory_approval(self):
        self.candidate.mkdir()
        self.assertIn('inventory digest mismatch', self.invoke())
    def test_tree_digest_changes_with_content(self):
        self.candidate.mkdir()
        p = self.candidate / 'lib.rs'; p.write_text('first')
        first = run.tree_digest(self.candidate)
        p.write_text('second')
        self.assertNotEqual(first, run.tree_digest(self.candidate))
    def test_tree_digest_excludes_build_and_git_metadata(self):
        self.candidate.mkdir()
        (self.candidate / 'Cargo.toml').write_text('control')
        first = run.tree_digest(self.candidate)
        for name in ['target', '.git']:
            p = self.candidate / name; p.mkdir(); (p / 'noise').write_text('ignored')
        self.assertEqual(first, run.tree_digest(self.candidate))
    def test_tree_symlink_rejected(self):
        self.candidate.mkdir()
        (self.candidate / 'link').symlink_to(self.sample_path)
        with self.assertRaises(run.Blocked):
            run.tree_digest(self.candidate)


class SourceInventoryControls(unittest.TestCase):
    """Tiny handwritten source identity controls; never Humentity execution."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / 'src' / 'control.rs'
        self.path.parent.mkdir()
        self.data = b'// handwritten identity control\n'
        self.path.write_bytes(self.data)
        self.entry = dict(path='src/control.rs', size=len(self.data),
                          git_blob_sha1=hashlib.sha1(b'blob ' + str(len(self.data)).encode() + b'\0' + self.data).hexdigest())
        self.local = {'src/control.rs': hashlib.sha256(self.data).hexdigest()}
    def tearDown(self):
        self.temp.cleanup()
    def verify(self):
        run.verify_inventory(self.root, [self.entry], self.local)
    def test_exact_inventory_without_git_or_lock(self):
        self.verify()
    def test_false_source_even_when_free_sha_matches(self):
        replacement = b'x' * len(self.data)
        self.path.write_bytes(replacement)
        self.local['src/control.rs'] = hashlib.sha256(replacement).hexdigest()
        with self.assertRaisesRegex(run.Blocked, 'upstream Git blob mismatch'):
            self.verify()
    def test_oversize_before_read(self):
        self.path.write_bytes(self.data + b'x')
        with self.assertRaisesRegex(run.Blocked, 'size mismatch'):
            self.verify()
    def test_missing_file(self):
        self.path.unlink()
        with self.assertRaisesRegex(run.Blocked, 'source files missing'):
            self.verify()
    def test_extra_file(self):
        (self.root / 'Cargo.lock').write_text('forbidden upstream addition')
        with self.assertRaisesRegex(run.Blocked, 'unexpected candidate file'):
            self.verify()
    def test_extra_directory(self):
        (self.root / 'assets').mkdir()
        with self.assertRaisesRegex(run.Blocked, 'unexpected candidate directory'):
            self.verify()
    def test_source_symlink(self):
        self.path.unlink(); self.path.symlink_to('/etc/hosts')
        with self.assertRaisesRegex(run.Blocked, 'nonregular'):
            self.verify()
    def test_directory_symlink(self):
        (self.root / 'evil').symlink_to('/tmp', target_is_directory=True)
        with self.assertRaisesRegex(run.Blocked, 'nonregular'):
            self.verify()
    def test_nonregular_fifo(self):
        import os
        self.path.unlink(); os.mkfifo(self.path)
        with self.assertRaisesRegex(run.Blocked, 'nonregular'):
            self.verify()
    def test_inventory_traversal(self):
        self.entry['path'] = '../escape'
        with self.assertRaisesRegex(run.Blocked, 'unsafe'):
            self.verify()
    def test_approved_sha_mismatch(self):
        self.local['src/control.rs'] = '0' * 64
        with self.assertRaisesRegex(run.Blocked, 'local SHA256 mismatch'):
            self.verify()

class OutputPreservationControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.approval = self.root / 'approval.json'; self.approval.write_bytes(b'APPROVAL SENTINEL')
        self.sample = self.root / 'sample.json'; self.sample.write_bytes(b'SAMPLE SENTINEL')
        self.source = self.root / 'source'; self.source.mkdir()
        self.source_file = self.source / 'lib.rs'; self.source_file.write_bytes(b'SOURCE SENTINEL')
    def tearDown(self):
        self.temp.cleanup()
    def invoke(self, receipt):
        snapshots = {p: p.read_bytes() for p in [self.approval, self.sample, self.source_file]}
        with contextlib.redirect_stdout(io.StringIO()):
            result = run.main(['--approval', str(self.approval), '--sample', str(self.sample),
                               '--candidate', str(self.source), '--receipt', str(receipt)])
        self.assertEqual(result, 2)
        for p, data in snapshots.items(): self.assertEqual(p.read_bytes(), data)
    def test_receipt_is_approval(self): self.invoke(self.approval)
    def test_receipt_is_sample(self): self.invoke(self.sample)
    def test_receipt_is_source(self): self.invoke(self.source_file)
    def test_receipt_symlink_alias(self):
        p = self.root / 'alias.json'; p.symlink_to(self.approval); self.invoke(p)
    def test_receipt_hardlink_alias(self):
        import os
        p = self.root / 'alias.json'; os.link(self.approval, p); self.invoke(p)
    def test_log_is_input(self):
        p = self.root / 'result.json'
        self.approval.rename(p.with_suffix('.metadata.log'))
        self.approval = p.with_suffix('.metadata.log')
        self.invoke(p)
        self.assertFalse(p.exists())
    def test_log_symlink_alias(self):
        p = self.root / 'result.json'; p.with_suffix('.metadata.log').symlink_to(self.sample)
        self.invoke(p); self.assertFalse(p.exists())
    def test_existing_output_preserved(self):
        p = self.root / 'result.json'; p.write_bytes(b'OLD RESULT')
        self.invoke(p); self.assertEqual(p.read_bytes(), b'OLD RESULT')
    def test_run_command_never_truncates_log_alias(self):
        with self.assertRaises(FileExistsError):
            run.run_command(['false'], self.approval)
        self.assertEqual(self.approval.read_bytes(), b'APPROVAL SENTINEL')

if __name__ == '__main__':
    unittest.main()
