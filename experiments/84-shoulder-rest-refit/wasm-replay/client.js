// Browser-local CPU capture. Rust witness strings are never parsed/re-serialized.
const status = document.querySelector('#status');
const wait = () => new Promise(resolve => setTimeout(resolve, 0));
const ARM = 'b1_arm_rehearsal_v1';
const KNEE = 'b1_knee_flex_v1';
const OVERALL_TIMEOUT_MS = 5 * 60 * 1000;

function sameOrigin(value) {
  const url = new URL(value, location.href);
  if (url.origin !== location.origin) throw new Error('Cross-origin capture URL rejected');
  return url.href;
}
function loadReplayModule(url) {
  return import(url);
}
function lifecycle() {
  const controller = new AbortController();
  const deadline = performance.now() + OVERALL_TIMEOUT_MS;
  let stopped = false;
  let rejectDeadline;
  const expired = new Promise((_, reject) => { rejectDeadline = reject; });
  const timer = setTimeout(() => {
    stopped = true;
    controller.abort();
    rejectDeadline(new Error('Five-minute overall capture deadline exceeded'));
  }, OVERALL_TIMEOUT_MS);
  function check() {
    if (stopped || performance.now() >= deadline) {
      stopped = true;
      controller.abort();
      throw new Error('Five-minute overall capture deadline exceeded or lifecycle stopped');
    }
  }
  return {
    signal: controller.signal,
    check,
    async bounded(promise) {
      check();
      const result = await Promise.race([promise, expired]);
      check();
      return result;
    },
    close() {
      stopped = true;
      clearTimeout(timer);
      controller.abort();
    },
  };
}
async function send(path, raw, life) {
  life.check();
  if (typeof raw !== 'string' || !raw.length || raw.includes('\n')) {
    throw new Error('Expected one verbatim compact Rust JSON record');
  }
  const response = await life.bounded(fetch(sameOrigin(path), {
    method: 'POST', body: raw + '\n', headers: { 'Content-Type': 'application/json' },
    cache: 'no-store', credentials: 'omit', redirect: 'error', signal: life.signal,
  }));
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
}
async function run() {
  const life = lifecycle();
  try {
    const response = await life.bounded(fetch(sameOrigin('/config'), {
      cache: 'no-store', credentials: 'omit', redirect: 'error', signal: life.signal,
    }));
    if (!response.ok) throw new Error(`/config: HTTP ${response.status}`);
    const config = Object.freeze(await life.bounded(response.json()));
    if (typeof config.run_id !== 'string' || config.asset_root !== 'assets') {
      throw new Error('Immutable run_id and asset_root=assets required');
    }
    if ((config.capture_path ?? '/capture') !== '/capture' || (config.complete_path ?? '/complete') !== '/complete') {
      throw new Error('Unexpected capture transport paths');
    }
    const api = await life.bounded(loadReplayModule(sameOrigin(config.pkg_module ?? '/pkg/nvwa_shoulder_wasm_replay.js')));
    // Dynamic import/instantiation cannot always be aborted. Their late result
    // cannot cross the bounded await or reach any host call after expiration.
    await life.bounded(api.default());
    life.check();
    api.init(config.asset_root, config.run_id);
    life.check();
    let count = 0;
    for (const torso of [-1, 0, 1]) {
      for (const clip of [ARM, KNEE]) {
        for (const k of clip === ARM ? [0, 8, 16, 24, 32] : [16]) {
          const deadline = performance.now() + 45_000;
          life.check();
          api.begin_case(torso, clip, k, config.run_id);
          status.textContent = `Capturing ${count + 1}/18: torso ${torso}, ${clip}, k${k}`;
          let raw;
          while (true) {
            life.check();
            if (performance.now() >= deadline) throw new Error('45-second case deadline exceeded');
            raw = api.poll();
            life.check();
            if (performance.now() >= deadline) throw new Error('45-second case deadline exceeded');
            if (typeof raw === 'string') break;
            if (raw !== undefined && raw !== null) throw new Error('Unexpected poll response');
            await life.bounded(wait()); // Yield so AssetServer/fetch promises settle.
          }
          await send('/capture', raw, life);
          count += 1;
          await life.bounded(wait());
        }
      }
    }
    life.check();
    await send('/complete', api.complete(), life);
    life.check();
    status.textContent = 'Completed 18 production CPU snapshots. Admission remains separate.';
    document.documentElement.dataset.captureState = 'complete';
  } finally {
    life.close();
  }
}
run().catch(error => {
  status.textContent = `STOPPED: ${String(error)}`;
  document.documentElement.dataset.captureState = 'failed';
  console.error(error);
});
