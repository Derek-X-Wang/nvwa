// Throwaway passive geometry observer. No input text/clipboard reads, event
// dispatch, focus calls, canvas sizing, or browser API overrides.
(() => {
  const limit = 1200;
  const rows = [];
  let serial = 0;
  let dropped = 0;
  let stopped = false;
  const removers = [];
  const timers = new Set();
  const metadata = {
    schema: 'nvwa-fixed-css-dpr-v1',
    sessionId: crypto.randomUUID(),
    url: location.href,
    userAgent: navigator.userAgent,
    source: JSON.parse(document.getElementById('nvwa-fixed-css-source').textContent),
    collector: {limit, pointerCoverage: 'all document targets; drag moves only',
      timerDelayMs: 250, textRead: false, viewportAndCanvasSeparate: true}
  };
  const output = document.createElement('pre');
  output.id = 'nvwa-fixed-css-json';
  output.hidden = true;
  document.body.append(output);
  const target = element => ['nvwa', 'nvwa_text_input', 'nvwa-fixed-css-export', 'nvwa-fixed-css-stop'].includes(element?.id)
    ? element.id : 'other';
  const rect = element => {
    if (!element) return null;
    const r = element.getBoundingClientRect();
    return {x: r.x, y: r.y, width: r.width, height: r.height};
  };
  const geometry = () => {
    const canvas = document.getElementById('nvwa');
    const input = document.getElementById('nvwa_text_input');
    const css = getComputedStyle(canvas);
    const inputCss = input ? getComputedStyle(input) : null;
    const visual = window.visualViewport;
    return {
      dpr: window.devicePixelRatio,
      viewport: {width: innerWidth, height: innerHeight,
        visual: visual ? {width: visual.width, height: visual.height, scale: visual.scale,
          offsetLeft: visual.offsetLeft, offsetTop: visual.offsetTop} : null},
      fixedParent: rect(document.getElementById('nvwa-fixed-parent')),
      parent: rect(canvas.parentElement),
      parentTransform: getComputedStyle(canvas.parentElement).transform,
      scroll: {x: scrollX, y: scrollY},
      canvas: {rect: rect(canvas), client: {width: canvas.clientWidth, height: canvas.clientHeight},
        backing: {width: canvas.width, height: canvas.height},
        css: {width: css.width, height: css.height, transform: css.transform}},
      caret: input ? {rect: rect(input), hidden: input.hidden,
        css: {left: inputCss.left, top: inputCss.top, width: inputCss.width, height: inputCss.height}} : null,
      activeElement: document.activeElement === document.body ? '' : target(document.activeElement),
      documentFocused: document.hasFocus()
    };
  };
  const packet = () => ({...metadata,
    inventory: {limit, recorded: serial, retained: rows.length, dropped,
      firstIndex: rows[0]?.index ?? null, lastIndex: rows.at(-1)?.index ?? null}, stopped, rows});
  const record = (kind, data = {}) => {
    const row = {index: serial++, timeMs: performance.now(), kind, ...data, geometry: geometry()};
    rows.push(row);
    if (rows.length > limit) { rows.shift(); dropped++; }
    return row;
  };
  const listen = (element, type, callback) => {
    element.addEventListener(type, callback, {capture: true, passive: true});
    removers.push(() => element.removeEventListener(type, callback, true));
  };
  for (const type of ['pointerdown', 'pointermove', 'pointerup', 'pointercancel']) {
    listen(document, type, event => {
      if (type === 'pointermove' && !event.buttons) return;
      const row = record(type, {target: target(event.target), trusted: event.isTrusted,
        pointerId: event.pointerId, button: event.button, buttons: event.buttons,
        client: {x: event.clientX, y: event.clientY}});
      if (type !== 'pointermove') {
        const timer = setTimeout(() => {
          timers.delete(timer);
          record('settled', {after: type, originIndex: row.index,
            originPointerId: row.pointerId, originTimeMs: row.timeMs});
        }, 250);
        timers.add(timer);
      }
    });
  }
  for (const type of ['focusin', 'focusout']) listen(document, type, event =>
    record(type, {target: target(event.target), trusted: event.isTrusted}));
  listen(window, 'blur', event => { if (event.target === window) record('window-blur'); });
  listen(window, 'focus', event => { if (event.target === window) record('window-focus'); });
  listen(window, 'resize', () => record('window-resize'));
  if (window.visualViewport) for (const type of ['resize', 'scroll'])
    listen(window.visualViewport, type, () => record(`visual-${type}`));
  let lastDpr = window.devicePixelRatio;
  const dprTimer = setInterval(() => {
    if (window.devicePixelRatio !== lastDpr) {
      lastDpr = window.devicePixelRatio; record('dpr-change');
    }
  }, 100);
  let lastGeometry = '';
  const observer = new MutationObserver(changes => {
    if (!changes.some(change => ['nvwa', 'nvwa_text_input'].includes(change.target.id))) return;
    const signature = JSON.stringify(geometry());
    if (signature !== lastGeometry) { lastGeometry = signature; record('dom-geometry-change'); }
  });
  observer.observe(document.documentElement, {subtree: true, attributes: true,
    attributeFilter: ['style', 'width', 'height', 'hidden']});
  // Explicit user action publishes a synchronous snapshot. The external button
  // changes focus after the tested click interval and does not cover the canvas.
  const exportCapture = (event, final = false) => {
    if (!event.isTrusted) return;
    if (!stopped) record('user-export', {trusted: true, final});
    if (final && !stopped) {
      removers.forEach(remove => remove());
      timers.forEach(timer => clearTimeout(timer));
      timers.clear(); clearInterval(dprTimer); observer.disconnect();
      stopped = true;
      record('stopped', {trusted: true, reason: 'user-stop-export'});
    }
    const serialized = JSON.stringify(packet(), null, 2);
    output.textContent = serialized;
    const url = URL.createObjectURL(new Blob([serialized], {type: 'application/json'}));
    const link = document.createElement('a');
    link.href = url;
    link.download = `nvwa-fixed-css-${serial}.json`;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  document.getElementById('nvwa-fixed-css-export').addEventListener('click', event => exportCapture(event));
  document.getElementById('nvwa-fixed-css-stop').addEventListener('click', event => exportCapture(event, true));
  record('installed');
})();
