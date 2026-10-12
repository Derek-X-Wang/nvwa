/* Throwaway boundary instrumentation; frozen Rust/Wasm and runtime HTML stay unchanged. */
(function (scope) {
  'use strict';

  function installProbe(frame, options) {
    const mode = options.mode;
    if (!['A', 'B', 'C', 'D'].includes(mode)) throw new Error('Unknown screenshot case');
    const now = options.now || (() => frame.performance.now());
    const later = options.later || ((fn, ms) => frame.setTimeout(fn, ms));
    const cancel = options.cancel || (id => frame.clearTimeout(id));
    const started = now();
    const original = {
      create: frame.URL.createObjectURL,
      revoke: frame.URL.revokeObjectURL,
      click: frame.HTMLElement.prototype.click,
      toBlob: frame.HTMLCanvasElement.prototype.toBlob,
    };
    const urls = new Map();
    const canvasBlobs = new WeakMap();
    const timers = new Set();
    let stopped = false;
    let explicitEvent = null;
    let sequence = 0;
    const activation = () => ({
      isActive: frame.navigator.userActivation?.isActive ?? null,
      hasBeenActive: frame.navigator.userActivation?.hasBeenActive ?? null,
    });
    const record = (phase, fields = {}) => options.record({
      sequence: ++sequence, case: mode, phase,
      elapsedMs: now() - started, activation: activation(),
      durableFile: 'NOT-VERIFIED', ...fields,
    });
    const shape = canvas => ({ width: canvas.width, height: canvas.height });
    const clickListener = event => {
      if (event.target?.tagName === 'BUTTON'
          && event.target.textContent === 'Download actual benchmark canvas PNG') {
        explicitEvent = { isTrusted: event.isTrusted, activation: activation() };
        record('explicit-button-event', { event: explicitEvent });
      }
    };
    frame.document.addEventListener('click', clickListener, true);

    frame.HTMLCanvasElement.prototype.toBlob = function (callback, ...args) {
      const canvas = this;
      const request = { event: explicitEvent, activation: activation(), canvas: shape(canvas) };
      record('toBlob-request', request);
      try {
        return original.toBlob.call(canvas, blob => {
          if (blob) canvasBlobs.set(blob, request);
          record(blob ? 'toBlob-blob' : 'toBlob-null', {
            ...request, callbackActivation: activation(),
            blobBytes: blob?.size ?? null, blobType: blob?.type ?? null,
          });
          try { callback(blob); }
          catch (error) {
            record('toBlob-callback-error', { error: String(error) });
            throw error;
          }
        }, ...args);
      } catch (error) {
        record('toBlob-error', { error: String(error) });
        throw error;
      }
    };
    frame.URL.createObjectURL = function (blob) {
      try {
        const url = original.create.call(this, blob);
        const canvasRequest = canvasBlobs.get(blob);
        urls.set(url, {
          createdMs: now(), source: canvasRequest ? 'real-canvas-toBlob' : 'runtime-encoded-blob',
          blobBytes: blob.size, blobType: blob.type, canvasRequest,
          anchor: null, filename: null, pending: false,
        });
        record('blob-url-created', { source: urls.get(url).source, blobBytes: blob.size, blobType: blob.type });
        return url;
      } catch (error) {
        record('blob-url-error', { error: String(error) });
        throw error;
      }
    };
    frame.HTMLElement.prototype.click = function (...args) {
      const entry = this.tagName === 'A' ? urls.get(this.href) : null;
      if (!entry || !this.download.endsWith('.png')) return original.click.apply(this, args);
      const automatic = this.download === 'nvwa-web-benchmark.png' && !entry.canvasRequest;
      entry.filename = this.download;
      entry.anchor = this;
      entry.automatic = automatic;
      const originallyAttached = this.isConnected;
      if (automatic && ['B', 'D'].includes(mode) && !originallyAttached) {
        frame.document.body.append(this);
        record('probe-attached-anchor', { filename: this.download });
      }
      record('anchor-click-attempt', {
        source: entry.source, automatic, filename: this.download,
        originallyAttached, anchorAttached: this.isConnected,
        blobBytes: entry.blobBytes, blobType: entry.blobType,
        canvas: shape(frame.document.getElementById('nvwa')),
        revokePolicy: automatic && mode === 'D' ? 'delay-1000ms' : 'preserve-runtime-request',
      });
      try { return original.click.apply(this, args); }
      catch (error) {
        record('anchor-click-error', { filename: this.download, error: String(error) });
        throw error;
      }
    };
    const revoke = (url, entry, cleanup = false) => {
      try {
        original.revoke.call(frame.URL, url);
        if (entry?.automatic && ['B', 'D'].includes(mode)) entry.anchor?.remove();
        urls.delete(url);
        record('blob-url-revoked', {
          filename: entry?.filename ?? null,
          urlLifetimeMs: entry ? now() - entry.createdMs : null,
          delayFromRequestMs: entry?.requestedMs == null ? null : now() - entry.requestedMs,
          anchorAttached: entry?.anchor?.isConnected ?? null, cleanup,
        });
      } catch (error) {
        record('revoke-error', { filename: entry?.filename ?? null, error: String(error) });
        throw error;
      }
    };
    frame.URL.revokeObjectURL = function (url) {
      const entry = urls.get(url);
      if (!entry) return original.revoke.call(this, url);
      entry.requestedMs = now();
      record('revoke-request', { filename: entry.filename, anchorAttached: entry.anchor?.isConnected ?? null });
      if (entry.automatic && mode === 'D' && !entry.pending) {
        entry.pending = true;
        const timer = later(() => {
          timers.delete(timer);
          if (!stopped) revoke(url, entry);
        }, 1000);
        timers.add(timer);
        return;
      }
      revoke(url, entry);
    };
    record('hooks-ready', { runtimeUrl: frame.location.href, evidenceScope: 'page-instrumented adapter; file outcome pending' });
    return {
      stop() {
        if (stopped) return;
        stopped = true;
        timers.forEach(cancel);
        timers.clear();
        urls.forEach((entry, url) => revoke(url, entry, true));
        frame.URL.createObjectURL = original.create;
        frame.URL.revokeObjectURL = original.revoke;
        frame.HTMLElement.prototype.click = original.click;
        frame.HTMLCanvasElement.prototype.toBlob = original.toBlob;
        frame.document.removeEventListener('click', clickListener, true);
        record('probe-stopped');
      },
    };
  }

  function bootPage() {
    const records = [];
    const picker = document.getElementById('case');
    const selected = new URLSearchParams(location.search).get('case');
    if (['A', 'B', 'C', 'D'].includes(selected)) picker.value = selected;
    const status = document.getElementById('status');
    const output = document.getElementById('records');
    const container = document.getElementById('runtime');
    const stop = document.getElementById('stop');
    let probe;
    let iframe;
    let currentCase;
    const record = row => {
      records.push(row);
      output.textContent = JSON.stringify(records, null, 2);
      output.scrollTop = output.scrollHeight;
      console.info('NVWA_EXPORT_PROBE', JSON.stringify(row));
      if (row.phase === 'hooks-ready') status.textContent = 'PARTIAL — hooks ready; wait for real Rust capture. Persistent file NOT-VERIFIED.';
      if (row.phase === 'anchor-click-attempt') status.textContent = 'PARTIAL — PNG anchor click attempted. Independently inspect the download; file NOT-VERIFIED.';
      if (row.phase.endsWith('error') || row.phase === 'toBlob-null') status.textContent = 'PARTIAL — adapter error/null observed; inspect records. File NOT-VERIFIED.';
    };
    scope.nvwaExportExperiment = { records, installProbe };
    function shutdown() {
      probe?.stop();
      probe = null;
      iframe?.remove();
      iframe = null;
      stop.disabled = true;
    }
    stop.addEventListener('click', () => {
      shutdown();
      status.textContent = 'Runtime stopped. Records retained in memory; file outcome remains external.';
    });
    document.getElementById('start').addEventListener('click', event => {
      shutdown();
      records.length = 0;
      currentCase = picker.value;
      record({ case: currentCase, phase: 'start-event', isTrusted: event.isTrusted,
        activation: { isActive: navigator.userActivation?.isActive ?? null, hasBeenActive: navigator.userActivation?.hasBeenActive ?? null }, durableFile: 'NOT-VERIFIED' });
      status.textContent = 'NOT-RUN — loading frozen runtime; hooks not installed yet.';
      const runtimeFrame = document.createElement('iframe');
      const runtimeCase = currentCase;
      iframe = runtimeFrame;
      runtimeFrame.title = 'Frozen Nvwa Rust runtime';
      runtimeFrame.addEventListener('load', () => {
        if (iframe !== runtimeFrame) return;
        try { probe = installProbe(runtimeFrame.contentWindow, { mode: runtimeCase, record }); }
        catch (error) { record({ phase: 'hook-install-error', error: String(error), durableFile: 'NOT-VERIFIED' }); }
      }, { once: true });
      runtimeFrame.src = 'index.html?benchmark=1';
      container.append(runtimeFrame);
      stop.disabled = false;
    });
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { installProbe };
  else bootPage();
})(typeof window !== 'undefined' ? window : globalThis);
