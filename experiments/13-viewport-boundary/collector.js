/* Disposable DOM diagnostic. Never imports/calls Nvwa/Wasm/editor APIs. */
(() => {
  "use strict";
  const canvas = document.getElementById("nvwa");
  const panel = document.getElementById("viewport-boundary-panel");
  const jsonNode = document.getElementById("viewport-boundary-json");
  const view = document.getElementById("viewport-boundary-view");
  const status = document.getElementById("viewport-boundary-status");
  const maxRecords = 180;
  const startedAt = new Date().toISOString();
  const capabilities = {
    devicePixelRatio: typeof window.devicePixelRatio === "number",
    visualViewport: Boolean(window.visualViewport),
    resizeObserver: typeof ResizeObserver !== "undefined",
    devicePixelContentBox: typeof ResizeObserverEntry !== "undefined"
      && "devicePixelContentBoxSize" in ResizeObserverEntry.prototype,
    mutationObserver: typeof MutationObserver !== "undefined",
  };
  const records = [];
  let droppedRecords = 0;
  let sequence = 0;
  let latestObservedBoxes = null;
  let samplingTimer = null;
  let samplingDeadline = null;
  let settleTimer = null;
  let samplingWindowsStarted = 0;
  const errors = [];
  const finite = n => typeof n === "number" && Number.isFinite(n) ? n : null;
  const rectOf = node => {
    if (!node) return null;
    const r = node.getBoundingClientRect();
    return Object.fromEntries(["x", "y", "left", "top", "right", "bottom", "width", "height"]
      .map(k => [k, finite(r[k])]));
  };
  const geometryOf = node => {
    if (!node) return null;
    const style = getComputedStyle(node);
    return {
      tag: node.tagName, id: node.id || null, connected: node.isConnected,
      hidden: Boolean(node.hidden), rect: rectOf(node),
      client: { width: node.clientWidth, height: node.clientHeight },
      offset: { width: node.offsetWidth, height: node.offsetHeight },
      css: Object.fromEntries(["width", "height", "display", "position", "boxSizing",
        "borderLeftWidth", "borderTopWidth", "borderRightWidth", "borderBottomWidth",
        "paddingLeft", "paddingTop", "paddingRight", "paddingBottom", "transform",
        "writingMode", "zoom", "visibility", "opacity"]
        .map(k => [k, style[k] || null])),
    };
  };
  const boxList = boxes => boxes ? Array.from(boxes).map(box => ({
    inlineSize: finite(box.inlineSize), blockSize: finite(box.blockSize),
  })) : null;
  function report() {
    return {
      schemaVersion: 1,
      diagnostic: "Nvwa DOM viewport boundary; no runtime scales are directly observed",
      startedAt, page: { origin: location.origin, path: location.pathname,
        query: location.search, userAgent: navigator.userAgent },
      capabilities, maxRecords, droppedRecords, samplingWindowsStarted,
      samplingActive: samplingTimer !== null, samplingDeadline,
      errors: [...errors], records,
    };
  }
  function publish() {
    jsonNode.textContent = JSON.stringify(report());
    // Keep the collapsed panel cheap. Open-panel output is a view of the latest record.
    if (panel.open) view.textContent = JSON.stringify(records.at(-1) || {}, null, 2);
    status.textContent = `${records.length} retained; ${droppedRecords} dropped. `
      + (samplingTimer !== null ? "1 Hz sampling active (180-second bound)." : "Event-only capture active.");
  }
  function capture(reason) {
    const c = geometryOf(canvas);
    const r = c?.rect;
    const dpr = finite(window.devicePixelRatio);
    const vv = window.visualViewport;
    const active = document.activeElement;
    const inputs = Array.from(document.querySelectorAll("textarea,input"))
      .filter(node => !panel.contains(node)).slice(0, 8);
    const sample = {
      sequence: ++sequence, time: new Date().toISOString(), elapsedMs: finite(performance.now()), reason,
      window: { innerWidth: window.innerWidth, innerHeight: window.innerHeight,
        outerWidth: window.outerWidth, outerHeight: window.outerHeight,
        devicePixelRatio: dpr, scrollX: window.scrollX, scrollY: window.scrollY },
      screen: { width: screen.width, height: screen.height, availWidth: screen.availWidth,
        availHeight: screen.availHeight },
      visualViewport: vv ? Object.fromEntries(["width", "height", "scale", "offsetLeft",
        "offsetTop", "pageLeft", "pageTop"].map(k => [k, finite(vv[k])])) : null,
      document: { visibilityState: document.visibilityState, hasFocus: document.hasFocus(),
        activeElement: active ? { tag: active.tagName, id: active.id || null } : null,
        root: geometryOf(document.documentElement), body: geometryOf(document.body) },
      canvas: c ? {
        ...c, buffer: { width: canvas.width, height: canvas.height },
        attributes: { width: canvas.getAttribute("width"), height: canvas.getAttribute("height") },
        bufferPerCssPixel: {
          x: r.width > 0 ? finite(canvas.width / r.width) : null,
          y: r.height > 0 ? finite(canvas.height / r.height) : null,
        },
        cssTimesDprEstimate: dpr !== null ? { width: r.width * dpr, height: r.height * dpr } : null,
        latestResizeObserver: latestObservedBoxes,
      } : null,
      textInputGeometry: inputs.map(geometryOf),
      textInputCount: document.querySelectorAll("textarea,input").length,
    };
    records.push(sample);
    if (records.length > maxRecords) { records.shift(); droppedRecords++; }
    publish();
  }
  function eventCapture(reason) {
    capture(reason);
    clearTimeout(settleTimer);
    settleTimer = setTimeout(() => capture(`${reason}:settled-250ms`), 250);
  }
  function startSampling() {
    clearInterval(samplingTimer);
    samplingWindowsStarted++;
    samplingDeadline = new Date(Date.now() + 180000).toISOString();
    const deadlineMs = Date.now() + 180000;
    samplingTimer = setInterval(() => {
      if (Date.now() >= deadlineMs) {
        clearInterval(samplingTimer);
        samplingTimer = null;
        capture("sampling-ended");
      } else capture("bounded-1Hz-sample");
    }, 1000);
    capture("sampling-started");
  }
  for (const event of ["resize", "focus", "blur", "pageshow", "pagehide"])
    window.addEventListener(event, () => eventCapture(`window:${event}`));
  for (const event of ["visibilitychange", "focusin", "focusout"])
    document.addEventListener(event, () => eventCapture(`document:${event}`));
  if (window.visualViewport) {
    for (const event of ["resize", "scroll"])
      window.visualViewport.addEventListener(event, () => eventCapture(`visualViewport:${event}`));
  }
  if (capabilities.resizeObserver && canvas) {
    const observer = new ResizeObserver(entries => {
      const entry = entries.find(e => e.target === canvas);
      if (!entry) return;
      latestObservedBoxes = {
        observedAt: new Date().toISOString(), contentRect: {
          width: finite(entry.contentRect.width), height: finite(entry.contentRect.height),
        }, contentBoxSize: boxList(entry.contentBoxSize),
        borderBoxSize: boxList(entry.borderBoxSize),
        devicePixelContentBoxSize: boxList(entry.devicePixelContentBoxSize),
      };
      eventCapture("canvas:ResizeObserver");
    });
    try { observer.observe(canvas, { box: "device-pixel-content-box" }); }
    catch (error) {
      errors.push(`device-pixel-content-box observation unavailable: ${String(error)}`);
      observer.observe(canvas);
    }
  }
  if (capabilities.mutationObserver && canvas) {
    new MutationObserver(mutations => eventCapture(`canvas:attributes:${[...new Set(mutations.map(m => m.attributeName))].join(",")}`))
      .observe(canvas, { attributes: true, attributeFilter: ["width", "height", "style", "class"] });
  }
  document.getElementById("viewport-boundary-snapshot").addEventListener("click", () => capture("manual-button"));
  document.getElementById("viewport-boundary-sampling").addEventListener("click", startSampling);
  document.getElementById("viewport-boundary-download").addEventListener("click", () => {
    capture("before-user-download");
    const url = URL.createObjectURL(new Blob([JSON.stringify(report(), null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `nvwa-viewport-boundary-${Date.now()}.json`;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  panel.addEventListener("toggle", publish);
  capture("collector-installed");
  startSampling();
  for (const delay of [250, 1000, 3000, 8000])
    setTimeout(() => capture(`startup:${delay}ms`), delay);
})();
