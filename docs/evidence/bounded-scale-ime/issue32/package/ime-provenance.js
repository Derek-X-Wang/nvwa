// Diagnostic realm hook, installed synchronously before the production module.
(() => {
  'use strict';
  if (window.nvwaImeProvenance) throw new Error('IME provenance collector already installed');
  const script = document.currentScript;
  const pageKind = script?.dataset.pageKind;
  if (!['nvwa', 'plain-textarea', 'synthetic-selftest'].includes(pageKind)) throw new Error('Unknown diagnostic page kind');
  const composition = new Set(['compositionstart', 'compositionupdate', 'compositionend']);
  const relevant = new Set(['nvwa_text_input', 'egui_text_agent', 'nvwa', 'ime-control']);
  const originalDescriptor = Object.getOwnPropertyDescriptor(EventTarget.prototype, 'dispatchEvent');
  const originalDispatch = originalDescriptor.value;
  const installedAt = performance.now();
  let rows = [], eventIds = new WeakMap(), activeDispatch = new WeakMap();
  let running = false, sequence = 0, nextEvent = 0, nextDispatch = 0, dropped = 0, errors = 0, run = 0;
  let startedAt = null, stoppedAt = null, runId = null;
  let productionModuleStartAt = null, hookIntactBeforeModule = null;
  let status;
  const identity = element => relevant.has(element?.id) ? element.id : element?.tagName?.toLowerCase() || null;
  const eventId = event => {
    if (!eventIds.has(event)) eventIds.set(event, `e${++nextEvent}`);
    return eventIds.get(event);
  };
  const safely = action => { try { return action(); } catch (_) { errors++; return null; } };
  const eventMeta = event => ({
    eventId:eventId(event), eventType:event.type, trusted:event.isTrusted,
    constructorName:Object.getPrototypeOf(event)?.constructor?.name || null,
    dataLength:typeof event.data === 'string' ? [...event.data].length : null,
  });
  const snapshot = () => ({
    active:identity(document.activeElement), pageFocused:document.hasFocus(), visibility:document.visibilityState,
    dpr:window.devicePixelRatio, visualScale:window.visualViewport?.scale ?? null,
    proxyCount:document.querySelectorAll('#nvwa_text_input').length,
    proxyHidden:document.getElementById('nvwa_text_input')?.hidden ?? null,
    hookIntact:EventTarget.prototype.dispatchEvent === wrappedDispatch,
  });
  function append(row) {
    if (!running) return;
    if (rows.length >= 4000) { dropped++; return; }
    rows.push({sequence:++sequence, timeMs:performance.now(), ...row, ...snapshot()});
    if (status) status.textContent = `Recording ${pageKind}: ${rows.length} rows; dropped ${dropped}`;
  }
  function wrappedDispatch(...args) {
    const event = args[0];
    let dispatchId = null, previous = null;
    // No constructor wrapping or argument replacement. Inspection failures are isolated.
    safely(() => {
      if (!running || !composition.has(event?.type)) return;
      dispatchId = `d${++nextDispatch}`;
      previous = activeDispatch.get(event) ?? null;
      activeDispatch.set(event, dispatchId);
      append({type:'dispatch-start', dispatchId, target:identity(this), ...eventMeta(event),
        stack:new Error('composition dispatch witness').stack || null});
    });
    try {
      const result = Reflect.apply(originalDispatch, this, args);
      if (dispatchId) safely(() => append({type:'dispatch-return', dispatchId, eventId:eventId(event), result}));
      return result;
    } catch (error) {
      // Preserve the exact thrown value; do not serialize its potentially sensitive message.
      if (dispatchId) safely(() => append({type:'dispatch-throw', dispatchId, eventId:eventId(event)}));
      throw error;
    } finally {
      if (dispatchId) safely(() => {
        if (previous) activeDispatch.set(event, previous); else activeDispatch.delete(event);
      });
    }
  }
  Object.defineProperty(EventTarget.prototype, 'dispatchEvent', {...originalDescriptor, value:wrappedDispatch});
  for (const type of [...composition, 'beforeinput', 'input', 'keydown', 'keyup', 'focusin', 'focusout']) {
    document.addEventListener(type, event => safely(() => {
      if (!running || !relevant.has(event.target?.id)) return;
      const dispatchId = activeDispatch.get(event) ?? null;
      const row = {type:'observed-event', target:identity(event.target), ...eventMeta(event), dispatchId,
        provenance:composition.has(type) && dispatchId ? 'WITNESSED_REALM_DISPATCH' : 'UNKNOWN'};
      if ('inputType' in event) row.inputType = event.inputType;
      if ('isComposing' in event) row.composing = event.isComposing;
      if ('key' in event) {
        row.key = ['Space','Enter','Escape','Tab','Backspace','Delete','Shift','Control','Alt','Meta'].includes(event.key) ? event.key : event.key === ' ' ? 'Space' : 'printable-or-other';
        row.keyCode229 = event.keyCode === 229;
      }
      append(row);
    }), {capture:true, passive:true});
  }
  for (const [target, type] of [[window,'focus'],[window,'blur'],[document,'visibilitychange']]) {
    target.addEventListener(type, event => safely(() => append({type:'page-state', eventType:type, trusted:event.isTrusted})), {capture:true, passive:true});
  }
  const exported = () => ({schema:1, kind:'ime-event-provenance', pageKind,
    synthetic:pageKind === 'synthetic-selftest', run, runId, running, startedAt, stoppedAt,
    timeOrigin:performance.timeOrigin, productionModuleStartAt, hookIntactBeforeModule,
    browser:navigator.userAgent, hookInstalledAt:installedAt,
    earlyInstallation:script?.dataset.early === 'before-production-module',
    hookIntactAtExport:EventTarget.prototype.dispatchEvent === wrappedDispatch,
    dropped, instrumentationErrors:errors, rows});
  function start() {
    if (running) return; // Start is idempotent; Reset alone discards a previous case.
    if (rows.length) { status.textContent = 'Reset before starting another case; export the stopped case first.'; return; }
    running = true; startedAt = performance.now(); stoppedAt = null; run++; runId = crypto.randomUUID();
    safely(() => append({type:'checkpoint', label:'start'}));
  }
  function stop() {
    if (!running) return;
    safely(() => append({type:'checkpoint', label:'stop'}));
    running = false; stoppedAt = performance.now();
    status.textContent = `Stopped ${pageKind}: ${rows.length} rows; export before Reset.`;
  }
  function reset() {
    if (running) { status.textContent = 'Stop and export before Reset.'; return; }
    rows = []; eventIds = new WeakMap(); activeDispatch = new WeakMap();
    sequence = 0; nextEvent = 0; nextDispatch = 0; dropped = 0; errors = 0; startedAt = null; stoppedAt = null;
    status.textContent = `Ready ${pageKind}. Reset clears trace only; it does not change input.`;
  }
  function exportRaw() {
    if (running) { status.textContent = 'Stop before exporting the exact case.'; return; }
    const blob = new Blob([JSON.stringify(exported(), null, 2) + '\n'], {type:'application/json'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = `nvwa-ime32-${pageKind}-run${run}.json`;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function syntheticSelftest() {
    if (pageKind !== 'synthetic-selftest' || !running) return;
    const target = document.getElementById('ime-control');
    for (const type of composition) {
      target.dispatchEvent(new CompositionEvent(type, {data:'ab', bubbles:true, cancelable:true}));
    }
  }
  function mount() {
    const panel = document.createElement('section');
    panel.id = 'ime-provenance-controls';
    panel.style.cssText = 'position:fixed;bottom:8px;left:8px;z-index:20;max-width:600px;background:#fff;color:#111;padding:8px;font:13px system-ui;border:2px solid #465;';
    const label = document.createElement('strong');
    label.textContent = pageKind === 'synthetic-selftest' ? 'SYNTHETIC SELFTEST — never physical/product evidence' : `Issue32 diagnostic — ${pageKind}`;
    panel.append(label, document.createElement('br'));
    for (const [label, action] of [['Start case', start],['Stop case', stop],['Reset trace', reset],['Export exact raw JSON', exportRaw]]) {
      const button = document.createElement('button'); button.textContent = label; button.addEventListener('click', action); panel.append(button);
    }
    if (pageKind === 'synthetic-selftest') {
      const button = document.createElement('button'); button.textContent = 'Run known local SYNTHETIC dispatch'; button.addEventListener('click', syntheticSelftest); panel.append(button);
    }
    status = document.createElement('p'); status.style.margin = '4px 0 0'; panel.append(status); document.body.append(panel); reset();
  }
  // Export is read-only; all case actions are wired to visible owned buttons.
  window.nvwaImeProvenance = {export:() => structuredClone(exported()),
    noteProductionModuleStart() {
      if (pageKind !== 'nvwa' || productionModuleStartAt !== null) throw new Error('Unexpected module marker');
      productionModuleStartAt = performance.now();
      hookIntactBeforeModule = EventTarget.prototype.dispatchEvent === wrappedDispatch;
    },
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, {once:true}); else mount();
})();
