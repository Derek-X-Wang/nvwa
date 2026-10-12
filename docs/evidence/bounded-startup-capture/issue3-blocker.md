# Issue3 bounded exit, 2026-10-12

Current Codex Desktop, local Mac, selected Codex In-app Browser ID2. Root refreshed the exposed viewport documentation once; the exact text is [iab-viewport-api.txt](iab-viewport-api.txt). `ViewportSize` has only height and width. No supported DPR override is advertised. No viewport or page was changed during this capability check.

NOT-RUN — original IAB DPR-emulation trigger, cause and upstream boundary. Physical display migration also remains unavailable. Ordinary Chrome zoom and fixed-CSS controls accepted in merged PR33 remain passing controls, not a fix for the original failure. No speculative sizing workaround was implemented. Original issue3 criteria remain unchecked and retained.

Decision: record the reproduction-capability blocker, keep #3 OPEN/needs-info, proceed independently with #4 HTTP-cache startup boundary and #5 screenshot-export diagnosis. Resume #3 only when a supported original DPR-emulation control/trace or an actual display-scale transition becomes available. Do not repeat unchanged ordinary controls.

[Issue3](https://github.com/Derek-X-Wang/nvwa/issues/3); [merged prior packet](https://github.com/Derek-X-Wang/nvwa/blob/6b5cf8068fe5f859f82a1934bfedc8b224d49e20/docs/evidence/bounded-scale-ime/ACCEPTANCE.md).
