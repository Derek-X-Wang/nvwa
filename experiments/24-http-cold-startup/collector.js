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
