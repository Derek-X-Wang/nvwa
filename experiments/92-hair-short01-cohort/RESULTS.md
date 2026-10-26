# Short01 body and motion cohort (92)

**PARTIAL: numerical checks pass; complete plus-case hairline and crown are not visible.** This result does not release a formal asset identity or CLI persistence.

The existing compiled experiment 91 ran seven pinned Works at source 0 and 2. The torso/jaw recipes change both parameters together to -1, 0 or +1; head-width +1 is separate. This is not the full 3x3 parameter product. All 14 A/B/A triples (42 exact raw records) passed source reconstruction, full-envelope comparison and exact restoration. The single numerical run took 65.812 seconds. Actual capture took 2208.436 seconds, within 45 minutes. Normal and optimized controls each passed 7/7, with independent code and intended-failure review.

Independent review inspected all 28 held originals and 8 motion stills. Default, minus and head-width cases show no obvious new visible fit defect; forehead and both eyes remain clear. Both plus recipes clip the highest central hairline and crown. Their exposed regions show no obvious defect, but complete coverage is NOT-OBSERVED. The original camera, images and this PARTIAL result remain unchanged.

Four motion witnesses each retain 16 playing samples at 0-3.75 seconds in 0.25-second steps, with 53 named bones per sample. Changing matrices were observed for 18 arms joints and 3 knee joints, not all 53. Knee A/B's first motion stills show different instants (0.50/0.25 seconds). This is not all-frame video, contact, GPU depth or performance proof.

Later review of experiment 93 found that the historical 91/92 checker does not reject A1 reused as A2. Historical source, assertions and receipts stay unchanged. A separate audit of these 42 actual raw captures verified 42 distinct request IDs, each correlated with its frame and transfer hash. EVIDENCE.json pins that audit. Experiment 93 adds its own rejection guard; the audit does not turn cropped images into a visual pass.

EVIDENCE.json pins exact receipts, original example JPEGs and the local evidence root. Reproduction requires those original raw files:

```sh
python3 -B experiments/92-hair-short01-cohort/cohort.py <evidence-root>/web/COHORT.json
python3 -B -m unittest discover -s experiments/92-hair-short01-cohort -p 'test_*.py' -v
python3 -B -O -m unittest discover -s experiments/92-hair-short01-cohort -p 'test_*.py' -v
```

These local checks used Python 3.9.5; they are not complete portable CI. No new Rust build, acquisition, inference or CI occurred. Routine native UI remains deferred. M2/#80 HOLD, #112 original failure, #3 blocked and #4 gaps remain. The 46 owned downloads were moved into local evidence; the tab, viewport override and port 9205 server were released.
