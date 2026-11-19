#!/usr/bin/env python3
"""Discover and run original unittest methods in the selected source root."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import sys
import unittest


def leaves(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from leaves(item)
        else:
            yield item


def tests(start):
    loader = unittest.TestLoader()
    found = list(leaves(loader.discover(str(start), pattern="test_*.py")))
    if loader.errors:
        raise ValueError("test discovery failed: " + "\n".join(loader.errors))
    indexed = {test.id(): test for test in found}
    if not found or len(indexed) != len(found):
        raise ValueError("empty or duplicate unittest identity")
    return indexed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cohort", choices=["72-b1-admission-controls", "73-high-poly-eyes"])
    parser.add_argument("--run-test-ids-stdin", action="store_true")
    args = parser.parse_args()
    found = tests(Path("experiments") / args.cohort)
    if not args.run_test_ids_stdin:
        projected = {}
        for name, test in found.items():
            method = getattr(test, test._testMethodName)
            cls = type(test)
            entries = [method, cls.setUpClass, cls.tearDownClass, cls.setUp, cls.tearDown]
            projected[name] = hashlib.sha256(
                b"\0".join(inspect.getsource(obj).encode() for obj in entries)
            ).hexdigest()
        print(json.dumps(projected))
        return 0
    ids = json.loads(sys.stdin.read())
    if not ids or len(ids) != len(set(ids)) or not set(ids) <= found.keys():
        raise ValueError("invalid planned test subset")
    selected = unittest.TestSuite(found[t] for t in ids)
    result = unittest.TextTestRunner(verbosity=2).run(selected)
    if result.testsRun != len(ids) or result.skipped or not result.wasSuccessful():
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
