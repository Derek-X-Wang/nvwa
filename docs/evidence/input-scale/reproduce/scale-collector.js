// Passive, task-owned diagnostic only. Never shipped. No event dispatch,
// input values, clipboard access, DOM geometry changes, or browser API overrides.
(() => {
  if (globalThis.nvwaScaleProbe) throw new Error('Nvwa scale probe already installed');
  const rows = [];
  const listeners = [];
  const output = document.createElement('pre');
  output.id = 'nvwa-scale-probe-json';
  output.hidden = true;
  document.body.append(output);
  const metadata = {
    schema:'nvwa-scale-boundary-v1',url:location.href,userAgent:navigator.userAgent,
    case:new URLSearchParams(location.search).get('scale_case'),
    source:JSON.parse(document.getElementById('nvwa-scale-source')?.textContent ?? 'null')
  };
  let serial = 0;
  let pendingOutput = false;
  const publish = () => {
    if (pendingOutput) return;
    pendingOutput = true;
    requestAnimationFrame(() => {
      pendingOutput = false;
      output.textContent = JSON.stringify({...metadata,rows});
    });
  };
  const rect = element => {
    if (!element) return null;
    const r = element.getBoundingClientRect();
    return {x:r.x, y:r.y, width:r.width, height:r.height};
  };
  const geometry = () => {
    const canvas = document.getElementById('nvwa');
    const input = document.getElementById('nvwa_text_input');
    const css = canvas ? getComputedStyle(canvas) : null;
    const inputCss = input ? getComputedStyle(input) : null;
    const v = window.visualViewport;
    return {
      dpr: window.devicePixelRatio,
      viewport: {width:innerWidth, height:innerHeight,
        visual:v ? {width:v.width,height:v.height,scale:v.scale,offsetLeft:v.offsetLeft,offsetTop:v.offsetTop}:null},
      canvas:canvas ? {rect:rect(canvas), client:{width:canvas.clientWidth,height:canvas.clientHeight},
        backing:{width:canvas.width,height:canvas.height},
        css:{width:css.width,height:css.height,transform:css.transform}}:null,
      caret:input ? {rect:rect(input),hidden:input.hidden,
        css:{left:inputCss.left,top:inputCss.top,width:inputCss.width,height:inputCss.height}}:null,
      activeElement:document.activeElement?.id ?? null,
      documentFocused:document.hasFocus()
    };
  };
  const record = (kind, data={}) => {
    const row={index:serial++,timeMs:performance.now(),kind,...data,geometry:geometry()};
    rows.push(row);
    if (rows.length > 800) rows.shift();
    publish();
    return row;
  };
  const listen = (target,type,fn) => {
    target.addEventListener(type,fn,{capture:true,passive:true});
    listeners.push(() => target.removeEventListener(type,fn,true));
  };
  for (const type of ['pointerdown','pointermove','pointerup','pointercancel']) {
    listen(document,type,event => {
      if (event.target?.id !== 'nvwa') return;
      // Keep drag frames and click endpoints only, with real trusted status.
      if (type==='pointermove' && !event.buttons) return;
      record(type,{target:event.target.id,trusted:event.isTrusted,pointerId:event.pointerId,
        button:event.button,buttons:event.buttons,
        client:{x:event.clientX,y:event.clientY},offset:{x:event.offsetX,y:event.offsetY}});
      if (type !== 'pointermove') setTimeout(() => record('settled',{after:type}),250);
    });
  }
  for (const type of ['focusin','focusout','beforeinput','input','compositionstart','compositionend']) {
    listen(document,type,event => {
      if (!['nvwa','nvwa_text_input'].includes(event.target?.id)) return;
      record(type,{target:event.target.id,trusted:event.isTrusted,
        inputType:event.inputType ?? null,composing:event.isComposing ?? null});
      setTimeout(() => record('settled',{after:type}),250);
    });
  }
  listen(window,'resize',() => record('window-resize'));
  if (window.visualViewport) for (const type of ['resize','scroll']) {
    listen(window.visualViewport,type,() => record(`visual-${type}`));
  }
  let lastGeometry = '';
  const observer = new MutationObserver(records => {
    if (records.some(r => ['nvwa','nvwa_text_input'].includes(r.target.id))) {
      const current = JSON.stringify(geometry());
      if (current !== lastGeometry) {lastGeometry=current;record('dom-geometry-change');}
    }
  });
  observer.observe(document.documentElement,{subtree:true,attributes:true,attributeFilter:['width','height','style','hidden']});
  globalThis.nvwaScaleProbe = Object.freeze({
    mark:label => record('mark',{label}),
    // Screenshot-derived CSS targets / source identifiers are annotations,
    // never measurements inferred from hidden DOM controls.
    observe:observation => record('observation',{observation:JSON.parse(JSON.stringify(observation))}),
    snapshot:geometry,
    export:() => ({...metadata,rows:JSON.parse(JSON.stringify(rows))}),
    stop:() => {listeners.forEach(remove=>remove());observer.disconnect();return record('stopped');}
  });
  record('installed');
  setTimeout(() => record('settled',{after:'installed'}),1000);
})();
