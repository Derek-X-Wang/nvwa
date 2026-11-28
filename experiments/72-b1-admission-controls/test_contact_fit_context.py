"""Admit the two exact contact contexts, and reject one change at a time."""
from contextlib import contextmanager, ExitStack
import hashlib
import json
import os
import runpy
from pathlib import Path
import tempfile
import unittest

from test_contact_target_context import gates

ROOT = Path(__file__).resolve().parents[2]
EXP72 = 'experiments/72-b1-admission-controls'
EXP73 = 'experiments/73-high-poly-eyes'
MANIFEST = EXP72 + '/input-context-contact-fit-v1.json'
HELPER = EXP72 + '/contact_fit_source_context.py'
BOOTSTRAP = EXP72 + '/contact_fit_bootstrap.py'
FIXTURES = EXP72 + '/pre-contact-fit/'
SUCCESSOR = 'nvwa-contact-fit-source-context-v1'
PREDECESSOR = 'nvwa-contact-target-source-context-v1'
CORE_V18 = 'crates/nvwa-core/src/b1.rs'
MODULES = (
    'crates/nvwa-cli/src/motion_query/contact_fit.rs',
    'crates/nvwa-cli/src/motion_query/contact_recheck.rs',
    'crates/nvwa-runtime/src/b1/sole_measurement.rs',
)
WORKS = 'crates/nvwa-cli/tests/fixtures/contact-fit/'
WORK_DIGESTS = {
    'iris/start.nvwa.json': '2bf3efceda79ed3d90d61886518120c900867ac637286ddc181f8495315d0814',
    'iris/reference.nvwa.json': '5b3ba83e8a44c61b1bf4d0a624ea8519b67e3627350319a9b2d575a330a3eccc',
    'iris/accepted.nvwa.json': '6fc2cea4b5091b0a0e3e1d0c4d9aaeb2cb2b3afbb0f654ce66a336dbb68d625b',
    'mora/start.nvwa.json': 'c2d9ccafacbfba3a0a2d0cd465ee28e87df60be9542582fcd36484b40ffd687e',
    'mora/reference.nvwa.json': 'e2f7389274834d6eb889faf8033325bcc321d01350dd0f645be39f4646bbc4f1',
    'mora/accepted.nvwa.json': '5da679e027b86ad62f43ed4cda83267c768da72cdab8e9f83c811f54e830afec',
}


def link_source_tree(tree, source_names, before=None):
    # Building from selector inputs keeps the test independent of Git and build artifacts.
    for name in source_names:
        source = ROOT / name
        if before is not None:
            if name in (MANIFEST, HELPER) or (name in before and before[name] is None):
                continue
            if name in before:
                source = ROOT / (FIXTURES + name)
        destination = tree / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, destination)


@contextmanager
def replace_entry(tree, name):
    """Park the original entry outside both trees. Never write to a hardlinked inode."""
    path = tree / name
    with ExitStack() as cleanup:
        missing_dirs = []
        parent = path.parent
        while not parent.exists():
            missing_dirs.append(parent)
            parent = parent.parent
        for parent in reversed(missing_dirs):
            parent.mkdir()
            cleanup.callback(parent.rmdir)
        if path.exists() or path.is_symlink():
            parked = Path(cleanup.enter_context(tempfile.TemporaryDirectory(dir=tree.parent))) / 'entry'
            path.rename(parked)
            cleanup.callback(parked.rename, path)
        cleanup.callback(path.unlink, missing_ok=True)
        yield path


class ContactFitContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.live = gates(ROOT)
        cls.current72, cls.current73 = [gate(ROOT) for gate in cls.live]
        cls.manifest = json.loads((ROOT / MANIFEST).read_bytes())

        names = set(cls.current72['files']) | cls.current73[1].keys()
        for folder in (EXP72, EXP73):
            for path in (ROOT / folder).rglob('*'):
                relative = path.relative_to(ROOT)
                if not {'target', '.work', '__pycache__'}.intersection(relative.parts) and path.is_file():
                    names.add(relative.as_posix())
        for crate in ('nvwa-cli', 'nvwa-core', 'nvwa-runtime'):
            for folder in ('src', 'tests'):
                names.update(path.relative_to(ROOT).as_posix()
                             for path in (ROOT / 'crates' / crate / folder).rglob('*.rs'))

        temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temp.cleanup)
        cls.candidate = Path(temp.name).resolve() / 'candidate'
        cls.previous = cls.candidate.parent / 'predecessor'
        link_source_tree(cls.candidate, names)
        link_source_tree(cls.previous, names, cls.manifest['before'])

    def require_rejection(self, tree, name):
        for label, gate in zip(('72', '73'), self.live):
            with self.subTest(path=name, selector=label), self.assertRaises(ValueError):
                gate(tree)

    def test_exact_successor_and_original_works(self):
        a, b = self.current72, self.current73
        self.assertEqual((a['id'], b[0]), (SUCCESSOR, SUCCESSOR))
        self.assertEqual(a['current_rust_execution'], 'NOT-RUN')
        self.assertEqual(self.manifest['predecessor_context'], PREDECESSOR)
        self.assertEqual(self.manifest['predecessor_commit'], '8da2d17fcde1a43d2d52595cbf1a808ae3b270b2')
        for relative, digest in WORK_DIGESTS.items():
            name = WORKS + relative
            raw = (ROOT / name).read_bytes()
            with self.subTest(work=relative):
                self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
                self.assertEqual(json.loads(raw)['profile']['backend']['schema_version'], 18)
                self.assertEqual(a['files'][name], digest)
                self.assertEqual(b[1][name], {'bytes': len(raw), 'sha256': digest})
        for name in (*MODULES, CORE_V18, 'crates/nvwa-cli/tests/contact_query.rs'):
            raw = (ROOT / name).read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            self.assertEqual(a['files'][name], digest, name)
            self.assertEqual(b[1][name], {'bytes': len(raw), 'sha256': digest}, name)
        # Prove that the scratch tree itself passes before interpreting a rejection.
        self.assertEqual([gate(self.candidate) for gate in self.live], [a, b])

    def test_exact_predecessor_and_single_successor_markers(self):
        original = [gate(self.previous) for gate in gates(self.previous)]
        self.assertEqual((original[0]['id'], original[1][0]), (PREDECESSOR, PREDECESSOR))
        self.assertEqual([gate(self.previous) for gate in self.live], original)
        for name in (*MODULES, CORE_V18, WORKS + 'iris/start.nvwa.json', MANIFEST, HELPER, BOOTSTRAP):
            with replace_entry(self.previous, name) as path:
                os.link(ROOT / name, path)
                self.require_rejection(self.previous, name)

    def test_missing_modules_and_mixed_v18_source(self):
        for name in MODULES:
            with replace_entry(self.candidate, name):
                self.require_rejection(self.candidate, name)
        with replace_entry(self.candidate, CORE_V18) as path:
            os.link(self.previous / CORE_V18, path)
            self.require_rejection(self.candidate, CORE_V18)

    def test_single_byte_edits_to_modules_works_controls_and_retained_source(self):
        works = [WORKS + relative for relative in WORK_DIGESTS]
        for name in (*MODULES, *works, MANIFEST, HELPER, BOOTSTRAP, FIXTURES + CORE_V18):
            raw = (ROOT / name).read_bytes()
            with replace_entry(self.candidate, name) as path:
                path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
                self.require_rejection(self.candidate, name)

    def test_rust_source_inventory_in_each_protected_crate(self):
        for name in ('crates/nvwa-cli/src/motion_query/unregistered.rs',
                     'crates/nvwa-core/tests/unregistered.rs',
                     'crates/nvwa-runtime/src/b1/unregistered.rs',
                     'crates/nvwa-runtime/build.rs', 'crates/nvwa-cli/examples/extra.rs',
                     'crates/nvwa-core/benches/extra.rs', 'crates/nvwa-cli/extra.rs'):
            with replace_entry(self.candidate, name) as path:
                path.write_bytes(b'// unregistered source\n')
                self.require_rejection(self.candidate, name)

    def test_history_preflight_binds_the_reviewed_release(self):
        history = runpy.run_path(str(ROOT / 'scripts/check-v15-history.py'))
        check = history['check_contact_bootstrap']
        check(self.candidate)
        # Even a consistent helper + alternate manifest must not replace the
        # reviewed release. A harmless JSON whitespace edit changes its bytes.
        with ExitStack() as edits:
            policy = edits.enter_context(replace_entry(self.candidate, MANIFEST))
            original = (ROOT / MANIFEST).read_bytes()
            new = original + b'\n'
            policy.write_bytes(new)
            helper = edits.enter_context(replace_entry(self.candidate, HELPER))
            helper.write_bytes((ROOT / HELPER).read_bytes().replace(
                hashlib.sha256(original).hexdigest().encode(), hashlib.sha256(new).hexdigest().encode()))
            with self.assertRaisesRegex(history['ReplayError'], 'release manifest identity'):
                check(self.candidate)
        for name in (EXP72 + '/run.py', EXP73 + '/frozen_context.py', 'scripts/check-v15-live73.py'):
            with self.subTest(name=name), replace_entry(self.candidate, name) as altered:
                altered.write_bytes((ROOT / name).read_bytes() + b'\n')
                with self.assertRaises(history['ReplayError']):
                    check(self.candidate)

    def test_equal_bytes_through_file_or_directory_symlink(self):
        for name in (MODULES[0], WORKS + 'mora', FIXTURES + CORE_V18):
            with replace_entry(self.candidate, name) as path:
                path.symlink_to(ROOT / name)
                self.require_rejection(self.candidate, name)
