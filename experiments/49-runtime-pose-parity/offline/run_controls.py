"""Retain normal/optimized results without manufacturing runtime captures."""
import json
import platform
from pathlib import Path
import sys
import unittest

from test_evaluator import EvaluatorTests


suite = unittest.defaultTestLoader.loadTestsFromTestCase(EvaluatorTests)
names = [test.id() for test in suite]
result = unittest.TextTestRunner(verbosity=2).run(suite)
report = {'status': 'PASS' if result.wasSuccessful() else 'FAIL',
          'scope': 'offline expected evaluator and synthetic adapter controls; not actual native/Web evidence',
          'python': platform.python_version(), 'optimized': bool(sys.flags.optimize),
          'tests_run': result.testsRun, 'control_names': names,
          'failures': [{'test': test.id(), 'traceback': trace} for test, trace in result.failures],
          'errors': [{'test': test.id(), 'traceback': trace} for test, trace in result.errors]}
output = Path(__file__).with_name('controls-optimized.json' if sys.flags.optimize else 'controls-normal.json')
output.write_text(json.dumps(report, indent=2)+'\n')
raise SystemExit(0 if result.wasSuccessful() else 1)
