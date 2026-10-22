# #112: bounded offline garment witness attribution

## Outcome

Use existing retained frames to explain why the Linux pilot produced
`posed_over_fitted_rest_area = 22.005667838827247` while the unchanged garment
controls expect `22.0056357384` at six decimal places. Identify the responsible
frame components and distinguish direct evidence from an unproven producer cause.
This experiment does not fix or replace the original controls.

## Frozen execution

- Source: `baa0b6bbda0d9709f0fab37c9e7d962fd8d926c1`.
- Linux run: [39798844545](https://github.com/Derek-X-Wang/nvwa/actions/runs/39798844545).
- Executed pilot harness: `38a45bc4223d18eac98be65631ed279f5156fe32`.
- Starting analysis checkout: `44a9d8810c1529ee020a0f8a6873c5ede72c0e50`.
- Linux compressed input frame SHA256:
  `cf74fade5f05e05da4166a5e1607709ca2377b5752a5e4259dc072afd0998825`.

The original normal control was reproduced locally without editing it: 18 tests,
two identical scalar assertion failures. The original Linux optimized control is
still NOT-RUN. An offline replay or component-swap experiment cannot fill that gap.

## Method and acceptance

1. Minimize the scalar comparison to the actual retained target triangle.
2. Bind each comparison to frame hashes, requested shape/time/clip, source assets
   and available provenance. Do not label a local historical frame as a same-SHA
   Mac CI frame without proof.
3. Compare posed and fitted-rest coordinates, triangle/source identities, weights
   and bone matrices. Change one component group at a time in offline probes.
4. Retain measured numerator/denominator contributions and exact reproduction
   commands. A source arithmetic or iteration-order hypothesis requires a direct
   counterfactual, not only an OS/CPU label.
5. Add bounded analysis controls for invalid inputs and attribution behavior.
   Preserve the original assertion, mutation detection and failed CI report.
6. Obtain independent review of scripts, evidence and conclusion before reporting
   any migration recommendation.

## No-touch and resource boundaries

No product, asset, dependency, lockfile, existing test, historical evidence,
workflow or gate changes. No new download, model run, Rust build, GUI/GPU job,
VM, external compute or CI rerun. Local stdlib Python frame analysis only.

The numeric worker owns new analysis scripts/tests and their derived receipts;
the provenance helper writes an independent private audit. The orchestrator owns
this contract, final documentation, integration and GitHub issue publication.
Original producer files remain read-only. No migration or macOS-frequency change
is authorized here. #3 remains blocked; #4 retains its existing gaps.
