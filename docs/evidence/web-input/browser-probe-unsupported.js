// Throwaway loopback-only diagnostic. Never included in the shipped page.
// All trace text is the task-owned Chinese sentinel; no clipboard is read.
const panel = document.createElement('aside');
panel.style.cssText = 'position:fixed;bottom:4px;right:4px;z-index:20;background:#fff;color:#000;padding:6px;font:12px monospace';
panel.innerHTML = '<label>DOM control: <input id="ime-dom-control" aria-label="IME DOM control"></label> <button id="ime-commit-probe">Replay composition 女娲</button> <button id="ime-preedit-probe">Preview nv</button> <button id="ime-cancel-probe">Cancel composition</button> <button id="ime-batch-probe">Commit 女娲 + preview hao</button> <button id="ime-end-only">Commit only 女娲</button> <button id="ime-text-only">Input only 女娲</button><pre id="ime-debug-status"></pre>';
document.body.append(panel);
const output = panel.querySelector('pre');
const rows = [];
let captures = 0;
for (const type of ['compositionstart', 'compositionupdate', 'compositionend', 'beforeinput', 'input', 'keydown', 'keyup']) {
  document.addEventListener(type, event => {
    if (!['egui_text_agent', 'nvwa_text_input', 'ime-dom-control'].includes(event.target.id)) return;
    // Save event classes/counts only; never arbitrary user-entered text.
    captures++;
    rows.push(`${type} target=${event.target.id} composing=${event.isComposing ?? ''} inputType=${event.inputType ?? ''}`);
    rows.splice(0, Math.max(0, rows.length - 12));
  }, true);
}
for (const button of panel.querySelectorAll('button')) {
  button.addEventListener('pointerdown', event => event.preventDefault());
}
panel.querySelector('#ime-commit-probe').addEventListener('click', () => {
  const input = document.getElementById('nvwa_text_input') ?? document.getElementById('egui_text_agent');
  if (!input) throw new Error('No text agent installed');
  input.dispatchEvent(new CompositionEvent('compositionstart', {bubbles:true, data:''}));
  input.dispatchEvent(new CompositionEvent('compositionupdate', {bubbles:true, data:'nv'}));
  input.value = '女娲';
  input.dispatchEvent(new CompositionEvent('compositionend', {bubbles:true, data:'女娲'}));
  input.dispatchEvent(new InputEvent('input', {bubbles:true, data:'女娲', inputType:'insertFromComposition', isComposing:false}));
});
panel.querySelector('#ime-preedit-probe').addEventListener('click', () => {
  const input = document.getElementById('nvwa_text_input') ?? document.getElementById('egui_text_agent');
  if (!input) throw new Error('No text agent installed');
  input.dispatchEvent(new CompositionEvent('compositionstart', {bubbles:true, data:''}));
  input.value = 'nv';
  input.dispatchEvent(new CompositionEvent('compositionupdate', {bubbles:true, data:'nv'}));
});
panel.querySelector('#ime-cancel-probe').addEventListener('click', () => {
  const input = document.getElementById('nvwa_text_input') ?? document.getElementById('egui_text_agent');
  if (!input) throw new Error('No text agent installed');
  input.value = '';
  input.dispatchEvent(new CompositionEvent('compositionend', {bubbles:true, data:''}));
  input.dispatchEvent(new InputEvent('input', {bubbles:true, data:'', inputType:'insertFromComposition', isComposing:false}));
});
panel.querySelector('#ime-batch-probe').addEventListener('click', () => {
  const input = document.getElementById('nvwa_text_input') ?? document.getElementById('egui_text_agent');
  if (!input) throw new Error('No text agent installed');
  input.value = '女娲';
  input.dispatchEvent(new CompositionEvent('compositionend', {bubbles:true, data:'女娲'}));
  input.dispatchEvent(new InputEvent('input', {bubbles:true, data:'女娲', inputType:'insertFromComposition', isComposing:false}));
  input.dispatchEvent(new CompositionEvent('compositionstart', {bubbles:true, data:''}));
  input.value = 'hao';
  input.dispatchEvent(new CompositionEvent('compositionupdate', {bubbles:true, data:'hao'}));
});
panel.querySelector('#ime-end-only').addEventListener('click', () => {
  const input = document.getElementById('nvwa_text_input') ?? document.getElementById('egui_text_agent');
  if (!input) throw new Error('No text agent installed');
  input.dispatchEvent(new CompositionEvent('compositionstart', {bubbles:true, data:''}));
  input.dispatchEvent(new CompositionEvent('compositionend', {bubbles:true, data:'女娲'}));
});
panel.querySelector('#ime-text-only').addEventListener('click', () => {
  const input = document.getElementById('nvwa_text_input') ?? document.getElementById('egui_text_agent');
  if (!input) throw new Error('No text agent installed');
  input.dispatchEvent(new InputEvent('input', {bubbles:true, data:'女娲', inputType:'insertText', isComposing:false}));
});
setInterval(() => {
  const input = document.getElementById('nvwa_text_input') ?? document.getElementById('egui_text_agent');
  output.textContent = `active=${document.activeElement?.id} hidden=${input?.hidden} events=${captures}\n${rows.join('\n')}`;
}, 250);
