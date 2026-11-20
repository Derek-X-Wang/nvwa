# Hosted V15 history replay stdlib prewarm

Only GitHub's hosted Linux `portable-eye` job prewarms installed CPython
standard-library bytecode for the full V15 history replay. The replay uses an
isolated compiler and a fresh private scratch directory. It checks normal and
`-O` cache contents against the actual compiler output and source bytes. There
are no retained caches, downloads, or cached repository imports, tests, assets,
fixture checks, or outcomes. A failed cache check fails the replay; it does not
replace or skip a test. The workflow, 20-minute step limit, existing suite
selection, and original historical Git object are unchanged.

Local replay, offline export, and narrowed invocations retain their original
empty-cache behavior. The focused cache controls are:

```sh
python3 -B scripts/test-ci-v15-stdlib-cache.py
python3 -B -O scripts/test-ci-v15-stdlib-cache.py
```
