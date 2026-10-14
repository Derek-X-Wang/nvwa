# Independent R2 classification-family review

Verdict: **NO-GO for notice-coverage publication at d12be0048b0350c1bbf519bef908a1dffdf9a039.** This supersedes stage-C acceptance of the notice classification and coverage statements. It does not invalidate the separate experiment-35 observations or PR42 CI evidence. No verdict is given on the moving v3 repair.

Reviewed input: the reviewer's immutable stage-B reproduced pack, manifest SHA256 `ab92b4816b18191e0d24d063e43a9e183cd3204114a4321da5d478455a403bf2`, and collector/checker/cohort source read from the exact d12 commit into `old-tools/`. No current experiment-36 source was used for this verdict.

## P2 — Discovery filenames are promoted to license-text coverage without checking content role

Affected source invariant: `old-tools/collect.py:51-52` discovers names including COPYING, AUTHORS, COPYRIGHT, NOTICE and ATTRIBUTION, and line 84 promotes all locally copied matches to `license_text_candidate_files`. `old-tools/cohort.py:98-105` repeats that promotion while checking semantic consistency. The external frozen anchor proves the same bytes and metadata were preserved; it does not prove this original classification was correct.

Four actual Rust files from objc2-foundation 0.2.2 and 0.3.2 contain NSCopying bindings/tests and no license terms. They are the only local files counted as license-text candidates for those two packages. The additional 0.3.2 upstream LICENSE.md is a licensing explanation that was already correctly marked notice-only. These two packages must therefore be included among those without a substantive license-text candidate.

The family audit covered all 323 package records, all 694 retained package notice references, and 200 unique byte hashes. Of the 688 references currently designated license-text candidates, **27 references across 24 packages are false positives**: four Rust source files and 23 declaration, author, copyright, attribution, or application-notice-only files. The complete exact path/hash/source inventory is `false-positive-candidates.json`; `inventory.json` covers all 694 references. The corrected no-substantive-text-candidate count for this unchanged corpus is **23 rather than 21**. Only the two foundation versions are newly missing; the other 22 affected packages have separate terms-bearing candidates. This count is not a claim that the other 300 packages have complete applicable license coverage.

Concrete content counterexamples beyond Rust code:

- typenum 1.20.1 LICENSE contains only the 17-byte declaration `MIT OR Apache-2.0`.
- guillotiere 0.7.0 and shlex 2.0.1 LICENSE-APACHE contain short application notices and links, not Apache's full terms.
- aho-corasick, byteorder, memchr and termcolor COPYING contain only a declaration of the MIT/Unlicense choice.
- craft-ui ATTRIBUTION.md and NOTICE, AUTHORS/COPYRIGHT records, parking LICENSE-THIRD-PARTY, petgraph documentation-image LICENSE.md and winit documentation attribution preserve relevant information but do not themselves supply substantive license terms.

These useful notices must remain retained and separately classified. Excluding all ATTRIBUTION or short files would introduce false negatives: glam ATTRIBUTION.md contains actual MIT terms, adler2 LICENSE-0BSD is a short substantive grant, and atomic-waker/futures-lite LICENSE-THIRD-PARTY mix a short Apache application notice with actual MIT terms. The mixed files do not thereby establish complete Apache or package-level coverage. epaint font subasset terms and their scope must also remain distinct from package metadata.

## Independent evidence

- `audit.py` and `summary.json`: content-role triage over every package reference, with all negative and mixed/short cases read; all 670 locally available original source files were rehashed against the immutable copied bytes. The 24 public supplement references were checked against retained immutable hashes without fetching or reading moving publication files.
- `old-checker-false-green.json`: the actual frozen v2 checker accepts the actual frozen packet as VERIFIED-INTEGRITY/PARTIAL-COVERAGE and reports 21 missing packages.
- `classification-regression.py` / `classification-regression-red.json`: four intended red controls exercise actual copying.rs discovery, actual declaration-only typenum classification, the actual checker status, and its missing count. These are concrete old-source failures, not simulated metadata mutants. A discovery implementation may continue retaining source matches if it classifies them separately; the required invariant is that they never supply license-text coverage.
- `classification-regression-initial-harness-error.json` preserves the first run. One fixture assertion incorrectly expected a trailing newline in typenum's file; the exact-byte assertion was corrected, then all four tests failed at their intended classification boundaries. No reviewed source or fixture bytes were changed.
- `postrun-reconciliation.json`: all 1,039 indexed files, their sizes and hashes, and the exact 1,040-file inventory including manifest remain unchanged. Four short/mixed positive examples retain substantive grants. Old tool source hashes are recorded there.

The content-pattern pass is triage, not a universal license parser or a completeness proof. The 661 terms-bearing references contain substantive terms, but this review does not certify that every license is entire, applies to the whole package, covers each expression branch, or satisfies a release obligation. README explanations and license-choice declarations cannot close a missing-text gap by naming a license or linking to it.

## Required repair/re-review family

1. Separate discovery, retained notice role, substantive terms, and package/asset applicability. Preserve original bytes, identities and expressions, including AND/OR/WITH, legacy slash and first-party null; do not select licensing alternatives.
2. Cover the full 27-reference family, with actual Rust, declaration-only LICENSE, application-notice-only LICENSE-APACHE, COPYRIGHT/AUTHORS/NOTICE/ATTRIBUTION, and mixed/short genuine-license counterexamples. A single `.rs` exclusion does not fix this family.
3. Bind revised classification to the actual reviewed bytes and source identity. Test that the checker rejects reverting roles, inflating text-candidate coverage, erasing required gaps, or changing classification and associated counts self-consistently. Merely pinning a newly generated manifest is not independent content validation.
4. Preserve the original packet/anchor and failed evidence as historical inputs; explicitly reconcile the new classifications, no-text counts, package/asset/font inventories and report/PR claims. Do not rewrite the historical 21 as though the earlier run produced 23.
5. Keep candidate-text presence separate from complete license/applicability coverage. Known partial or third-party-only texts cannot establish completeness. Root-owner license, signing, shipped membership and distribution/legal approval remain unresolved.

Restored-green v3 controls: **NOT-RUN**, pending a stable owner handoff. No new retrieval, browser, rendering, actual download, build, Git mutation or publication was performed. Only this private review directory was written. Finite CPU work has ended; reviewer is quiescent, with no helper process left running. Runtime instance disposal is not claimed.
