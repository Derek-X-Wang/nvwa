# Bounded obstruction80 contract draft

Approval scope: one offline rejection-only run after independent review and root
freeze. This contract preserves v3/v4 REJECT, all27 logical points, all30 old
inequalities and all29 unmasked ties. No refit, candidate, side, nearest search,
global embedding, all581 reconstruction, remaining18 snapshots, product assets,
CI, dependency or threshold changes are authorized. #112 original FAIL, #3 blocked,
#4 gaps and #79/M2 scope remain unchanged.

## Two distinct claims

1. **Conditional source-space arithmetic**: distance from fixed garment source566
   (logical386 and568, original garment triangles1063 and1600, barycentric[0,1,0])
   to one concrete member of original body triangle16002, OBJquad8001/fan0,
   sources8373/8377/8330. Its named mathematical domain is the frozen83 garment
   audit triangles against original unmasked `g body` fan geometry. Root's freeze
   must authenticate its original policy meter metric and shared neutral source
   gauge. This can yield `CONDITIONAL_STRICT_OBSTRUCTION` or
   `UNKNOWN_BOUND_NOT_STRICT`. It is not admitted physical contact or a visible
   defect/cause/quality finding.
2. **Physical/causal stage**: neutral27-to-posed-notch and intended clearance
   semantics remain unproved. This implementation has no physical-admit path.
   Overall result remains `REFUSE_MISSING_PREREQUISITE` even with true arithmetic.
   Caller-supplied booleans cannot promote it. A later semantic evaluator would
   require a separately reviewed implementation and authority.

A missing technical prerequisite is `REFUSE_INVALID_OR_UNAVAILABLE_INPUT`, not
permission to calculate a useful-looking result. Root must include the technical
source/domain/common-metric/support review in the frozen input packet. The
prerequisite auditor's entire exact report and raw/input closure are inputs.
Existing posed source packets are reused; no new capture is required here.

## Exact reconstruction and bounded membership

`obstruction.py` is standalone Python standard library code. Decimal OBJ/MHCLO
tokens become exact rational numbers. Each binary32 operation uses rational
nearest rounding with ties-to-even, including signed helper normalization,
ordered complete helper sums, scale subtraction/division and offset product/add.
No approximate saved nearest point, decimal distance, host floating point
geometry, normal or tolerance is used as proof. The reconstructed binary32 cage
must equal every stored neutral cage value in the authenticated v4 receipt;
source566 must exactly equal the saved source point.

Only the preselected original body triangle is used. Its nondegeneracy is checked
by exact Gram determinant. A rational edge parameter is computed for its
8377->8330 edge and clamped to [0,1]; q uses barycentrics[0,1-t,t]. The certificate
consumer checks nonnegative barycentrics summing exactly to one. Thus q belongs
to the closed bounded triangle without a nearest-feature or side claim.

Exact squared rational distance is the core result. A readable distance upper
bound is ceil(sqrt(distance_squared)*10^12)/10^12, computed with integer isqrt and
an exact comparison. The checker verifies U^2 >= distance_squared and rejects the
current fixed support conditionally only when U < exact9999/10000000 meter.
Equality or upper-grid straddle stays UNKNOWN. No unsigned-distance PASS exists.

Input reconstruction error is zero **for these exact serialized source-space
binary32 positions**, with exact rational subsequent arithmetic. This is not zero
error relative to physical anatomy, ideal asset decimals, GPU results, posed
skinning, or a different fusing/reconstruction pipeline. Those claims remain
unadmitted. Unknown error models or a nonzero/unproved error field refuse.

## Fixed-position dependency scope

The permitted hypothetical correction changes only offsets of the unchanged30
mapping rows in frozen support SHA66dd2cc157b92bf5651e3c1e88c33d3ce72e6f6ec9fed8694a27984970b05053.
The base cage, scale inputs, mapping helpers/weights, every other row, topology,
recipe and source frame remain fixed. Garment source566 is outside position
support. Its helpers17012/16984/16980 and offsets therefore remain fixed. Body
triangle positions come directly from the unchanged cage. These facts prove
position invariance in this neutral source-space model for every permitted
choice of offsets. They do not prove feasibility for any broader correction.

Source566 belongs to normal accumulation support. Adjacent garment geometry and
normals can change. No visual-invariance claim follows from fixed p or body
positions. No posed skinning or global deformation theorem is claimed.

## Freeze, attempt and closure

`prepare.py` creates only a DRAFT. It authenticates immutable design, rereview,
original audit, v3/v4 receipts/freeze, support, source assets, ledger and prerequisite
report. Root supplies the supplemental closure list, confirms technical
admission, replaces review/authorization placeholders with exact hashes, freezes
all experiment files and chooses one new absolute output directory. Preparation
is not an attempt and does not call reconstruction/certificate/run.

The actual command is root-owned:

```sh
python3 -B experiments/87-bounded-obstruction80/obstruction.py \
  --freeze /absolute/root-frozen-policy.json \
  --freeze-sha256 EXACT_SHA256 \
  --output /absolute/new-exclusive-attempt
```

The runner authenticates the exact freeze and complete source inventory before
creating the output directory exclusively. Directory existence forbids reuse.
A fsynced atomic CONSUMED.json marker reserves the attempt before calculation;
a STARTED receipt is published atomically. Every receipt uses a unique temporary
file, fsync, replace and directory fsync. A failed replacement preserves the prior
valid receipt. Recoverable first/final publication failure produces an explicit
REFUSE_PERSISTENCE receipt with its error. A persistent error retains the consumed
marker and attempts a separate fallback/incomplete receipt; the exception and CLI
summary state consumed=true. A failed publication is never reported as successful.
There is no guarantee of publication on an unwritable or failed filesystem, but
the reserved directory still prevents replay. SIGKILL/power loss can prevent any
final receipt; the durable marker deliberately says CONSUMED_INCOMPLETE.

Before any reconstruction/certificate call, the runner checks the independently
reviewed prerequisite report's exact SHA7a77d4338960a946587ec3c50b68ee94d4f787d0777def7070dca1fe4c5bc8ec,
kind/base/status, all12 unique claim identities and exact status/gate combinations.
Its80 evidence file identities must appear in the consumed supplemental closure.
All five shoulder packet checks, current20raw/19gzip records, source/capsule pairs,
support/body/ledger identities and relevant frame flags are bound consistently.
The frozen exact report is trusted as independently reviewed evidence; this does
not rerun historical geometry. Missing/malformed/false/contradictory/omitted/stale
required evidence prevents reconstruction and any usable conditional certificate.
Both prepare and execution enforce this protocol; an arbitrary nonempty list is
insufficient. All consumed bytes and the old309 durable source files are hashed
before and after calculation. Closure failure removes the conditional result.

The numerical common Euclidean source coordinates and original code-contract
metre metric are VERIFIED by that report. Remaining missing prerequisites are
physical intended-contact clearance policy and neutral lead-to-visible-notch
causal/visibility correspondence. These are not described as missing numerical
coordinates or units.

Calculation runs in one owned local POSIX fork process. The supervisor joins with
the frozen deadline, sends SIGKILL if still alive, and waits at most1s for reaping.
The child independently installs a default-action POSIX real-time SIGALRM, which
also terminates it if its supervisor disappears. Frozen maximum is1200s. A hard
timeout or interrupted child yields refusal, no canonical conditional result,
and retains the parent's durable consumed marker and receipt. Supervisor SIGTERM
is converted to handled interruption while it owns the child; its finally block
kills any surviving child. No worker descendants, network, machine or dependency
are involved. This bounds the owned calculation; filesystem persistence, OS
scheduling/reaping and supervisor publication are not real-time guarantees.
Uninterruptible kernel I/O can delay process reaping; no software can promise
instant kernel termination in that state. The timeout control uses a1s blocked
synthetic worker and proves termination without real source data.

Exit2 is intentional for every real outcome because the physical stage refuses.

The receipt retains the complete original ledger, rows and ties; witness-only
arithmetic coverage is explicit. It does not relabel partial coverage as a full
baseline result. There is no signing, authoring, scored candidate or source write.

## Verification and execution boundary

Analytical tests invoke `certify`, which the actual entrypoint consumes. Controls
cover strict fixture, equality/straddle, invalid barycentrics, domain, units,
relative frame, unproved bounds, changed support, fixed dependencies, degeneracy,
exact f32 ties/subnormals, signed mapping, common rigid invariance, all27/30/29
coverage, stale inputs, freeze changes, attempt reuse and restored controls. The
membership guard is also removed from a compiled in-memory copy; invalid
membership then escapes, making the same rejection expectation red. Source bytes
remain unchanged. Synthetic attempt tests include full consumed-run report mutations with tiny
synthetic evidence and substituted immutable source reconstruction. They exercise
the real certificate, admission, process lifecycle and publication seams. Their
valid restored case remains conditional-only. They do not consume a real attempt.
First/final atomic-replace failures, marker failure, interrupted child/supervisor,
actual blocked-child timeout and replay controls run in normal and optimized
Python. The original15 tests remain intact.

Development authenticated and reconstructed real source identities to check
implementation prerequisites, as authorized. It did not call `certify` on real
data or invoke the actual entrypoint. The single actual calculation awaits root
review/freeze/run. Tests, source reconstruction, arithmetic, physical admission,
visibility, GPU behavior and product quality are separate evidence categories.

## Review rework v2

R2-1: bind exact reviewed schema and complete prerequisite closure before arithmetic;
separate verified technical coordinates/units from unknown physical semantics.
R2-2: durable consumed marker, atomic replacement, truthful fallback and CLI state;
recoverable publication failures are explicit refusal outcomes.
R2-3: owned-process supervisor and independent POSIX child alarm enforce the hard
calculation ceiling. All process/source/invocation behavior is in these same four
reviewed files. No external timeout helper or unreviewed command is required.
