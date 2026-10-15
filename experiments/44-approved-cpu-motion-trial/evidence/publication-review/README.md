# Publication review and optimized-verifier correction

These archived files describe publication verification, not a new model run.
They leave the original 25 acquisition/run/review/resource copies unchanged.

1. `initial-review.json` is the exact independent first publication review. It
   accepted the real evidence/narrative but held publication for one P2 defect:
   optimized Python removed every assertion while the verifier still printed a
   success result. Its 32-path inventory hash identifies the original candidate;
   it is historical, not the current publication index.
2. `red-controls.json` records the original verifier against a private copy whose
   ledger invocation count was changed from 1 to 2, with stale hashes retained.
   Normal Python rejected it; `-O`, `-OO`, `PYTHONOPTIMIZE=1` and `=2` falsely
   exited 0 and printed receipt consistency. The actual original run was valid.
3. The current verifier has an explicit **non-assert** `sys.flags.optimize`
   rejection at the start of `main()`, before evidence reads. All original
   assertions and hash/privacy checks remain. `green-controls.json` records 20
   expected results: two valid normal passes, two normal bad-ledger rejections,
   and sixteen optimized rejections across valid/bad fixtures and CLI/imported
   `main()` entry points.
4. `verifier-before-fix.py.txt` retains the exact original verifier as inert text,
   SHA-256 `b64e923c060208558971db66f5334a721b43a2b8c38ba91a3c4d9c40babea955`. It is history, never a CI entry point. The
   current `verify_evidence.py` is the only experiment44 executable verifier.

The red/green receipt paths refer to private temporary fixture copies, which are
not published. The retained original source and recorded commands permit an
isolated offline reconstruction: copy the small public44 evidence to a new
private temporary sibling of a copied public41 `proposal.json`, install the old
source as that private copy's `verify_evidence.py`, and mutate only that copy's
ledger to count2 without rebinding hashes. Normal mode rejects; optimized old
mode demonstrates the false green. Never change the canonical published ledger,
reset authorization, run models or use the historical source as validation.
No model download or inference is needed to reproduce this verifier defect.

Current CI runs the corrected verifier and the separate45 numerical HOLD study
and controls. A green HOLD study means its evidence and rejection controls pass;
it does not admit normalized motion, anatomical/axis semantics, target playback,
or a product provider. Targeted rereview and hosted CI remain separate gates.
