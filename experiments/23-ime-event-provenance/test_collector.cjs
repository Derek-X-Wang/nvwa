// Node VM controls for the actual collector file. A small DOM harness is NOT a browser or IME run.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');
const nativeDescriptor = Object.getOwnPropertyDescriptor(EventTarget.prototype, 'dispatchEvent');
const original = nativeDescriptor.value;
const source = fs.readFileSync(__dirname + '/collector.js', 'utf8');
let forwarded;
let deliberateThrow = null;
function forwardingSpy(...args) {
  forwarded = {receiver:this, args};
  if (deliberateThrow) throw deliberateThrow;
  return Reflect.apply(original, this, args);
}
Object.defineProperty(EventTarget.prototype, 'dispatchEvent', {...nativeDescriptor, value:forwardingSpy});
class Element extends EventTarget {
  constructor(tag) { super(); this.tagName=tag.toUpperCase(); this.children=[]; this.id=''; this.hidden=false; this.style={}; this.textContent=''; }
  append(...children) { this.children.push(...children); }
  click() { this.dispatchEvent(new Event('click')); }
  remove() {}
}
const handlers = new Map();
const textarea = new Element('textarea'); textarea.id='ime-control';
const body = new Element('body'); body.append(textarea);
const document = {
  currentScript:{dataset:{pageKind:'synthetic-selftest',early:'before-production-module'}},
  readyState:'complete',body,activeElement:textarea,visibilityState:'visible',
  hasFocus:() => true, querySelectorAll:() => [],
  getElementById:id => id==='ime-control' ? textarea : null,
  createElement:tag => new Element(tag),
  addEventListener(type, callback) { handlers.set(type, callback); textarea.addEventListener(type, callback); },
};
const window = new EventTarget(); window.devicePixelRatio=2;
class CompositionEvent extends Event {
  constructor(type, options={}) { super(type,options); this.data=options.data??''; }
}
try {
  vm.runInNewContext(source, {window,document,EventTarget,CompositionEvent,performance,crypto,
    navigator:{userAgent:'NODE-DOM-HARNESS-NOT-PHYSICAL'},structuredClone,Blob,URL,setTimeout});
  const buttons = body.children.flatMap(node => node.children).filter(node => node.tagName==='BUTTON');
  const button = text => buttons.find(item => item.textContent === text);
  button('Start case').click();
  button('Run known local SYNTHETIC dispatch').click();
  let capture=window.nvwaImeProvenance.export();
  assert.equal(capture.synthetic,true);
  assert.equal(capture.rows.filter(row => row.type==='dispatch-start').length,3);
  for (const observed of capture.rows.filter(row => row.type==='observed-event')) {
    assert.equal(observed.provenance,'WITNESSED_REALM_DISPATCH');
    assert.equal(observed.dataLength,2); assert.equal(observed.trusted,false);
    const start=capture.rows.find(row => row.type==='dispatch-start'&&row.dispatchId===observed.dispatchId);
    assert.equal(start.eventId,observed.eventId); assert.ok(start.stack.includes('syntheticSelftest'));
    assert.ok(!('data' in observed));
  }
  button('Stop case').click();
  capture=window.nvwaImeProvenance.export();
  assert.equal(capture.running,false);assert.equal(capture.rows.at(-1).label,'stop');
  assert.equal(capture.instrumentationErrors,0);assert.equal(capture.dropped,0);
  const before = capture.rows.length;
  const event = new CompositionEvent('compositionend',{data:'ab',cancelable:true});
  const extra = {opaque:true};
  textarea.addEventListener('compositionend',e => e.preventDefault());
  assert.equal(textarea.dispatchEvent(event,extra),false);
  assert.equal(forwarded.receiver,textarea);assert.equal(forwarded.args.length,2);
  assert.equal(forwarded.args[0],event);assert.equal(forwarded.args[1],extra);
  assert.equal(window.nvwaImeProvenance.export().rows.length,before);
  const sentinel = {throwIdentity:'owned-fixture'}; deliberateThrow=sentinel;
  assert.throws(() => textarea.dispatchEvent(event), thrown => thrown===sentinel);
  deliberateThrow=null;
  const wrapped = EventTarget.prototype.dispatchEvent;
  assert.throws(() => Reflect.apply(wrapped,{},[event]), TypeError);
  button('Reset trace').click(); button('Start case').click();
  const second=window.nvwaImeProvenance.export();assert.notEqual(second.runId,capture.runId);
  assert.equal(second.rows.length,1);
  // Bypass the replaced prototype with the saved native method: absent witness stays UNKNOWN.
  Reflect.apply(original,textarea,[new CompositionEvent('compositionend',{data:'ab'})]);
  const unknown=window.nvwaImeProvenance.export().rows.find(row => row.type==='observed-event');
  assert.equal(unknown.provenance,'UNKNOWN');assert.equal(unknown.dispatchId,null);
  button('Reset trace').click(); // Active-case reset must not silently discard rows.
  assert.equal(window.nvwaImeProvenance.export().rows.length,2);
  button('Stop case').click();
  // Save both known and UNKNOWN controls privately when requested.
  if (process.argv[2]) {
    fs.mkdirSync(process.argv[2],{recursive:true});
    fs.writeFileSync(process.argv[2]+'/collector-selftest.json',JSON.stringify(capture,null,2)+'\n');
    fs.writeFileSync(process.argv[2]+'/collector-unwitnessed.json',JSON.stringify(window.nvwaImeProvenance.export(),null,2)+'\n');
  }
  console.log('PASS — actual collector Node harness: matching event IDs/callstacks, false native return, exact this/args/throw, stop/reset/UUID boundaries, bypass UNKNOWN. Browser and physical IME NOT-RUN.');
} finally {
  Object.defineProperty(EventTarget.prototype,'dispatchEvent',nativeDescriptor);
}
