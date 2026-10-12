// Executes the actual collector in an offline DOM-shaped semantic control.
// No browser, GPU, UI input, or current capture is fabricated.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {randomUUID} = require('node:crypto');

const elements = new Map();
const element = (id = '') => {
  const listeners = new Map();
  const value = {id, hidden: false, clientWidth: 1100, clientHeight: 640,
    width: 2200, height: 1280, textContent: '',
    getBoundingClientRect: () => ({x: 0, y: 0, width: 1100, height: 640}),
    addEventListener: (type, callback, options) => {
      const entries = listeners.get(type) ?? [];
      entries.push({callback, options}); listeners.set(type, entries);
    },
    removeEventListener: (type, callback) => listeners.set(type,
      (listeners.get(type) ?? []).filter(entry => entry.callback !== callback)),
    emit: (type, target = value) => {
      for (const entry of listeners.get(type) ?? []) entry.callback({target, isTrusted: true});
    },
    append: child => {if (child.id) elements.set(child.id, child);},
    click: () => {}, remove: () => {}};
  if (id) elements.set(id, value);
  return value;
};
const parent = element('nvwa-fixed-parent');
const canvas = element('nvwa'); canvas.parentElement = parent;
const input = element('nvwa_text_input');
const source = element('nvwa-fixed-css-source'); source.textContent = JSON.stringify({offlineControlOnly: true});
const exportButton = element('nvwa-fixed-css-export');
element('nvwa-fixed-css-stop');
const windowControl = element();
windowControl.devicePixelRatio = 2;
const documentControl = element();
documentControl.body = element();
documentControl.documentElement = element();
documentControl.activeElement = canvas;
let documentFocused = true;
documentControl.hasFocus = () => documentFocused;
documentControl.getElementById = id => elements.get(id) ?? null;
documentControl.createElement = () => element();
let tick = 0;
const context = vm.createContext({window: windowControl, document: documentControl,
  innerWidth: 1200, innerHeight: 700, scrollX: 0, scrollY: 0,
  location: {href: 'http://offline.invalid/control-only'}, navigator: {userAgent: 'offline-semantic-control'},
  crypto: {randomUUID}, performance: {now: () => ++tick},
  getComputedStyle: () => ({width: '1100px', height: '640px', transform: 'none', left: '0px', top: '0px'}),
  MutationObserver: class {observe() {} disconnect() {}},
  setInterval: () => 1, clearInterval: () => {}, setTimeout: () => 2, clearTimeout: () => {},
  Blob, URL: {createObjectURL: () => 'blob:offline-control', revokeObjectURL: () => {}}});
vm.runInContext(fs.readFileSync(__dirname + '/collector.js', 'utf8'), context);
const packet = () => {
  exportButton.emit('click');
  return JSON.parse(elements.get('nvwa-fixed-css-json').textContent);
};

// A capture-phase window listener sees descendant focus/blur events. The actual
// callback must filter their target, preserving the separate focusin/out records.
windowControl.emit('blur', canvas);
windowControl.emit('focus', input);
let rows = packet().rows;
assert.equal(rows.filter(row => row.kind === 'window-blur').length, 0,
  'descendant canvas blur was falsely labeled window-blur');
assert.equal(rows.filter(row => row.kind === 'window-focus').length, 0,
  'descendant textarea focus was falsely labeled window-focus');

documentFocused = false; windowControl.emit('blur');
documentFocused = true; windowControl.emit('focus');
rows = packet().rows;
assert.equal(rows.filter(row => row.kind === 'window-blur').length, 1,
  'actual window blur must remain observed');
assert.equal(rows.find(row => row.kind === 'window-blur').geometry.documentFocused, false);
assert.equal(rows.filter(row => row.kind === 'window-focus').length, 1,
  'actual window focus must remain observed');
console.log('PASS actual collector semantic control: descendant focus/blur ignored; window focus/blur retained');
