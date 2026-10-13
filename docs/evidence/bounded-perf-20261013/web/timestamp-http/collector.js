// Passive diagnostic. No fetch/console/WebGPU override, input dispatch or canvas write.
(() => {
  'use strict';
  const runId = location.pathname.match(/^\/run\/([0-9a-f]{32})\//)?.[1] ?? null;
  const startedAtMs = performance.now();
  const milestones = [];
  const output = document.createElement('pre');
  output.id = 'nvwa-startup-json';
  output.hidden = true;
  let ended = false;
  let sawHidden = false;
  let droppedResourceEntries = 0;
  const finite = value => Number.isFinite(value) && value >= 0 ? value : null;
  const fields = ['startTime', 'duration', 'fetchStart', 'domainLookupStart', 'domainLookupEnd',
    'connectStart', 'connectEnd', 'secureConnectionStart', 'requestStart', 'responseStart',
    'responseEnd', 'transferSize', 'encodedBodySize', 'decodedBodySize'];
  const timing = entry => ({name: entry.name, entryType: entry.entryType,
    initiatorType: entry.initiatorType ?? null, nextHopProtocol: entry.nextHopProtocol ?? null,
    deliveryType: entry.deliveryType ?? null, responseStatus: entry.responseStatus ?? null,
    ...Object.fromEntries(fields.map(field => [field, finite(entry[field])])),
    ...(entry.entryType === 'navigation' ? {
      type: entry.type, domInteractive: finite(entry.domInteractive),
      domContentLoadedEventStart: finite(entry.domContentLoadedEventStart),
      domContentLoadedEventEnd: finite(entry.domContentLoadedEventEnd),
      loadEventStart: finite(entry.loadEventStart), loadEventEnd: finite(entry.loadEventEnd)
    } : {})});
  const geometry = () => {
    const canvas = document.getElementById('nvwa');
    const bounds = canvas?.getBoundingClientRect();
    return {viewportCss: {width: innerWidth, height: innerHeight}, devicePixelRatio,
      canvasCss: bounds ? {x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height} : null,
      canvasBacking: canvas ? {width: canvas.width, height: canvas.height} : null,
      visibilityState: document.visibilityState};
  };
  const observeStatus = () => {
    const status = document.getElementById('boot-status');
    if (status?.hidden && !sawHidden) {
      sawHidden = true;
      milestones.push({name: 'boot-status-hidden-observed', observedAtMs: performance.now(),
        meaning: 'production init returned; observation upper bound; does not prove asset readiness or first presentation'});
    }
  };
  const snapshot = () => ({schema: 'nvwa-http-startup-browser-v1', runId, url: location.href,
    clock: 'Performance monotonic milliseconds since navigation timeOrigin',
    timeOriginEpochMs: performance.timeOrigin, snapshotAtMs: performance.now(), installedAtMs: startedAtMs,
    ended, userAgent: navigator.userAgent, geometry: geometry(), milestones: [...milestones],
    navigation: performance.getEntriesByType('navigation').map(timing),
    resources: performance.getEntriesByType('resource').slice(0, 2000).map(timing),
    resourceTimingLimit: {retainedLimit: 2000, entriesBeyondLimit: Math.max(0, performance.getEntriesByType('resource').length - 2000),
      browserBufferFullEvents: droppedResourceEntries},
    paint: performance.getEntriesByType('paint').map(entry => ({name: entry.name, startTime: finite(entry.startTime)})),
    supportedEntryTypes: globalThis.PerformanceObserver?.supportedEntryTypes ?? [],
    visibility: {assetReady: 'NOT-RUN: no read-only DOM milestone in frozen build; external NVWA_EVIDENCE uses Bevy TimeReal since first update',
      exactFirstPresentation: 'NOT-RUN: paint entries and hidden boot status do not identify WebGPU first frame',
      actualPixels: 'NOT-RUN: external screenshot completion may establish a visible upper bound'},
    limits: ['HTTP cache boundary only; browser/GPU/OS/shader state is not cold-proven',
      'resource size zero may mean unavailable timing; never interpret it alone as absence or cache hit',
      'no conversion between Bevy TimeReal and navigation monotonic clock']});
  const publish = () => {
    observeStatus();
    if (!output.isConnected && document.body) document.body.append(output);
    output.textContent = JSON.stringify(snapshot());
  };
  Object.defineProperty(window, 'nvwaStartupDiagnostics', {value: Object.freeze({snapshot}), configurable: false});
  const observer = new MutationObserver(publish);
  observer.observe(document.documentElement, {subtree: true, attributes: true, attributeFilter: ['hidden']});
  document.addEventListener('DOMContentLoaded', publish, {once: true});
  window.addEventListener('load', publish, {once: true});
  performance.addEventListener('resourcetimingbufferfull', () => { droppedResourceEntries++; });
  const timer = setInterval(publish, 250);
  setTimeout(() => { ended = true; clearInterval(timer); observer.disconnect(); publish(); }, 120000);
  publish();
})();

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

// OPTIONAL DIAGNOSTIC VARIANT. Changes production device/pass/encoder options.
// Uses actual production passes; no dummy pass, extra device or queue submit.
(() => {
  'use strict';
  const devices = new WeakMap(), queues = new WeakMap(), encoders = new WeakMap(), commands = new WeakMap();
  const records = [], errors = [], featureRequests = [];
  let instrumentedEncoders = 0, passCount = 0, mappedCount = 0;
  const safe = fn => { try { fn(); } catch (e) { if (errors.length < 16) errors.push(String(e)); } };
  const cleanup = metadata => {
    for (const name of ['readback', 'resolve', 'query']) safe(() => metadata[name]?.destroy());
  };
  const hook = (type, name, wrapper) => safe(() => {
    const p = globalThis[type]?.prototype, d = p && Object.getOwnPropertyDescriptor(p, name);
    if (!d || !d.configurable || typeof d.value !== 'function') throw new Error('hook unavailable: ' + type + '.' + name);
    Object.defineProperty(p, name, {...d, value: wrapper(d.value)});
  });
  hook('GPUAdapter', 'requestDevice', original => function (...args) {
    let forwarded = args;
    if (this.features.has('timestamp-query')) {
      const descriptor = args[0] ?? {};
      // Clone only this diagnostic variant. Preserve original descriptor/array.
      forwarded = [{...descriptor, requiredFeatures: Array.from(new Set([...(descriptor.requiredFeatures ?? []), 'timestamp-query']))}, ...args.slice(1)];
      featureRequests.push({requested: true, atMs: performance.now()});
    } else featureRequests.push({requested: false, atMs: performance.now()});
    const result = Reflect.apply(original, this, forwarded);
    safe(() => result.then(device => safe(() => {
      const info = {device, enabled: device.features.has('timestamp-query')};
      devices.set(device, info); queues.set(device.queue, info);
      device.addEventListener?.('uncapturederror', event => safe(() => {
        if (errors.length < 16) errors.push('actual GPU validation error: ' + String(event.error?.message ?? event.error));
      }));
      device.lost?.then(reason => safe(() => { if (errors.length < 16) errors.push('actual device lost: ' + String(reason.message)); }));
    }), e => safe(() => { if (errors.length < 16) errors.push('requestDevice rejected: ' + String(e)); })));
    return result;
  });
  hook('GPUDevice', 'createCommandEncoder', original => function (...args) {
    const encoder = Reflect.apply(original, this, args);
    safe(() => { const info = devices.get(this); if (info?.enabled) encoders.set(encoder, {info, passes: [], finished: false}); });
    return encoder;
  });
  const passHook = kind => original => function (...args) {
    let forwarded = args;
    const metadata = encoders.get(this), descriptor = args[0];
    if (metadata && !metadata.finished && descriptor && !descriptor.timestampWrites && passCount < 32) {
      safe(() => {
        if (!metadata.query && instrumentedEncoders < 8) {
          const device = metadata.info.device;
          metadata.query = device.createQuerySet({type: 'timestamp', count: 64});
          metadata.resolve = device.createBuffer({size: 512, usage: GPUBufferUsage.QUERY_RESOLVE | GPUBufferUsage.COPY_SRC});
          metadata.readback = device.createBuffer({size: 512, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ});
          instrumentedEncoders++;
        }
        if (metadata.query) {
          const index = metadata.passes.length * 2;
          forwarded = [{...descriptor, timestampWrites: {querySet: metadata.query,
            beginningOfPassWriteIndex: index, endOfPassWriteIndex: index + 1}}, ...args.slice(1)];
          metadata.passes.push({kind, index, ordinal: passCount++, label: String(descriptor.label ?? '').slice(0, 100)});
        }
      });
    }
    return Reflect.apply(original, this, forwarded);
  };
  hook('GPUCommandEncoder', 'beginRenderPass', passHook('render'));
  hook('GPUCommandEncoder', 'beginComputePass', passHook('compute'));
  hook('GPUCommandEncoder', 'finish', original => function (...args) {
    const metadata = encoders.get(this);
    if (metadata?.passes.length && !metadata.finished) safe(() => {
      this.resolveQuerySet(metadata.query, 0, metadata.passes.length * 2, metadata.resolve, 0);
      this.copyBufferToBuffer(metadata.resolve, 0, metadata.readback, 0, metadata.passes.length * 16);
      metadata.finished = true;
    });
    const result = Reflect.apply(original, this, args);
    safe(() => { if (metadata?.finished) commands.set(result, metadata); });
    return result;
  });
  hook('GPUQueue', 'submit', original => function (...args) {
    const result = Reflect.apply(original, this, args);
    safe(() => {
      if (!Array.isArray(args[0])) return; // never consume an iterable again
      for (const command of args[0]) {
        const metadata = commands.get(command);
        if (!metadata || metadata.mapped) continue;
        metadata.mapped = true;
        metadata.readback.mapAsync(GPUMapMode.READ, 0, metadata.passes.length * 16).then(() => {
          try { safe(() => {
            const ticks = new BigUint64Array(metadata.readback.getMappedRange(0, metadata.passes.length * 16));
            for (const pass of metadata.passes) {
              const start = ticks[pass.index], end = ticks[pass.index + 1];
              if (end < start) throw new Error('nonmonotonic GPU timestamps');
              records.push({...pass, startNs: start.toString(), endNs: end.toString(), durationNs: (end - start).toString(),
                clock: 'WebGPU timestamp query nanoseconds; uncalibrated to navigation/CPU', mappedAtMs: performance.now()});
            }
            mappedCount++;
            metadata.readback.unmap();
          }); } finally { cleanup(metadata); }
        }, e => { safe(() => { if (errors.length < 16) errors.push('mapAsync rejected: ' + String(e)); }); cleanup(metadata); });
      }
    });
    return result;
  });
  const snapshot = () => ({schema: 'nvwa-webgpu-timestamp-variant-v1', variant: true,
    featureRequests: [...featureRequests], instrumentedEncoders, passCount, mappedCount,
    records: [...records], errors: [...errors],
    status: records.length && !errors.length ? 'OBSERVED_PASS_DURATION' : 'NOT-RUN',
    overhead: 'up to8 query sets64queries plus8x512byte resolve and readback buffers; max32 production passes; requestDevice/pass/finish descriptors changed',
    limits: 'GPU pass duration only; nanosecond units with implementation-defined coarse precision; no full-frame, compositor, first character, display or GPU-memory claim'});
  Object.defineProperty(window, 'nvwaTimestampVariantDiagnostics', {value: Object.freeze({snapshot}), configurable: false});
})();
