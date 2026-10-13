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
