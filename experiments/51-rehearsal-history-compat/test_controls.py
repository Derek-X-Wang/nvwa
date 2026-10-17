"""Mutation/refusal controls for the real authenticated historical boundary."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

import audit


class CompatibilityControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='nvwa-history-controls-')
        # macOS exposes the system temporary directory through /var's symlink.
        cls.base = Path(cls.temporary.name).resolve()
        cls.repo = cls.base/'repo'
        cls.repo.mkdir()
        cls.snapshot = audit.preflight(audit.HERE.parents[1])
        audit.stage(cls.snapshot, cls.repo)
        cls.material = cls.base/'material'
        cls.material.mkdir()
        shutil.copy2(audit.HERE/'MANIFEST.json', cls.material/'MANIFEST.json')
        shutil.copytree(audit.HERE/'sources', cls.material/'sources')

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def restored(self):
        self.assertEqual(audit.preflight(self.repo, self.material), self.snapshot)

    def mutate(self, root, relative, replacement, error):
        path = root/relative
        previous = path.read_bytes()
        try:
            path.write_bytes(replacement)
            with self.assertRaisesRegex(audit.Rejected, error):
                audit.preflight(self.repo, self.material)
        finally:
            path.write_bytes(previous)
        self.restored()

    def test_baseline_original_clis_and_scope(self):
        self.restored()
        result = audit.run_staged(self.repo, 'historical48', bool(sys.flags.optimize))
        output = json.loads(result['stdout'])
        self.assertEqual(output['original_cli']['source_inputs'], 54)
        self.assertEqual(output['fresh_GUI_replay'], 'NOT-RUN')
        self.assertEqual(set(output['current49_retained_builds']), {'native', 'web'})

    def test_archive_source_tamper_and_restored_green(self):
        name = 'sources/crates/nvwa-core/src/lib.rs.txt'
        self.mutate(self.material, name, (self.material/name).read_bytes()+b'\n', 'input identity changed')

    def test_source_pin_tamper_and_restored_green(self):
        manifest = json.loads((self.material/'MANIFEST.json').read_bytes())
        manifest['files']['crates/nvwa-core/src/lib.rs']['sha256'] = '0'*64
        self.mutate(self.material, 'MANIFEST.json', json.dumps(manifest).encode(), 'manifest pin changed')

    def test_missing_source_path_and_restored_green(self):
        path = self.material/'sources/crates/nvwa-core/src/lib.rs.txt'
        previous = path.read_bytes()
        try:
            path.unlink()
            with self.assertRaisesRegex(audit.Rejected, 'missing or extra archived source path'):
                audit.preflight(self.repo, self.material)
        finally:
            path.write_bytes(previous)
        self.restored()

    def test_extra_source_path_and_restored_green(self):
        path = self.material/'sources/untrusted.rs.txt'
        try:
            path.write_bytes(b'extra')
            with self.assertRaisesRegex(audit.Rejected, 'missing or extra archived source path'):
                audit.preflight(self.repo, self.material)
        finally:
            path.unlink()
        self.restored()

    def test_untrusted_source_path_mapping(self):
        for unsafe in ['../outside.rs', '/absolute.rs', 'sources/../outside.rs', 'sources//double.rs', 'sources\\win.rs']:
            with self.subTest(path=unsafe):
                manifest = json.loads((self.material/'MANIFEST.json').read_bytes())
                row = manifest['files'].pop('crates/nvwa-core/src/lib.rs')
                manifest['files'][unsafe] = row
                self.mutate(self.material, 'MANIFEST.json', json.dumps(manifest).encode(), 'unsafe relative path')

    def test_archive_alias_mapping_refused(self):
        manifest = json.loads((self.material/'MANIFEST.json').read_bytes())
        manifest['files']['crates/nvwa-core/src/lib.rs']['archive_path'] = 'sources/Cargo.toml.txt'
        self.mutate(self.material, 'MANIFEST.json', json.dumps(manifest).encode(), 'archive path mapping changed')

    def test_historical_asset_capture_source_receipt_tamper(self):
        names = ['experiments/48-genuine-fixture-work/artifacts/assets/generated/genuine44-calibrated47.glb',
                 audit.E49+'probe/results/native.json',
                 'experiments/43-rig-mapping/spike.py',
                 'experiments/41-real-short-motion/evidence/source-receipts.json',
                 audit.E49+'historical48/sources/nvwa-studio-lib.rs.txt']
        for name in names:
            with self.subTest(path=name):
                self.mutate(self.repo, name, (self.repo/name).read_bytes()+b'\n', 'input identity changed')

    def test_extra_historical_input_refused(self):
        path = self.repo/audit.E49/'unexpected.json'
        try:
            path.write_bytes(b'{}')
            with self.assertRaisesRegex(audit.Rejected, 'missing or extra historical input path'):
                audit.preflight(self.repo, self.material)
        finally:
            path.unlink()
        self.restored()

    def test_symlink_source_and_input_refused(self):
        for root, relative in [(self.material, 'sources/crates/nvwa-core/src/lib.rs.txt'),
                               (self.repo, audit.E49+'probe/results/native.json')]:
            with self.subTest(path=relative):
                path = root/relative
                previous = path.read_bytes()
                target = self.base/'symlink-target'
                target.write_bytes(previous)
                try:
                    path.unlink()
                    path.symlink_to(target)
                    with self.assertRaisesRegex(audit.Rejected, 'symlink'):
                        audit.preflight(self.repo, self.material)
                finally:
                    path.unlink()
                    path.write_bytes(previous)
                    target.unlink()
                self.restored()

    def test_symlink_root_ancestor_refused(self):
        link = self.base/'linked-parent'
        try:
            link.symlink_to(self.base, target_is_directory=True)
            with self.assertRaisesRegex(audit.Rejected, 'symlink input root ancestor'):
                audit.preflight(link/'repo', self.material)
        finally:
            link.unlink()
        self.restored()

    def test_original_source_pin_rejects_mutation_then_passes_restored(self):
        path = self.repo/'Cargo.toml'
        previous = path.read_bytes()
        try:
            path.write_bytes(previous+b'\n')
            with self.assertRaisesRegex(audit.Rejected, 'original historical48 CLI exit 1.*input identity changed: Cargo.toml'):
                audit.run_staged(self.repo, 'historical48', bool(sys.flags.optimize))
        finally:
            path.write_bytes(previous)
        self.assertEqual(audit.run_staged(self.repo, 'historical48', bool(sys.flags.optimize))['exit_code'], 0)

    def test_original_capture_rejects_mutation_then_passes_restored(self):
        path = self.repo/audit.E49/'probe/results/native.json'
        previous = path.read_bytes()
        capture = json.loads(previous)
        capture['samples'][0]['nodes'][0]['global'][12] += 1
        try:
            path.write_text(json.dumps(capture))
            with self.assertRaisesRegex(audit.Rejected, 'original native-capture CLI exit 1'):
                audit.run_staged(self.repo, 'native-capture', bool(sys.flags.optimize))
        finally:
            path.write_bytes(previous)
        self.assertEqual(audit.run_staged(self.repo, 'native-capture', bool(sys.flags.optimize))['exit_code'], 0)

    def test_current_product_changes_are_outside_historical_scope(self):
        # The staged product source is the historical context, never a current-source check.
        path = self.repo/'crates/nvwa-core/src/lib.rs'
        previous = path.read_bytes()
        try:
            path.write_bytes(b'new current product source, not the retained capture cohort')
            self.restored()
        finally:
            path.write_bytes(previous)

    def test_archived_packaging_tools_tamper_then_restored_green(self):
        for name in ['scripts/build-web.sh', 'scripts/package-native.py']:
            relative = 'sources/'+name+'.txt'
            with self.subTest(path=name):
                self.mutate(self.material, relative,
                            (self.material/relative).read_bytes()+b'\n',
                            'input identity changed: '+name)

    def test_current_packaging_tools_are_outside_historical_scope(self):
        for name in ['scripts/build-web.sh', 'scripts/package-native.py']:
            with self.subTest(path=name):
                path = self.repo/name
                previous = path.read_bytes()
                try:
                    path.write_bytes(b'current B1 packaging source; not historical capture evidence')
                    self.restored()
                    snapshot = audit.preflight(self.repo, self.material)
                    with tempfile.TemporaryDirectory(prefix='nvwa-packaging-history-') as temporary:
                        stage = Path(temporary).resolve()
                        audit.stage(snapshot, stage)
                        self.assertEqual((stage/name).read_bytes(), previous)
                        # Original source bindings and capture checks both run
                        # on original tool bytes, not this changed live source.
                        for check in ['historical48', 'web-capture']:
                            self.assertEqual(audit.run_staged(stage, check,
                                                             bool(sys.flags.optimize))['exit_code'], 0)
                finally:
                    path.write_bytes(previous)
                self.restored()

    def test_duplicate_manifest_key_refused(self):
        raw = (self.material/'MANIFEST.json').read_bytes()
        self.mutate(self.material, 'MANIFEST.json', raw.replace(b'{', b'{"files":{},', 1), 'duplicate JSON key')


if __name__ == '__main__':
    unittest.main()
