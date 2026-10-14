# Native CUA provenance and replay

All UI calls below ran through `mcp__cua_repl.js` in this worker. Native apps, not shell UI scripting or CDP, provided the interaction. The transcript is the complete tool-call provenance; this file records the material calls and their observable outcomes without copying unrelated browser inventory. The filenames below identify the actual retained screenshots and saved bytes.

## Native Studio

The exact retained release executable was copied privately, then launched from the shell with `RUST_LOG=info`, `NVWA_ASSET_ROOT=$PWD/.work/m12-gui/Nvwa.app/Contents/Resources/assets`, `--benchmark --work $PWD/.work/m12-gui/agent-nine-second.nvwa.json --capture $PWD/docs/evidence/m12-agent-loop/native-initial-render.png`. Its PID/session and cleanup are in `lifecycle.json`.

```js
app = await cua.getApp('/Users/derekxwang/.codex/worktrees/m11-ui-integration/nvwa/.work/m12-gui/Nvwa.app');
await app.getScreenshot(); // native-loaded.png: real character, revision 2, jaw .42, smile .20
await app.click([300,622]); // Pause; reobserve because button widths change.
await app.getAXStateAndScreenshot();
await app.click([749,622]);
await app.pressKey('BackSpace');
await app.typeText('4.5');
await app.pressKey('Return');
await app.click([943,740]);
await app.getAXState();
await app.getScreenshot(); // native-wave-paused.png: 4.5 seconds, agent-wave, Play
await app.click([1078,203]); // One jaw slider pointer edit, .42 -> .71
await app.click([943,740]);
await app.getAXState();
await app.getScreenshot(); // native-jaw-edited.png: revision 3
await app.click([564,77]); // Save current private path
await app.getAXState();
// Filesystem copy of the actual saved bytes -> native-edited.nvwa.json
await app.click([95,77]); // One Undo
await app.getAXState();
await app.getScreenshot(); // native-undone.png: revision 4, jaw .42
await app.click([564,77]); // Save
await app.getAXState();
// Filesystem copy -> native-undone.nvwa.json
await app.click([514,77]); // Open same saved private path
await app.getAXState();
await app.getScreenshot(); // native-reloaded.png: revision 4 restored and playback resumes
```

Before this accepted cycle, typing numeric `.7` into the jaw field generated three revisions (2 -> 5). Its actual full save is retained as `native-typing-attempt-rev5.nvwa.json`. The exact original bytes were recopied to the private path, then the actual GUI Open reloaded revision 2. The successful single-pointer cycle above began from that fresh original. Numeric typing is not reported as one atomic shape edit. A transport click also initially missed after Pause changed control widths; it was repeated using a fresh screenshot. Only visibly correct 4.5-second captures count.

## Native Player

Launch the same private executable sequentially with `--player --benchmark --work $PWD/.work/m12-gui/agent-player.nvwa.json --capture $PWD/docs/evidence/m12-agent-loop/native-player-render.png`. The Player input is a separate byte-identical original Work copy, revision 2.

```js
app = await cua.getApp('/Users/derekxwang/.codex/worktrees/m11-ui-integration/nvwa/.work/m12-gui/Nvwa.app');
await app.getScreenshot(); // native-player-loaded.png: authored wave plays
await app.click([444,688]); // Pause, then inspect current controls.
await app.getAXStateAndScreenshot();
await app.click([650,688]);
await app.pressKey('BackSpace');
await app.typeText('2');
await app.pressKey('Return');
await app.click([780,735]);
await app.getAXState();
await app.getScreenshot(); // native-player-held-before.png: idle, Play, 2.0
await app.click([639,390]); // Actual chest hit
await app.getAXState();
await app.getScreenshot(); // native-player-interaction.png: overhead wave, cursor-held label, 2.0
await app.getAXState();
await app.getScreenshot(); // native-player-restored.png: idle, Play, 2.0
```

## Web route and Studio

`await cua.createBrowserTab('iab', URL, {visible:true})` returned **Browser is not available: iab**. The supported fallback was native Chrome through the same CUA API. `cua.getApp('com.google.Chrome')` verified an existing New Tab. Clicking its observed New Tab button AX58 created the sole owned tab (initial AX120). `setValue` on the observed address field AX9 plus Return loaded `http://127.0.0.1:9201/?work=works/agent-nine-second.nvwa.json`. The browser translation bubble was closed through its observed AX Close button. No new browser permission prompt occurred.

The private `python3 -m http.server 9201 --bind 127.0.0.1 --directory .work/m12-gui/web` served byte-identical copies. Port-registry entry 9201 was read and the port checked free before starting. `web-http.log` records actual requests.

The native Chrome window was zoomed through its exposed `zoom the window` secondary action to expose transport controls. Its raw CUA screenshot is 5120×2100, with the visible 2560×1050 window in the upper-left and white padding elsewhere. Pointer coordinates required the full screenshot scale: twice the visible content coordinates. A first Save coordinate landed in the address field. After correcting the scale, the first canvas click restored page focus and was dropped; subsequent clicks worked. No browser zoom or DPR emulation was applied. Complete raw captures remain retained; `*-crop.png` files remove only the white padding at the original content scale.

```js
// After the observed window zoom and page focus:
await chrome.click([1130,200]); // Studio Save
await chrome.getAXState(); // Actual download shown: agent-nine-second.nvwa.json
// Move only the newly created owned export to web-initial-saved.nvwa.json.
// It is byte-identical to the original e333... input.
await chrome.click([1536,1778]);
await chrome.pressKey('BackSpace');
await chrome.typeText('4.5');
await chrome.pressKey('Return');
await chrome.click([2800,1900]);
await chrome.getAXState();
await chrome.getScreenshot(); // web-wave-paused.png: 4.5, Play, agent-wave
await chrome.click([4716,452]); // One jaw pointer edit .42 -> .71
await chrome.click([2800,1900]);
await chrome.getAXState();
await chrome.getScreenshot(); // web-jaw-edited.png: revision 3
await chrome.click([1130,200]); // Save -> actual downloaded web-edited.nvwa.json
await chrome.getAXState();
// Dismiss download bubble through its observed checkbox, then:
await chrome.click([190,200]); // Undo
await chrome.getAXState();
await chrome.getScreenshot(); // web-undone.png: revision 4, jaw .42
await chrome.click([1130,200]); // Save -> web-undone.nvwa.json
await chrome.getAXState();
await chrome.pressKey('Escape');
await chrome.click([1028,200]); // Studio Open -> actual native file chooser
await chrome.getAXState();
await chrome.pressKey('super+shift+g');
await chrome.getAXState();
await chrome.setValue(76,'/Users/derekxwang/.codex/worktrees/m11-ui-integration/nvwa/docs/evidence/m12-agent-loop/web-undone.nvwa.json');
await chrome.pressKey('Return');
await chrome.getAXState(); // Exact filename plus revision-4 JSON preview
await chrome.click(154); // Observed chooser Open
await chrome.getAXState();
await chrome.getScreenshot(); // web-reloaded.png: actual restored document
await chrome.click([1130,200]); // Save after reload -> web-reloaded-saved.nvwa.json
await chrome.getAXState();
```

One extra initial export from establishing focus is retained as `web-initial-extra.nvwa.json`, also byte-identical to input. All new task-owned exports were moved out of Downloads by exact filename/content checks. No unrelated download was opened, moved, or deleted. The actual downloaded full Works, not screenshot text, supply the complete-document comparisons.

## Web Player and cleanup

The same owned tab was navigated through its current address field AX82 to `http://127.0.0.1:9201/?player=1&work=works/agent-nine-second.nvwa.json`.

```js
await chrome.getScreenshot(); // web-player-loaded.png: real sequence and character
await chrome.click([824,1912]);
await chrome.pressKey('BackSpace');
await chrome.typeText('2');
await chrome.pressKey('Return');
await chrome.click([2800,2000]);
await chrome.getAXState();
await chrome.getScreenshot(); // web-player-held-before.png: idle, Play, 2.0
await chrome.click([2560,840]); // Actual head hit
await chrome.getAXState();
await chrome.getScreenshot(); // web-player-interaction.png: moving wave, cursor-held label, 2.0
await chrome.getAXState();
await chrome.getScreenshot(); // web-player-restored.png: idle, Play, 2.0
await chrome.performSecondaryAction(101,'zoom the window'); // Restore prior window zoom
await chrome.getAXState();
await chrome.click(98); // Only the observed owned tab Close
await chrome.getAXState(); // Prior New Tab remains
```

Screenshots were saved from `await app.getScreenshot()` or `await chrome.getScreenshot({emit:false})` using `node:fs/promises.writeFile` inside CUA. File writes preserve the returned bytes; they do not generate scene imagery. The 20 raw CUA captures are JPEG-encoded despite their legacy `.png` filenames. The other 13 image files are actual PNG: two renderer captures and 11 convenience crops. `screenshot-formats.json` records the file-signature inventory. Raw bytes, original filenames, and call references remain unchanged; no raw capture was transcoded. Native processes were stopped/reaped before Web started. The owned static server was stopped/reaped, port 9201 verified free, and the exclusive GPU/UI token released before the final CPU comparisons and report.
