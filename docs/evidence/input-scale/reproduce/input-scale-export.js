(() => {
 const bar=document.createElement('div');
 bar.style.cssText='position:fixed;right:8px;bottom:8px;z-index:4;background:#172331;color:white;padding:4px;font:12px system-ui;pointer-events:auto';
 const label=document.createElement('span');
 const button=document.createElement('button');
 button.textContent='Export observed input/scale JSON';
 button.addEventListener('click',()=>{
  const capture={rootCase:new URLSearchParams(location.search).get('scale_case'),sourceHead:'93c77d5d8409a6b142c1aeaa07a50b594bcecb29',recovery:JSON.parse(document.getElementById('nvwa-recovery-json').textContent),scale:JSON.parse(document.getElementById('nvwa-scale-probe-json').textContent)};
  const blob=new Blob([JSON.stringify(capture,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const link=document.createElement('a');
  link.href=url;link.download='nvwa-observed-'+capture.rootCase+'-'+Math.round(performance.now())+'.json';
  document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
 });
 bar.append(label,button);document.body.append(bar);
 const refresh=()=>{label.textContent='Observed DPR '+devicePixelRatio+' · CSS '+innerWidth+'×'+innerHeight+'  ';};
 addEventListener('resize',refresh,{passive:true});refresh();
})();
