/* Synthetic adapter/lifecycle checks only. No browser, PNG, or durable file proof. */
const assert = require('node:assert/strict');
const test = require('node:test');
const { installProbe } = require('./export-probe.js');

function environment(mode) {
  let clock = 0;
  let blobResult = { size: 42, type: 'image/png' };
  let blobError;
  const records = [], clicked = [], revoked = [], scheduled = new Map();
  const listeners = new Map();
  class Element {
    constructor(tagName) { this.tagName = tagName; this.isConnected = false; }
    click() { clicked.push({ attached: this.isConnected }); }
    remove() { this.isConnected = false; }
  }
  class Canvas extends Element {
    constructor() { super('CANVAS'); this.width = 1280; this.height = 720; }
    toBlob(callback) { if (blobError) throw blobError; callback(blobResult); }
  }
  const canvas = new Canvas();
  let urlCount = 0;
  const frame = {
    HTMLElement: Element, HTMLCanvasElement: Canvas,
    navigator: { userActivation: { isActive: false, hasBeenActive: false } },
    URL: {
      createObjectURL() { return 'blob:synthetic-' + ++urlCount; },
      revokeObjectURL(url) { revoked.push(url); },
    },
    document: {
      body: { append(anchor) { anchor.isConnected = true; } },
      getElementById() { return canvas; },
      addEventListener(name, callback) { listeners.set(name, callback); },
      removeEventListener(name) { listeners.delete(name); },
    },
    location: { href: 'synthetic://not-browser' },
  };
  const oldClick = Element.prototype.click;
  const oldRevoke = frame.URL.revokeObjectURL;
  const probe = installProbe(frame, {
    mode, record: row => records.push(row), now: () => clock,
    later(fn, ms) { const id = scheduled.size + 1; scheduled.set(id, { fn, ms }); return id; },
    cancel(id) { scheduled.delete(id); },
  });
  function automatic() {
    const anchor = new Element('A');
    anchor.href = frame.URL.createObjectURL({ size: 77, type: '' });
    anchor.download = 'nvwa-web-benchmark.png';
    anchor.click();
    frame.URL.revokeObjectURL(anchor.href);
    return anchor;
  }
  return {
    frame, canvas, records, clicked, revoked, scheduled, probe, automatic,
    oldClick, oldRevoke, listeners,
    tick(ms) { clock += ms; const pending = [...scheduled.values()]; scheduled.clear(); pending.forEach(timer => timer.fn()); },
    setBlob(value) { blobResult = value; }, setError(value) { blobError = value; },
  };
}

test('SYNTHETIC A/B: actual-anchor adapter preserves A and attaches B, with immediate revocation', () => {
  for (const mode of ['A', 'B']) {
    const env = environment(mode);
    const anchor = env.automatic();
    assert.deepEqual(env.clicked, [{ attached: mode === 'B' }]);
    assert.equal(env.revoked.length, 1);
    assert.equal(anchor.isConnected, false);
    assert.equal(env.records.find(row => row.phase === 'anchor-click-attempt').originallyAttached, false);
    assert.ok(env.records.every(row => row.durableFile === 'NOT-VERIFIED'));
    env.probe.stop();
  }
});

test('SYNTHETIC D: URL remains live and anchor attached until the separate 1000 ms revoke', () => {
  const env = environment('D');
  const anchor = env.automatic();
  assert.equal(env.revoked.length, 0);
  assert.equal(anchor.isConnected, true);
  assert.deepEqual([...env.scheduled.values()].map(timer => timer.ms), [1000]);
  env.tick(1000);
  assert.equal(env.revoked.length, 1);
  assert.equal(anchor.isConnected, false);
  assert.equal(env.records.find(row => row.phase === 'blob-url-revoked').delayFromRequestMs, 1000);
  env.probe.stop();
});

test('SYNTHETIC C: null and thrown toBlob failures remain visible and retain original behavior', () => {
  const env = environment('C');
  env.setBlob(null);
  let callbackValue = 'not-called';
  env.canvas.toBlob(blob => { callbackValue = blob; });
  assert.equal(callbackValue, null);
  assert.ok(env.records.some(row => row.phase === 'toBlob-null'));
  assert.equal(env.revoked.length, 0);
  const error = new Error('synthetic security failure');
  env.setError(error);
  assert.throws(() => env.canvas.toBlob(() => {}), value => value === error);
  assert.ok(env.records.some(row => row.phase === 'toBlob-error'));
  env.probe.stop();
});

test('SYNTHETIC canvas classification never applies D automatic delay to explicit canvas bytes', () => {
  const env = environment('D');
  env.canvas.toBlob(blob => {
    const anchor = new env.frame.HTMLElement('A');
    anchor.href = env.frame.URL.createObjectURL(blob);
    anchor.download = 'nvwa-web-canvas.png';
    env.frame.document.body.append(anchor);
    anchor.click();
    env.frame.URL.revokeObjectURL(anchor.href);
  });
  const attempt = env.records.find(row => row.phase === 'anchor-click-attempt');
  assert.equal(attempt.source, 'real-canvas-toBlob');
  assert.equal(attempt.automatic, false);
  assert.equal(env.scheduled.size, 0);
  assert.equal(env.revoked.length, 1);
  env.probe.stop();
});

test('SYNTHETIC stop cancels pending revoke, releases URL, restores adapters, and is idempotent', () => {
  const env = environment('D');
  const anchor = env.automatic();
  env.probe.stop();
  env.probe.stop();
  assert.equal(env.scheduled.size, 0);
  assert.equal(env.revoked.length, 1);
  assert.equal(anchor.isConnected, false);
  assert.equal(env.frame.HTMLElement.prototype.click, env.oldClick);
  assert.equal(env.frame.URL.revokeObjectURL, env.oldRevoke);
  assert.equal(env.listeners.size, 0);
  assert.equal(env.records.filter(row => row.phase === 'probe-stopped').length, 1);
});
