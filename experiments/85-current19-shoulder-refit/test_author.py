"""Author reservation/source-equivalence controls. Actual generation is NOT-RUN."""
import ast
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import author as a


def neutral_math_body(path):
    module=ast.parse(path.read_text())
    attempt=next(node for node in module.body if isinstance(node,ast.FunctionDef) and node.name=='attempt')
    body=next(node for node in attempt.body if isinstance(node,ast.Try)).body
    end=next(i for i,node in enumerate(body) if isinstance(node,ast.Assign) and
             any(isinstance(target,ast.Name) and target.id=='manifest' for target in node.targets))
    return ast.dump(ast.Module(body=body[:end],type_ignores=[]),include_attributes=False)


class AuthorControls(unittest.TestCase):
    def test_literal_unchanged_neutral_math_block(self):
        self.assertEqual(neutral_math_body(Path(a.__file__)),neutral_math_body(Path(a.reference.__file__)))
    def test_unchanged_pure_helpers(self):
        for name in ('nearest_plane','positive_scales','interpolate','triangle_sources'):
            self.assertIs(getattr(a,name),getattr(a.reference,name))
        self.assertEqual(len(a.SAMPLES),7)
        self.assertEqual((a.MARGIN,a.RESIDUAL_FLOOR,a.MAX_DELTA),(.001,.0009999,.020))
    def test_one_exclusive_attempt_directory(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d).resolve()/'one-attempt';freeze={'attempt_directory':str(out)}
            a.reserve_attempt(out,freeze)
            with self.assertRaises(ValueError):a.reserve_attempt(out,freeze)
    def test_another_directory_is_not_an_implicit_retry(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();freeze={'attempt_directory':str(root/'one-attempt')}
            with self.assertRaises(ValueError):a.reserve_attempt(root/'another-attempt',freeze)
            self.assertFalse((root/'another-attempt').exists())
    def test_missing_stage_freeze_refuses_before_planes(self):
        with tempfile.TemporaryDirectory() as d,patch.object(a,'nearest_plane') as plane:
            root=Path(d).resolve()
            with self.assertRaises(ValueError):a.attempt(root/'missing',root,root/'one-attempt')
            plane.assert_not_called()
            self.assertFalse((root/'one-attempt').exists())


if __name__=='__main__':unittest.main()
