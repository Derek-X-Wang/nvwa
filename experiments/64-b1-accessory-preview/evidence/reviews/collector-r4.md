# Private native collector targeted re-review — r4

**CLEAR for the scoped pre-send-error recovery change.** No replay, relaxed capture identity, or changed-error suppression was found in this diff. Actual application recovery remains a separate root-owned check.

Verified identities:

- `collection/collect_native.py`: `fbed0bb30e0332de052b70053b1d6af1b5cad100765a98a2764b9a311dda1488` (matches dispatch and remained unchanged after tests).
- `collection/test_collector.py`: `fea1622f45586534c60c3313b69ac2a5bfb61f686aec9054162ca60ec52ebe4b`.
- `collection/README.md`: `06ea3e45e218cbf4b8fb7b53272ef17c9929552bf0cf0ae9e6db882e5731695f`.

Compared the current CLI directly with retained `collect_native.py.r3`. Its only changes record the hash of the preserved original report (`:247-254`) and make the error-report branch wait when the observed bytes have that same hash (`:279-285`). Request validation, shape/geometry/appearance admission, path guards, prior-ID refusal, and final report reread are unchanged.

The new state has the intended limits:

- The hash comes from `original-report.raw` before the one command replacement. No prior report means no matching old-error hash.
- Each changed observed report is preserved before parsing or applying the error rule. An error with different bytes raises immediately, including an error without a request ID.
- An identical old error only sleeps and returns to the bounded polling loop. It cannot reach `verify`, write an accepted envelope, or mark captured. Persistence ends in a failed timeout receipt with original/observed raw evidence retained.
- A subsequent matching captured response must still pass the unchanged exact request and evidence checks. `automatic-rebind`, other request IDs, stale states, and mismatched frames remain ineligible.
- There is still exactly one command replacement outside the polling loop. No resend, ID rename, or retry was added.

Byte identity is the intentional boundary: a newly emitted error with bytes identical to the pre-send error is indistinguishable under this rule and may wait until timeout. It still cannot produce a successful capture. The guarantee here is immediate rejection of **changed bytes**, not detection of every same-text error re-emission.

Independently ran all **14 current actual-function fixture tests** using `python3 -B`. Loaded the real CLI/tests in memory; redirected only temporary fixture directories into the authorized `.work/appearance64/collector-review-r4-scratch`, and set the CLI module's real `__file__` for its self-path guard. No collector/test source was edited.

```text
Ran 14 tests in 0.683s
OK
remaining_test_threads 0
```

The added controls exercised delayed recovery after the exact pre-send error, rejection of a changed ID-less error, and bounded timeout with raw preservation when the old error persists. Existing controls also passed for identity/structure/mode checks, the authentic empty-runtime variants, invalid/residual runtime rejection, automatic-rebind exclusion, original IDs, protected inputs, and raw-byte preservation.

Evidence log: `.work/appearance64/collector-review-r4-scratch/fourteen-tests.log`. All temporary fixture directories were removed and all test-created threads had exited. Only this report and the authorized scratch log were retained.

VERIFIED — exact private collector diff, final hash, and 14 synthetic pipeline/validator tests. NOT-RUN — actual native invalid-UTF8 recovery, real application channels, UI/GPU, numerical verification, server, build, Git, or publication. No original experiment source/public verification artifact was changed. Root retains actual recovery replay and publication ownership.
