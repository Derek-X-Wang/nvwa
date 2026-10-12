# Input scale evidence checks

This small Python 3 standard-library checker compares complete saved Works and
validates one explicit browser geometry relation. It does not run a browser or
measure pointer alignment.

The Work commands use the accepted `SceneDocument` shape: `schema_version`,
`revision`, `profile`, `character`, and `timeline`. `work-edit` requires the
only changed fields to be the selected `character.parameters` value and a
strictly increasing revision. `work-layout --action layout|focus` requires the
whole Work, including revision, to stay equal. `work-undo` checks the edit and
then requires all baseline content to return while revision advances again.

The geometry command takes one JSON record with these fields:

```json
{
  "observation_source": "runtime_dom",
  "css_size": {"width": 1280, "height": 720},
  "client_rect": {"x": 0, "y": 0, "width": 1280, "height": 720},
  "physical_canvas": {"width": 2560, "height": 1440},
  "device_pixel_ratio": 2,
  "logical_relation": "physical_canvas = round(client_rect_css_size * device_pixel_ratio)",
  "transition_claims": []
}
```

The checker requires finite positive sizes and DPR, finite rectangle position,
CSS size equal to the client rectangle, integer physical canvas dimensions,
and exact agreement with the stated rounded CSS-by-DPR relation. A transition
claim must include non-empty `observed_events`; each event needs `event_name`,
`observed: true`, and a source. A missing field is reported as
`PARTIAL / NOT-RUN`. Screenshot or image sources are rejected as runtime event
evidence.

Passing geometry means only that the supplied runtime DOM measurements agree
with the declared relation. The checker never treats a canvas ratio or a
screenshot as proof of pointer alignment, actual DPR change, IME behavior, or
actual tab hide/show. Transition event records are checked for explicitness,
but their meaning is not validated.

The checker accepts standalone paths and does not impose a shared evidence
schema outside this experiment:

```sh
python3 experiments/21-input-scale-evidence-checks/check_evidence.py work-edit BASE.json EDITED.json --parameter jaw_width
python3 experiments/21-input-scale-evidence-checks/check_evidence.py work-layout BEFORE.json AFTER.json --action focus
python3 experiments/21-input-scale-evidence-checks/check_evidence.py work-undo BASE.json EDITED.json UNDONE.json --parameter jaw_width
python3 experiments/21-input-scale-evidence-checks/check_evidence.py geometry GEOMETRY.json
```

Tiny fixtures under `.work/input-scale/evidence-checks/fixtures/` are unit-only
checker inputs. They are not browser observations or runtime acceptance
evidence. Actual browser execution and its evidence remain with the integration
owner.

## Integrated actual results

Root subsequently ran actual Chrome tab/zoom and physical acceptance. See
[the attributed acceptance packet](../../docs/evidence/input-scale/ACCEPTANCE.md)
for results, exact raw copies, offline commands, review fixes and explicit limits.
Worker-only NOT-RUN statements above describe the preparation stage.
