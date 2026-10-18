# Actual result — CPU rejection, quality HOLD

The approved source has 4,194,304 texels; 2,201,816 have alpha8>=128. At generated
mip 1 (1024²), exact preservation would require 550,454 passing texels. The
closest choice in the frozen finite family is scale 128/128, with 551,642 passing
texels. The next histogram cutoff gives 548,656; the target lies in this gap.
All 255 nonzero scales plus scale 0 were evaluated, including exact tie rules.

The best error is 1,188 / 1,048,576 = **0.001132965087890625**, or
**0.1132965087890625 percentage point**. It exceeds the frozen 0.001
(0.1 percentage point) bound. Therefore the whole candidate is **REJECTED**.
The 0.001 bound is an engineering coverage condition, not artistic acceptance.
Levels 2–5 pass that numerical condition; levels 6–11 have recorded residuals
and no preservation claim. `alpha-reference.json` retains all 256-bin raw
histograms, scales, exact errors and signed differences. No failure is hidden.

Ordinary and optimized Python runs both exit 1 with `CPU_REJECTED`/failed level 1
and produce identical 38,106-byte reports (SHA-256 in `validation.json`). Eight
hand/negative/evidence controls pass under both modes. Controls include all
five PNG filters, raw-sum versus rounded-feedback distinction, nontrivial
scale selection, invalid input, and seven altered-evidence/policy variants.
An independent test enumerates rounded output membership from each retained
histogram; it does not call the implementation's scale-selection function.
This is same-author executable cross-checking, not an independent human/agent
review or a replay of GPU behavior.

This experiment stopped here. RGB filtering, mip-image generation/upload,
actual image/sampler binding exports, Rust compilation/tests, native/Web apps,
screenshots, GPU ownership/readback and performance are **NOT-RUN**. No source,
geometry, weights, UV, material, Work or production controller was changed.
Unfinished runtime scaffolding is preserved privately with hashes and is not
published as runnable verified code. Preliminary source/verification helpers are kept
there as unverified development work; they do not become rendering evidence.

This rejection applies only to this specified finite global correction policy
and frozen condition. It neither proves every mip method ineffective nor
establishes an asset-only cause. Whole-texture alpha coverage cannot prove
local hairline improvement.65's existing paired images remain separate HOLD
evidence; 68's actual baseline, if later available, cannot be relabeled a 69
candidate render. A later replacement review needs the bounded provenance
and rendering controls in `REPLACEMENT-REQUIREMENTS.md`.
