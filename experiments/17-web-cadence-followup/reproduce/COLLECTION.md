> Post-run path-redacted collection plan. The exact root collector is retained in ../evidence/public/root-collector.js. This copy was not measured. Replace PERF_WORKTREE and PRIMARY placeholders with approved local paths before any future run.

# Executor collection commands

This is a predeclared command plan, not proof of execution. No screenshot or runtime result exists yet. Use root's GPU lease before server/tab creation.

Run identity before/after and summary from this checkout:

```sh
python3 -B experiments/17-web-cadence-followup/followup.py identity --output experiments/17-web-cadence-followup/evidence/identity-before.json
python3 -B experiments/17-web-cadence-followup/check-followup.py
python3 -B experiments/17-web-cadence-followup/followup.py seal --output experiments/17-web-cadence-followup/evidence/seal-before.json
python3 -B experiments/17-web-cadence-followup/followup.py start --label A1 --lease ROOT_GPU_LEASE
python3 -B experiments/17-web-cadence-followup/followup.py attempt --label A1 --workload idle
ps -axo pid=,pcpu=,rss=,comm= > .work/perf27/raw/A1-idle-process-before.txt
# Execute one CUA navigation/collection below, close its tab, then finite.
ps -axo pid=,pcpu=,rss=,comm= > .work/perf27/raw/A1-idle-process-after.txt
python3 -B experiments/17-web-cadence-followup/followup.py stop --label A1
```

Repeat only declared labels/workloads. Never rerun a failed navigation. Before and after process observations use executable names only, avoiding secret-bearing full process arguments. Available process CPU/RSS is partial context; no complete GPU workload attribution.

CUA persistent setup, after lease:

```js
let evidenceFs = await import('node:fs/promises');
let evidenceDir = '<PERF_WORKTREE>/.work/perf27/raw';
let viewport = await browser.capabilities.get('viewport');
let visibility = await browser.capabilities.get('visibility');
let initialVisibility = await visibility.get();
await viewport.set({width:1280,height:720});
await visibility.set(true);
```

For each planned navigation, create one tab then navigate to its exact declared URL. Use advertised APIs only. The `Shift` key focuses canvas without issuing a Work command. Root capability probes prove document.hasFocus unavailable in the advertised read-only scope. Root separately verified document.visibilityState and activeElement. Preserve explicit null document focus and its reason. Browser presentation and actual AX focus are available partial observations; they do not prove document hasFocus. The DOM evaluator observes canvas geometry only; no performance, renderer, or application state evaluation.

```js
let tab = await cua.createBrowserTab(browser.browserId, exactUrl, {visible:true});
await tab.playwright.locator('#nvwa').press('Shift');
let canvas = await tab.playwright.locator('#nvwa').evaluate(el => {
  const c = el.getBoundingClientRect(); return {width:c.width,height:c.height};
});
let ax = await tab.getAXState();
let documentObservation = await tab.playwright.evaluate(() => ({
  visibility:document.visibilityState,activeElementId:document.activeElement?.id}));
let beforeDom = {...documentObservation,focus:null,
  focus_observation:'unavailable:DOM scope has no hasFocus',
  browser_visible:await visibility.get(),ax_focus:ax,canvas};
await evidenceFs.writeFile(`${evidenceDir}/${label}-${workload}-before-dom.json`, JSON.stringify(beforeDom,null,2), {flag:'wx'});
// One bounded clock sleep16s, then inspect tab.dev.logs({limit:1000}).
// If report is absent, wait up to five more seconds per attempt within45s overall.
// Keep complete final console plus exceptions; no run replacement.
let logs = await tab.dev.logs({limit:1000});
await evidenceFs.writeFile(`${evidenceDir}/${label}-${workload}-console.json`, JSON.stringify(logs,null,2), {flag:'wx'});
// Repeat the same DOM observer for after-dom; save fresh DOM snapshot.
await evidenceFs.writeFile(`${evidenceDir}/${label}-${workload}.png`, await tab.screenshot({fullPage:false}), {flag:'wx'});
await tab.close();
```

The console limit1000 is a finite collection cap. Record if it is reached; a saturated capture is incomplete. Store exceptions in a separate run error file. No extra diagnostic resources or modified HTML. After final arm or any cancellation: stop matching owned server, close remaining task-created tab, `await viewport.reset()`, restore initial browser visibility, record empty task tab inventory and exact port listener absence. Then:

```sh
python3 -B experiments/17-web-cadence-followup/followup.py identity --output experiments/17-web-cadence-followup/evidence/identity-after.json
python3 -B experiments/17-web-cadence-followup/followup.py seal --output experiments/17-web-cadence-followup/evidence/seal-after.json
python3 -B experiments/17-web-cadence-followup/followup.py summarize --output experiments/17-web-cadence-followup/evidence/comparison.json
```

Prior preflight files already exist and must not be overwritten. Use their retained outputs; the commands document reproduction in a fresh evidence directory. Every new evidence file uses exclusive creation.
