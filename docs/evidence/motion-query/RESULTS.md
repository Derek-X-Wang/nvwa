# B1 short dance: motion query and screenshot comparison

This report records a local experiment on an unpublished build with the
knee weight-shift pilot enabled. The production motion evaluator uses the
existing rehearsal poses. The clearance values and timing below apply to
the pilot build.

On 2026-11-08, two independent GPT-6.1 Sol sessions at high effort started
from identical bytes of a 10-second B1 rehearsal with arm, knee and arm
phrases. Both aimed for at least 0.400 s in the left foot's near-floor band
before the 6 s handoff. Character, stage and all timeline spans had to stay
the same. One session observed motion through the headless query prototype.
The other saw only time-labeled images from the actual Web preview.

| Observed in one run per route | Numeric | Screenshots |
| --- | ---: | ---: |
| Total input and output tokens, including cached input | 288,824 | 663,641 |
| Uncached input tokens | 21,798 | 27,063 |
| Agent tool requests, including waits | 8 | 19 |
| Application CLI calls made by the Agent | 3 | 3 |
| Time spent in the two observation commands | 29.3 s | 226.2 s |
| Knee phrase playback speed after edit | 1.55× | 1.65× |
| Sampled left foot near-floor lead before handoff | 0.400 s | 0.525 s |

The original lead was 0.325 s. The final numerical check used the same
25 ms sample grid and near-floor band for both Works. Both edits changed only
the knee phrase speed and advanced the revision. Neither report flagged a
below-floor interval or foot-clearance jump. The screenshot Agent saw the
earlier settling in the rendered frames and reported that the pictures could
not establish the 0.5 cm threshold. The after-the-fact numerical check verified
the result. The screenshot path produced 14 frames and included two failed
auxiliary shell commands.

The numeric route used 56.5% fewer total tokens and 19.5% fewer uncached input
tokens in this matched case. These are workflow observations for one pair of
Agent runs. They include prompt, caching, tool results, waiting and retries
where applicable. They do not isolate image token cost or establish a general
savings rate. The build and independent scoring are outside the creator
measurements. Neither run establishes short dance quality or release approval.

Use `nvwa-cli motion-query` for the same local observe, edit and recheck loop.
Start with its summary. Review rhythm, pose and apparent contact at normal
speed after the numerical check. Sampled body-foot geometry does not measure
force, shoe clearance or continuous behavior between observations.

The follow-up used an unpublished build of the formal CLI with the same
local weight-shift pilot enabled. In that build, the 1.55× Work returned
the prototype's summary byte-for-byte. A 1.60× revision
increased the near-floor lead to 0.475 s on the same 25 ms grid. A separate
50 ms scan covered the entire 10 s and compared both clip starts at 3.25 and
6 s. It reported no below-floor intervals or clearance jumps. The final
candidate played through 10 s in the Web Player, with a sampled visual check
around the handoffs. This supports the local timing adjustment and the
observation workflow. Full choreography and release acceptance are separate.

## Recompute the reported metrics

The commands show the inputs used to compute the comparison. For a new
experiment, supply the rollout for the same thread as the worker's event
file, its application call log, and a `--batch-receipt` for each recorded
render batch.

```sh
python3.12 -B scripts/motion-review-report.py run events.jsonl rollout.jsonl calls.jsonl > numeric.json
python3.12 -B scripts/motion-review-report.py run screenshot-events.jsonl screenshot-rollout.jsonl screenshot-calls.jsonl \
  --batch-receipt before/receipt.json --batch-receipt after/receipt.json > screenshots.json
python3.12 -B scripts/motion-review-report.py compare numeric.json screenshots.json
python3.12 -B scripts/motion-review-report.py playback capture-receipt.json actual.webm --player-end-s 10
```

Each event file belongs beside its worker's `meta.json`. A run report
counts requests from the rollout, execution items from worker events and
application calls from the call log. It also lists cache use, render work
and observation time. The comparison requires independent threads with
matching model and effort. Use the Work and query receipts separately to
verify that the edits meet the same acceptance criteria.

The playback report verifies the recording hash and reads its frame count
and media duration with `ffprobe`. Supply the endpoint only when it was
actually observed in the Player. The report keeps that observation, mean
recording frame rate and paused diagnostic status separate.
