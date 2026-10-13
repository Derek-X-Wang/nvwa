// Node VM CPU controls. Fake API objects; no browser, GPU, or timing result.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const here = new URL('.', import.meta.url);
const baseline = fs.readFileSync(new URL('gpu-boundaries.js', here), 'utf8');
const variant = fs.readFileSync(new URL('timestamp-variant.js', here), 'utf8');

function setup(enabled) {
  const calls = [];
  class GPUQueue { submit(...args) { calls.push(['submit', this, args]); if (args[0] === 'throw') throw sentinel; return token; } }
  class GPUCanvasContext { getCurrentTexture(...args) { calls.push(['texture', this, args]); return token; } }
  class GPUCommandEncoder {
    beginRenderPass(...args) { calls.push(['render', this, args]); return token; }
    beginComputePass(...args) { calls.push(['compute', this, args]); return token; }
    resolveQuerySet(...args) { calls.push(['resolve', this, args]); }
    copyBufferToBuffer(...args) { calls.push(['copy', this, args]); }
    finish(...args) { calls.push(['finish', this, args]); return {}; }
  }
  class GPUDevice {
    constructor() { this.features = new Set(enabled ? ['timestamp-query'] : []); this.queue = new GPUQueue(); }
    createCommandEncoder(...args) { calls.push(['encoder', this, args]); return new GPUCommandEncoder(); }
    createQuerySet(d) { calls.push(['query', this, [d]]); return {destroy() { calls.push(['query-destroy']); }}; }
    createBuffer(d) { calls.push(['buffer', this, [d]]); return {mapAsync() { return Promise.resolve(); },
      getMappedRange() { return new BigUint64Array(Array.from({length: 64}, (_, i) => BigInt(i * 100))).buffer; },
      unmap() { calls.push(['unmap']); }, destroy() { calls.push(['buffer-destroy']); }}; }
  }
  const device = new GPUDevice(), promise = Promise.resolve(device);
  class GPUAdapter {
    constructor() { this.features = new Set(enabled ? ['timestamp-query'] : []); }
    requestDevice(...args) { calls.push(['requestDevice', this, args]); return promise; }
  }
  let tick = 0;
  const context = {GPUAdapter, GPUQueue, GPUCanvasContext, GPUDevice, GPUCommandEncoder,
    GPUBufferUsage: {QUERY_RESOLVE: 1, COPY_SRC: 2, COPY_DST: 4, MAP_READ: 8}, GPUMapMode: {READ: 1},
    document: {createElement() { return {}; }, body: {append() {} }},
    performance: {now() { return ++tick; }},
    setInterval() {}, setTimeout() {}, console,
    nvwaStartupDiagnostics: {snapshot() { return {}; }}};
  context.window = context;
  vm.createContext(context);
  const sentinel = new Error('original failure'), token = {};
  return {context, calls, device, promise, sentinel, token};
}

{
  const s = setup(false); vm.runInContext(baseline, s.context);
  const adapter = new s.context.GPUAdapter(), descriptor = {requiredFeatures: []};
  assert.equal(adapter.requestDevice(descriptor), s.promise, 'exact production promise preserved');
  assert.equal(s.calls[0][1], adapter, 'this preserved');
  assert.equal(s.calls[0][2][0], descriptor, 'original descriptor identity preserved');
  assert.equal(s.device.queue.submit([]), s.token, 'return identity preserved');
  assert.throws(() => s.device.queue.submit('throw'), e => e === s.sentinel, 'original thrown object preserved');
  assert.equal(new s.context.GPUCanvasContext().getCurrentTexture('arg'), s.token);
  await Promise.resolve();
  assert.equal(s.context.nvwaWebPerfDiagnostics.snapshot().devices.length, 1);
  assert.equal(s.calls.filter(x => x[0] === 'requestDevice').length, 1, 'no extra device requests');
}
{
  const s = setup(false); vm.runInContext(baseline + variant, s.context);
  const descriptor = {requiredFeatures: []};
  assert.equal(new s.context.GPUAdapter().requestDevice(descriptor), s.promise);
  assert.equal(s.calls[0][2][0], descriptor, 'unavailable feature preserves exact descriptor');
  await Promise.resolve();
  const encoder = s.device.createCommandEncoder(), pass = {colorAttachments: []};
  assert.equal(encoder.beginRenderPass(pass), s.token);
  assert.equal(s.calls.find(x => x[0] === 'render')[2][0], pass, 'unavailable feature preserves exact pass');
  assert.equal(s.calls.filter(x => x[0] === 'query').length, 0);
}
{
  const s = setup(true); vm.runInContext(baseline + variant, s.context);
  const descriptor = {requiredFeatures: ['feature-a']}, adapter = new s.context.GPUAdapter();
  assert.equal(adapter.requestDevice(descriptor), s.promise);
  assert.deepEqual(descriptor, {requiredFeatures: ['feature-a']}, 'feature descriptor untouched');
  assert.equal(s.calls[0][2][0].requiredFeatures.includes('timestamp-query'), true);
  await Promise.resolve(); await Promise.resolve();
  const encoder = s.device.createCommandEncoder(), pass = {colorAttachments: []};
  assert.equal(encoder.beginRenderPass(pass), s.token);
  assert.equal(Object.hasOwn(pass, 'timestampWrites'), false, 'pass descriptor untouched');
  const forwarded = s.calls.find(x => x[0] === 'render')[2][0];
  assert.equal(forwarded.timestampWrites.beginningOfPassWriteIndex, 0);
  assert.equal(forwarded.timestampWrites.endOfPassWriteIndex, 1);
  const command = encoder.finish();
  assert.equal(s.device.queue.submit([command]), s.token);
  await Promise.resolve(); await Promise.resolve();
  const diagnostic = s.context.nvwaTimestampVariantDiagnostics.snapshot();
  assert.equal(diagnostic.records.length, 1);
  assert.equal(diagnostic.records[0].durationNs, '100', 'CPU fake tick arithmetic only');
  assert.equal(s.calls.filter(x => x[0] === 'submit').length, 1, 'no added submit');
  assert.equal(s.calls.filter(x => x[0] === 'requestDevice').length, 1, 'no added device');
  assert.equal(s.calls.filter(x => x[0] === 'query-destroy').length, 1);
  assert.equal(s.calls.filter(x => x[0] === 'buffer-destroy').length, 2);
  const old = {timestampWrites: {existing: true}};
  s.device.createCommandEncoder().beginComputePass(old);
  assert.equal(s.calls.find(x => x[0] === 'compute')[2][0], old, 'existing timestampWrites untouched');
  for (let i = 0; i < 50; i++) {
    const e = s.device.createCommandEncoder();
    e.beginRenderPass({});
    e.finish();
  }
  const bounded = s.context.nvwaTimestampVariantDiagnostics.snapshot();
  assert.ok(bounded.instrumentedEncoders <= 8);
  assert.ok(bounded.passCount <= 32);
}
console.log('PASS CPU wrapper preservation, unavailable-feature path, fake tick arithmetic, lifecycle and boundedness; GPU NOT-RUN');
