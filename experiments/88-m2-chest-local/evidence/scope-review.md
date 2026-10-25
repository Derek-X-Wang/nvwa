# Stage A independent scope review

Verdict: PASS FOR IMPLEMENTATION ONLY. Zero blocking proposal findings. Real constructor and candidate evaluation remain NOT-RUN and unreleased.

Reviewed proposal SHA256 `26a88b0a04fdf7248612a592def42b63086192d59a3504de872a187742894aeb`; input receipt SHA256 `02dc61cc3ea3c9ced7fc917f6f6d0c3bbe151e71372c76e0a3855c2752b602db`. All19 repository input hashes independently read back and matched. Review began only after independent old87/feasibility first pass was recorded.

The proposal fixes L=0.5 and the20mm x/y factors before candidate values or motion predictions. Its lambda lies in[0,0.5]; restricting writes to the42 original arm rows inside the immutable96 domain preserves the54 torso rows. The scalar taper goes to zero with zero derivative at outer x=.305/y1.28/1.40; the proposal correctly does not claim continuity across the arm/torso seam or finite-mesh C1/shading quality. No z boundary is introduced. This is adequate to test, not a mathematical guarantee of visual benefit.

In-place original-slot retention, first original zero slot for chest, unchanged remaining zero slot bits, zero-field byte identity, direct float32 serialization/readback, no renormalization, no pruning and unchanged2e-6/1% rejection limits satisfy the authorized operation. Implementation must enforce these conditions at the constructor-called boundary and reject rather than repair bad records. Root should freeze exact code hashes only after independent guard/control review.

The independent new-vs-old50 byte comparison is correctly separated from the untouched old50 exact-byte gate. The fixed39 edge IDs,259 incident face IDs, seven held keys and90-pose preservation requirements stay fixed. Two named edge reductions plus smaller39-edge maximum are necessary diagnostics, not visual acceptance. Changed surface partition membership is explicitly noncomparable; old failures remain. Offline failure stops before CLI/Web, actual visible gain and no new band defect are required, and all unavailable evidence remains NOT-RUN/HOLD.

The fixed limits of30-second constructor,240-second offline phase,30-second synthetic control modes, one candidate and no parameter adjustment are explicit. No runtime/source policy, region, framework or verification threshold expansion appears in the proposal.

Residual risks: chest movement can worsen edges or create new local flattening; support retention is algebraic until real float32 and readback guards run; normal/shading and between-key motion remain unproved. These are correctly retained acceptance risks, not reasons to tune after freeze.

VERIFIED — proposal scope and all19 input pins. NOT-RUN — implementation, synthetic controls, candidate construction, offline result, CLI/Web, deformed normals and visual benefit.
