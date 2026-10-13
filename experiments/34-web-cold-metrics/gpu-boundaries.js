// Diagnostic wrapper only. No extra adapter/device/queue submission is requested.
(() => {
  'use strict';
  const clock = 'Performance monotonic milliseconds since navigation timeOrigin';
  const events = [], hooks = [], devices = [], heap = [];
  let dropped = 0, ended = false;
  const out = document.createElement('pre');
  out.id = 'nvwa-web-perf-json'; out.hidden = true;
  const now = () => performance.now();
  const safe = callback => { try { callback(); } catch (_) { /* instrumentation must not throw into production */ } };
  const event = (name, data = {}) => safe(() => {
    if (events.length < 64) events.push({name, atMs: now(), clock, ...data}); else dropped++;
  });
  const hook = (type, name, wrapper) => safe(() => {
    const prototype = globalThis[type]?.prototype;
    const descriptor = prototype && Object.getOwnPropertyDescriptor(prototype, name);
    if (!descriptor || typeof descriptor.value !== 'function' || !descriptor.configurable) {
      hooks.push({method: type + '.' + name, installed: false}); return;
    }
    Object.defineProperty(prototype, name, {...descriptor, value: wrapper(descriptor.value)});
    hooks.push({method: type + '.' + name, installed: true});
  });
  const seenQueues = new WeakSet(), seenContexts = new WeakSet();
  hook('GPUAdapter', 'requestDevice', original => function (...args) {
    const result = Reflect.apply(original, this, args);
    safe(() => {
      // Preserve the exact promise returned by production's method.
      result.then(device => safe(() => {
        if (devices.length < 8) devices.push({enabledFeatures: Array.from(device.features).sort(), observedAtMs: now(), clock});
        event('production-device-resolved-observed', {meaning: 'promise reaction CPU observation; no GPU execution/display claim'});
      }), () => event('production-device-rejected-observed'));
    });
    return result;
  });
  hook('GPUQueue', 'submit', original => function (...args) {
    const result = Reflect.apply(original, this, args);
    safe(() => {
      if (!seenQueues.has(this)) {
        seenQueues.add(this);
        event('first-production-queue-submit-return', {meaning: 'CPU API returned after a production submit; commands may be uploads or offscreen; not GPU duration or display'});
      }
    });
    return result;
  });
  hook('GPUCanvasContext', 'getCurrentTexture', original => function (...args) {
    const result = Reflect.apply(original, this, args);
    safe(() => {
      if (!seenContexts.has(this)) {
        seenContexts.add(this);
        event('first-production-canvas-texture-return', {meaning: 'CPU texture acquisition returned; not submit, present, compositor or visible pixels'});
      }
    });
    return result;
  });
  const sampleHeap = () => safe(() => {
    const m = performance.memory;
    if (m && heap.length < 30) heap.push({atMs: now(), clock, usedJSHeapSize: m.usedJSHeapSize,
      totalJSHeapSize: m.totalJSHeapSize, jsHeapSizeLimit: m.jsHeapSizeLimit,
      meaning: 'browser-exposed JS heap only; may be coarse/shared; excludes process RSS, GPU and complete Wasm memory'});
  });
  const snapshot = () => ({schema: 'nvwa-web-perf-browser-v1', clock, snapshotAtMs: now(), ended,
    startup: window.nvwaStartupDiagnostics.snapshot(), events: [...events], hooks: [...hooks],
    eventsDropped: dropped, devices: devices.map(d => ({...d, enabledFeatures: [...d.enabledFeatures]})),
    jsHeap: {status: heap.length ? 'OBSERVED_SUBSET' : 'NOT-RUN', samples: [...heap]},
    claims: {firstPhysicalPresentation: 'NOT-RUN', gpuTimestampDuration: 'NOT-RUN',
      gpuMemory: 'NOT-RUN', browserProcessMemory: 'NOT-RUN', fullyCold: 'NOT-RUN'},
    gpuTimestampVariant: globalThis.nvwaTimestampVariantDiagnostics?.snapshot() ?? null,
    overhead: 'three production-called WebGPU prototype wrappers; bounded first-call events; 1s heap/DOM sample for30s; retained base collector250ms/120s'});
  const publish = () => safe(() => {
    if (!out.isConnected && document.body) document.body.append(out);
    out.textContent = JSON.stringify(snapshot());
  });
  Object.defineProperty(window, 'nvwaWebPerfDiagnostics', {value: Object.freeze({snapshot}), configurable: false});
  sampleHeap(); publish();
  const timer = setInterval(() => { sampleHeap(); publish(); }, 1000);
  setTimeout(() => {
    ended = true; clearInterval(timer); publish();
    safe(() => {
      const payload = JSON.stringify(snapshot());
      console.info('NVWA_WEB_PERF ' + payload);
      if (new TextEncoder().encode(payload).length <= 512000) {
        fetch('./capture.json', {method: 'POST', credentials: 'omit', headers: {'Content-Type': 'application/json'}, body: payload})
          .then(response => console.info('NVWA_WEB_PERF_RETAINED ' + response.status),
            () => console.info('NVWA_WEB_PERF_RETAINED unavailable'));
      }
    });
  }, 30000);
})();
