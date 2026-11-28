"""Check both live contact selectors and the exact predecessor, including failed edits."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

import contact_fit_source_context as fit
import contact_target_source_context as contact

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    spec = importlib.util.spec_from_file_location('nvwa_contact_' + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gates(root):
    exp = root / contact.EXP72
    eye = root / contact.EXP73
    a = load(exp / 'run.py')
    f = load(eye / 'frozen_context.py')
    pins = json.loads((exp / 'pins.json').read_bytes())
    raw = (eye / 'FROZEN-INPUTS.json').read_bytes()
    original = json.loads(raw)
    contexts = f.current_source_contexts(eye, raw, original)
    running = f._running_source_context(eye, original, contexts)
    query = f._motion_query_source_context(eye, running)
    cpu = f._cpu_context(eye, query[1])
    return (lambda target: a.check_source_context(target, pins),
            lambda target: f.integration_source_context(eye, cpu, target))


def source_tree(destination, *, predecessor, contact_root=None):
    """Materialize the two selectors' files without copying build outputs or downloading history."""
    base = ROOT if contact_root is None else contact_root
    first, second = gates(base)
    names = set(first(base)['files']) | second(base)[1].keys()
    for directory in (contact.EXP72, contact.EXP73):
        for path in (base / directory).rglob('*'):
            if not {'target', '.work', '__pycache__'}.intersection(path.relative_to(base).parts) and path.is_file():
                names.add(path.relative_to(base).as_posix())
    # Unpinned Rust source names still participate in the successor inventory.
    for crate in ('nvwa-cli', 'nvwa-core', 'nvwa-runtime'):
        for directory in ('src', 'tests'):
            for path in (base / 'crates' / crate / directory).rglob('*.rs'):
                names.add(path.relative_to(base).as_posix())
    if contact_root is None:
        names -= fit.ADDED | {fit.HELPER, fit.MANIFEST}
    if predecessor:
        names -= contact.ADDED | {contact.HELPER, contact.MANIFEST}
    for name in names:
        retained = contact.FIXTURE_PATH + name if predecessor and name in contact.CHANGED else name
        if contact_root is None and retained in fit.CHANGED:
            retained = fit.FIXTURE_PATH + retained
        source = base / retained
        dest = destination / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        # This tree is immutable. Tests replace links before mutating test bytes.
        os.link(source, dest)


class ContactTargetContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix='nvwa-contact-target-predecessor-')
        cls.addClassCleanup(temporary.cleanup)
        cls.root = Path(temporary.name).resolve()
        source_tree(cls.root, predecessor=False)

    def test_admit_successor_and_reject_missing_mixed_and_unknown_sources(self):
        first, second = gates(self.root)
        a, b = first(self.root), second(self.root)
        self.assertEqual((a['id'], b[0]), (contact.ID, contact.ID))
        self.assertEqual(a['current_rust_execution'], 'NOT-RUN')
        after = json.loads((self.root / contact.MANIFEST).read_bytes())['after']
        for name, expected in after.items():
            raw = (self.root / name).read_bytes()
            pin = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            if name not in contact.SELECTORS:
                self.assertEqual(expected, pin)
            self.assertEqual((a['files'][name], b[1][name]), (pin['sha256'], pin))
        with tempfile.TemporaryDirectory() as temp:
            tree = Path(temp).resolve()
            source_tree(tree, predecessor=False, contact_root=self.root)
            for name, replacement, reason in (
                (contact.TEST, None, 'missing/nonregular'),
                ('crates/nvwa-core/src/stage.rs', self.root / (contact.FIXTURE_PATH + 'crates/nvwa-core/src/stage.rs'), 'source bytes mismatch'),
                ('crates/nvwa-runtime/src/lib.rs', b'unknown bytes', 'source bytes mismatch'),
                ('crates/nvwa-cli/src/unknown.rs', b'fn extra() {}', 'Rust source inventory mismatch'),
                (contact.MANIFEST, b'{}', 'candidate manifest identity'),
                (contact.HELPER, b'# incomplete', 'candidate helper identity'),
            ):
                target = tree / name
                target.unlink(missing_ok=True)
                if isinstance(replacement, Path):
                    os.link(replacement, target)
                elif replacement is not None:
                    target.write_bytes(replacement)
                for gate in (first, second):
                    with self.subTest(name=name, gate=gate), self.assertRaisesRegex(ValueError, reason):
                        gate(tree)
                target.unlink(missing_ok=True)
                if (self.root / name).is_file():
                    os.link(self.root / name, target)
            (tree / contact.TEST).unlink()
            (tree / contact.TEST).symlink_to(self.root / contact.TEST)
            for gate in (first, second):
                with self.assertRaisesRegex(ValueError, 'symlink'):
                    gate(tree)

    def test_both_live_selectors_still_admit_exact_travel_predecessor(self):
        with tempfile.TemporaryDirectory() as temp:
            tree = Path(temp).resolve()
            source_tree(tree, predecessor=True, contact_root=self.root)
            current = gates(self.root)
            predecessor = gates(tree)
            old = predecessor[0](tree), predecessor[1](tree)
            self.assertEqual(old[0]['id'], 'nvwa-travel-query-source-context-v1')
            self.assertEqual(old[0]['id'], old[1][0])
            self.assertEqual(current[0](tree), old[0])
            self.assertEqual(current[1](tree), old[1])
            for name in contact.TRAVEL_EXTRA_PINS:
                path = tree / name
                path.unlink()
                for gate in current:
                    with self.subTest(missing=name), self.assertRaisesRegex(ValueError, 'missing/nonregular'):
                        gate(tree)
                path.write_bytes(b'unknown successor bytes')
                for gate in current:
                    with self.subTest(orphan=name), self.assertRaisesRegex(ValueError, 'missing/nonregular'):
                        gate(tree)
                path.unlink()
                os.link(self.root / (contact.FIXTURE_PATH + name), path)

    def test_reject_edited_helpers_before_loading_them_in_the_candidate_checkout(self):
        with tempfile.TemporaryDirectory() as temp:
            tree = Path(temp).resolve()
            source_tree(tree, predecessor=False, contact_root=self.root)
            first, second = gates(tree)
            sentinel = tree / 'untrusted-helper-executed'
            for name in ('contact_target_source_context.py', 'travel_query_source_context.py', 'integration_context.py'):
                original = self.root / contact.EXP72 / name
                local = tree / contact.EXP72 / name
                local.unlink()
                for edit in (b'\n# harmless edit\n',
                             f"\nfrom pathlib import Path\nPath({str(sentinel)!r}).touch()\n".encode()):
                    local.write_bytes(original.read_bytes() + edit)
                    for gate in (first, second):
                        reason = 'contact helper template identity' if name == 'contact_target_source_context.py' else 'source helper identity'
                        with self.subTest(helper=name), self.assertRaisesRegex(ValueError, reason):
                            gate(tree)
                        self.assertFalse(sentinel.exists())
                local.unlink()
                os.link(original, local)


    def test_coordinated_helper_and_selector_digest_edits_fail_before_exec(self):
        with tempfile.TemporaryDirectory() as temp:
            tree = Path(temp).resolve()
            source_tree(tree, predecessor=False, contact_root=self.root)
            helper = tree / contact.HELPER
            old = helper.read_bytes()
            sentinel = tree / 'untrusted-coordinated-exec'
            changed = old + f"\nfrom pathlib import Path\nPath({str(sentinel)!r}).touch()\n".encode()
            helper.unlink()
            helper.write_bytes(changed)
            old_sha = hashlib.sha256(old).hexdigest().encode()
            new_sha = hashlib.sha256(changed).hexdigest().encode()
            for name in contact.SELECTORS:
                path = tree / name
                raw = path.read_bytes()
                self.assertEqual(raw.count(old_sha), 1)
                path.unlink()
                path.write_bytes(raw.replace(old_sha, new_sha))
            first, second = gates(tree)
            history = load(tree / 'scripts/check-v15-history.py')
            for gate in (first, second, history.check_contact_bootstrap):
                with self.subTest(gate=gate), self.assertRaisesRegex(ValueError, 'contact helper template identity'):
                    gate(tree)
                self.assertFalse(sentinel.exists())
