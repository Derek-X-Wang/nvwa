// Replay recipe inside the documented native cua_repl session, after prepare.py
// and an explicitly scheduled task-owned renderer have been launched.
// These coordinates apply to the observed 1280x784 native window capture only.
// Reinspect the current screenshot before using them on another machine/window.
var app = await cua.getApp('/Users/derekxwang/.codex/worktrees/m11-ui-integration/nvwa/.work/m12-retarget/Nvwa-retarget.app');
var fs = await import('node:fs/promises');
var evidenceRoot = '/Users/derekxwang/.codex/worktrees/m11-ui-integration/nvwa/experiments/40-retarget-visual';
// Observe actual playing motion before Pause. Save two native screenshots with
// fresh AX observations between them; no synthetic rendering or fixed picture.
await app.getScreenshot();
await app.getAXState();
await app.getScreenshot();
await app.click([445, 688]); // Pause; verify the button now says Play.
await app.getAXStateAndScreenshot();
// Repeat for each exact time: 0, .123, .5, 1.25, 2.345, 3.
// Clicking this numeric DragValue selects its contents. BackSpace clears it.
await app.click([648, 688]);
await app.pressKey('BackSpace');
await app.typeText('0.5');
await app.pressKey('Return');
await app.click([780, 735]); // Move pointer away from the value and scene.
await app.getAXState();
await fs.writeFile(evidenceRoot + '/screens/corrected-wave-0.500.png', await app.getScreenshot());
// Read the screenshot: Ready, Active: wave, Play, and 0.50 must be visible.
