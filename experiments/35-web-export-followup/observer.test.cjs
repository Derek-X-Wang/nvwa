const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname + '/observer.js', 'utf8');
function setup(original, document) {
  const scope = {console: Object.fromEntries(['log','info','warn','error','debug'].map(k => [k, original])), document, addEventListener() {}};
  scope.top = scope;
  vm.runInNewContext(source, {window: scope, performance: {now: () => 4, timeOrigin: 1}, location: {href:'http://127.0.0.1:9206/case-1/index.html'}, navigator: {userAgent:'synthetic'}});
  return scope;
}
test('forwards exact arguments, receiver, return value and original exception', () => {
  const calls=[];
  const scope=setup(function(...args) { calls.push({receiver:this,args}); return 7; });
  const marker={x:1};
  assert.equal(scope.console.log('NVWA_EVIDENCE {}',marker),7);
  assert.equal(calls[0].receiver, scope.console);
  assert.equal(calls[0].args[1],marker);
  assert.equal(scope.nvwaExportFollowup.records.length,2);
  const failure=new Error('original failure');
  const other=setup(() => {throw failure;});
  assert.throws(() => other.console.error('actual failure'),error => error===failure);
});

function fakeDocument({initializationFailure, failWrite = () => false} = {}) {
  let writes = 0;
  let text = '';
  const children = [];
  const journal = {
    get textContent() { return text; },
    set textContent(value) {
      writes++;
      if (failWrite(writes)) throw new Error('journal write rejected');
      text = value;
    },
  };
  return {
    journal, children,
    createElement(tag) {
      if (initializationFailure === 'create') throw new Error('journal create rejected');
      assert.equal(tag, 'script');
      return journal;
    },
    body: {append(element) {
      if (initializationFailure === 'append') throw new Error('journal append rejected');
      children.push(element);
    }},
  };
}

test('supported DOM journal initializes once and publishes each bounded overflow while forwarding originals', () => {
  const document = fakeDocument();
  const calls = [];
  const scope = setup(function (...args) { calls.push({receiver: this, args}); return 9; }, document);
  assert.equal(document.children.length, 1);
  assert.equal(document.journal.type, 'application/json');
  assert.equal(document.journal.id, 'nvwa-export-followup-journal');
  assert.equal(JSON.parse(document.journal.textContent).records.length, 1);
  for (let i = 0; i < 100; i++) {
    const marker = {i};
    assert.equal(scope.console.error('x'.repeat(20000), marker), 9);
    const snapshot = JSON.parse(document.journal.textContent);
    assert.equal(snapshot.records.length, Math.min(64, i + 2));
    assert.equal(snapshot.dropped, Math.max(0, i + 2 - 64));
    assert.equal(calls[i].receiver, scope.console);
    assert.equal(calls[i].args[1], marker);
  }
  const snapshot = JSON.parse(document.journal.textContent);
  assert.equal(snapshot.dropped, 37);
  assert.equal(snapshot.records[1].message.length, 16384);
  assert.equal(snapshot.journalFailures.writes, 0);
  assert.equal(calls.length, 100);
});

test('DOM write failures preserve forwarding and subsequent successful update exposes failure and overflow counts', () => {
  const document = fakeDocument({failWrite: write => write === 1 || write >= 65 && write <= 101});
  let calls = 0;
  const scope = setup(() => ++calls, document);
  for (let i = 0; i < 100; i++) assert.equal(scope.console.error('error'), i + 1);
  assert.equal(calls, 100);
  assert.equal(scope.nvwaExportFollowup.records.length, 64);
  assert.equal(scope.nvwaExportFollowup.dropped, 37);
  assert.equal(scope.nvwaExportFollowup.journalFailures.writes, 38);
  assert.equal(scope.console.error('recovered write'), 101);
  const snapshot = JSON.parse(document.journal.textContent);
  assert.equal(snapshot.records.length, 64);
  assert.equal(snapshot.dropped, 38);
  assert.equal(snapshot.journalFailures.writes, 38);
  assert.equal(snapshot.journalFailures.lastError, 'Error: journal write rejected');
});

test('DOM initialization failure leaves original console behavior and bounded in-memory records intact', () => {
  for (const initializationFailure of ['create', 'append']) {
    const document = fakeDocument({initializationFailure});
    let calls = 0;
    const scope = setup(() => ++calls, document);
    for (let i = 0; i < 100; i++) assert.equal(scope.console.error('error'), i + 1);
    assert.equal(calls, 100);
    assert.equal(document.children.length, 0);
    assert.equal(scope.nvwaExportFollowup.records.length, 64);
    assert.equal(scope.nvwaExportFollowup.dropped, 37);
    assert.equal(scope.nvwaExportFollowup.journalFailures.initialization, 1);
    assert.equal(scope.nvwaExportFollowup.journalFailures.writes, 0);
  }
});

test('original console exception survives a failed DOM write', () => {
  const document = fakeDocument({failWrite: () => true});
  const failure = new Error('original console failure');
  let calls = 0;
  const scope = setup(() => {calls++; throw failure;}, document);
  assert.throws(() => scope.console.error('error'), error => error === failure);
  assert.equal(calls, 1);
  assert.equal(scope.nvwaExportFollowup.journalFailures.writes, 2);
});
test('bounded journal retains errors without swallowing or fabricating callback', () => {
  let calls=0;
  const scope=setup(() => {calls++;});
  for(let i=0;i<100;i++) scope.console.error('x'.repeat(20000));
  assert.equal(calls,100);
  assert.equal(scope.nvwaExportFollowup.records.length,64);
  assert.equal(scope.nvwaExportFollowup.dropped,37);
  assert.equal(scope.nvwaExportFollowup.records[1].message.length,16384);
  assert.equal(scope.nvwaExportFollowup.records.some(r=>r.message?.includes('NVWA_EVIDENCE')),false);
});
