"""Node VM controls of actual client lifecycle; synthetic APIs, no Wasm/assets/UI."""
from pathlib import Path
import shutil
import subprocess
import unittest

CLIENT = Path(__file__).with_name('client.js').resolve()
NODE_CONTROL = r'''
const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const source = fs.readFileSync(process.argv[1], 'utf8');
const mode = process.argv[2];
const deferred = () => {
  let resolve;
  const promise = new Promise(r => { resolve = r; });
  return { promise, resolve };
};
const flush = async () => { for (let i = 0; i < 40; ++i) await Promise.resolve(); };
async function check() {
  const hanging = deferred();
  const calls = { init: 0, begin: 0, poll: 0, complete: 0, import: 0, posts: [] };
  const status = { textContent: '' };
  const root = { dataset: {} };
  let clock = 0;
  let expire;
  let signal;
  const api = {
    default: () => mode === 'wasm-init' ? hanging.promise : Promise.resolve(),
    init: () => { calls.init++; },
    begin_case: () => { calls.begin++; },
    poll: () => { calls.poll++; return '{"synthetic":"verbatim"}'; },
    complete: () => { calls.complete++; return '{"synthetic":"complete"}'; },
  };
  const context = vm.createContext({
    document: { querySelector: () => status, documentElement: root },
    location: { href: 'http://127.0.0.1:9218/', origin: 'http://127.0.0.1:9218' },
    performance: { now: () => clock },
    URL, AbortController,
    console: { error() {} },
    setTimeout: (fn, ms) => {
      if (ms === 300000) { expire = fn; return 1; }
      return setTimeout(fn, ms);
    },
    clearTimeout: id => { if (id !== 1) clearTimeout(id); },
    fetch: (url, options) => {
      signal = options.signal;
      if (url.endsWith('/config')) {
        if (mode === 'config') return hanging.promise;
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ run_id: 'synthetic', asset_root: 'assets' }),
        });
      }
      calls.posts.push({ url, body: options.body });
      return hanging.promise;
    },
  });
  // Execute the checked-in client itself. Substitute only its module-loader
  // function seam before config's awaited promise resumes; no actual import.
  vm.runInContext(source, context);
  context.loadReplayModule = () => {
    calls.import++;
    return mode === 'import' ? hanging.promise : Promise.resolve(api);
  };
  await flush();
  assert.equal(typeof expire, 'function', 'overall deadline not installed');
  if (mode === 'post') {
    assert.equal(calls.posts.length, 1);
    assert.equal(calls.posts[0].body, '{"synthetic":"verbatim"}\n');
  }
  clock = 300001;
  expire();
  await flush();
  assert.equal(root.dataset.captureState, 'failed');
  assert.equal(signal.aborted, true, 'fetch signal not aborted');
  const before = { ...calls, posts: calls.posts.length };
  hanging.resolve(mode === 'import' ? api : undefined);
  await flush();
  assert.deepEqual({ ...calls, posts: calls.posts.length }, before,
    'late promise result resumed capture');
  assert.equal(calls.complete, 0);
  if (mode !== 'post') {
    assert.equal(calls.init, 0);
    assert.equal(calls.poll, 0);
    assert.equal(calls.posts.length, 0);
  } else {
    assert.equal(calls.begin, 1);
    assert.equal(calls.poll, 1);
  }
  process.stdout.write(`PASS synthetic hanging ${mode}: abort + late-result fence\n`);
}
check().catch(error => { console.error(error); process.exitCode = 1; });
'''


class ClientLifecycleControls(unittest.TestCase):
    def control(self, mode):
        node = shutil.which('node')
        if node is None:
            self.fail('Node.js is required for Wasm client lifecycle controls; node missing')
        result = subprocess.run([node, '-e', NODE_CONTROL, str(CLIENT), mode],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS synthetic hanging ' + mode, result.stdout)

    def test_hanging_config_aborts_and_fences_late_result(self):
        self.control('config')

    def test_hanging_import_cannot_late_initialize(self):
        self.control('import')

    def test_hanging_wasm_init_cannot_late_initialize(self):
        self.control('wasm-init')

    def test_hanging_post_aborts_without_next_case_or_complete(self):
        self.control('post')


if __name__ == '__main__':
    unittest.main()
