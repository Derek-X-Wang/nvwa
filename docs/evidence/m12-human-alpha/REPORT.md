# Guided physical-human Alpha and Save feedback

## Actual human observation

The guided native trial used reviewed main `9502dd370b262761bf4f4f10f2418163c7574946` and its verified retained Studio source cohort. The human reported all three tasks normal: the complete nine-second sequence, one jaw-width edit with Undo/Redo, and Save with finding/reopening the Work.

The usability problem was confirmation. The human initially thought Save had failed because no feedback was noticeable, then reopened the file and confirmed it had saved. A fresh native screenshot showed `Document saved` only at the bottom of the animation panel. This supports a visibility problem, not a persistence failure.

Byte inspection of the saved Work confirms revision 2 → 5 and jaw width 0.42 → 1.0. Every other JSON field matches the prepared baseline. CLI validation returned `valid:true`, `asset_checked:true`, revision5. SHA-256 of the preserved saved Work: `eeb37048459d985adbf15a96fe103d45e31e9810bb99d8006d9cdbd668d7a2e9`. The original Desktop file and a separate private byte-identical snapshot are retained. Redacted observations are in [guided-native.json](guided-native.json).

## Scope and remaining human work

This was guided: the agent prepared the application and Work and supplied three steps. It does not establish unassisted capability discovery or full Alpha acceptance. Human Web exchange, Player clarity and error recovery remain NOT-RUN. Issue [#49](https://github.com/Derek-X-Wang/nvwa/issues/49) stays open. The visible Save confirmation fix is tracked separately in [#51](https://github.com/Derek-X-Wang/nvwa/issues/51).

The original #3 scaling blocker, #4 performance gaps, #12 real-model no-go and distribution/platform limits are unchanged. No real inference, signed release, extra hardware or formal performance measurement is implied.

## Human feedback after the first fix

The first revised native build displayed a visible saved message and destination. The human confirmed those were clear, then requested bottom-right placement instead of the upper-left banner. That observation used source `0cd7146bf487d15bc30f187508dab6ba786d5c3d` and native binary SHA-256 `7c53117d27e3c812168ee9ad889290ea582dba2afb57dd66c0052fc17fa1541c`. It is separate from any later acceptance of the bottom-right placement. The same focused fix, #51 / PR #52, incorporates this positioning request.
