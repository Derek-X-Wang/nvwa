# Independent R2 targeted re-review — 53 stale partial fix

Outcome: **P2 resolved. No additional findings in the targeted fix.**

The real `fetch()` function now validates the existing destination directly when reusing it. It does not select or promote a sibling `.part`. New downloads and license reuse create a unique owned temporary; size, SHA256 and optional Git-blob identity are checked on that same candidate before promotion. Failure removes only the temporary owned by this invocation. Existing approved bytes, unrelated stale partials and license inputs remain preserved.

Reviewed exact hashes:

- `experiments/53-character-comparison/delivery/download_approved.py`: `5e5016c402e1819c70642798fa8b90cd5a0bf6fff82afa08c6611c40ec1fd6f2`.
- `experiments/53-character-comparison/delivery/test_download_approved.py`: `6bad73c45402aec3a174c8c10419b95701e20d3e00d5a96e537bbe025e8966b6`.

Executed from the assigned research worktree:

```sh
python3 -B experiments/53-character-comparison/delivery/test_download_approved.py -v
python3 -O -B experiments/53-character-comparison/delivery/test_download_approved.py -v
python3 -B .work/character-actual-independent-review/verify_stale_part_fix.py
```

Both test modes passed all 11 tests. Logs are `fix-tests-normal.log` and `fix-tests-optimized.log`. Cases exercise existing reuse with SHA256 and Git-blob checks, both mismatch rejections, mocked fresh download, fresh hash failure, transport failure, license reuse and rejection, HTTP input and final redirect rejection, short body and oversized body rejection. All transport is mocked or explicitly forbidden.

The third command independently repeats the original reviewer counterexample with the fixed actual function and transport forbidden. The approved destination and stale partial both survive unchanged, and the receipt now matches actual bytes. Receipt: `stale-part-fix-verification.json`. Original red evidence remains in `stale-part-reproduction.json`; it was not overwritten.

The successful `-O` run demonstrates that size/hash/Git/HTTPS checks inside the fixed `fetch()` do not depend on Python assertions. It is not a claim about all admission/preflight assertions elsewhere in the historical downloader.

VERIFIED — Original retry-preservation invariant restored at the frozen hashes; targeted offline controls pass normally and under `-O`. No real network/download/build/GPU executed. No reviewed files changed. 55 remains excluded; graphical, animation, adoption and previous broader review bounds are unchanged. No reviewer-owned processes remain; private review evidence retained for root.
