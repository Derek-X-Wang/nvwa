// Passive, task-local observer. No focus, synthetic events, keys or clipboard reads.
(() => {
  if (window.nvwaRecovery) throw new Error('Nvwa recovery capture already installed');
  const rows = [];
  const listeners = [];
  let sentinels = {};
  let running = false;
  let sequence = 0;
  let dropped = 0;
  const output = document.createElement('pre');
  output.id = 'nvwa-recovery-json';
  output.hidden = true;
  document.body.append(output);
  const exported = () => ({schema:1,kind:'passive-browser-capture',syntheticDispatch:false,
    browser:navigator.userAgent,startedAt:performance.timeOrigin,
    sentinelLabels:Object.keys(sentinels),dropped,rows});
  const identity = element => element?.id || element?.tagName?.toLowerCase() || null;
  const rect = element => {
    if (!element) return null;
    const r = element.getBoundingClientRect();
    return {x:r.x, y:r.y, width:r.width, height:r.height};
  };
  const snapshot = () => {
    const proxy = document.getElementById('nvwa_text_input');
    const canvas = document.getElementById('nvwa');
    return {
      pageFocused:document.hasFocus(), visibility:document.visibilityState,
      active:identity(document.activeElement), proxyCount:document.querySelectorAll('#nvwa_text_input').length,
      proxyHidden:proxy?.hidden ?? null, proxyRect:rect(proxy), canvasRect:rect(canvas),
      canvasBacking:canvas ? {width:canvas.width,height:canvas.height}:null,
      dpr:window.devicePixelRatio, visualScale:window.visualViewport?.scale ?? null,
      viewport:{width:innerWidth,height:innerHeight},
    };
  };
  function append(row) {
    if (!running) return;
    if (rows.length >= 2000) { dropped++; output.textContent = JSON.stringify(exported()); return; }
    rows.push({sequence:++sequence,timeMs:performance.now(),...row,...snapshot()});
    output.textContent = JSON.stringify(exported());
  }
  function listen(target, type, handler) {
    target.addEventListener(type, handler, {capture:true,passive:true});
    listeners.push([target,type,handler]);
  }
  for (const type of ['focus','blur','visibilitychange','resize']) {
    const target = type === 'visibilitychange' ? document : window;
    listen(target,type,event => append({type,target:identity(event.target),trusted:event.isTrusted}));
  }
  for (const type of ['compositionstart','compositionupdate','compositionend','beforeinput','input','keydown','keyup','pointerdown','focusin','focusout']) {
    listen(document,type,event => {
      const target = identity(event.target);
      if (!['nvwa_text_input','nvwa','egui_text_agent'].includes(target)) return;
      const data = typeof event.data === 'string' ? event.data : null;
      const row = {type,target,trusted:event.isTrusted};
      if (data !== null) {
        row.dataLength = [...data].length;
        row.sentinelMatches = Object.entries(sentinels).filter(([,value]) => value === data).map(([name]) => name);
      }
      if ('inputType' in event) row.inputType = event.inputType;
      if ('isComposing' in event) row.composing = event.isComposing;
      if ('key' in event) {
        row.key = ['Tab','Enter','Escape','Backspace','Delete','ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End','Shift','Control','Alt','Meta'].includes(event.key) ? event.key : 'printable-or-other';
        row.keyCode229 = event.keyCode === 229;
        row.modifiers = {shift:event.shiftKey,ctrl:event.ctrlKey,alt:event.altKey,meta:event.metaKey};
      }
      append(row);
    });
  }
  window.nvwaRecovery = {
    start(expected = {}) {
      if (!Object.values(expected).every(value => typeof value === 'string')) throw new Error('Sentinels must be strings');
      sentinels = {...expected}; rows.length = 0; sequence = 0; dropped = 0; running = true;
      append({type:'checkpoint',label:'start'});
    },
    mark(label) { append({type:'checkpoint',label}); },
    export() {
      return structuredClone(exported());
    },
    stop() { append({type:'checkpoint',label:'stop'}); running = false; },
    remove() {
      running = false;
      for (const [target,type,handler] of listeners) target.removeEventListener(type,handler,true);
      output.remove();
      delete window.nvwaRecovery;
    },
  };
  // Root reads #nvwa-recovery-json; no mutating browser evaluate is needed.
  window.nvwaRecovery.start();
})();
