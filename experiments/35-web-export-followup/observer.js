// Observation only: no render, editor, anchor, Blob, URL, or timer replacement.
(function install(scope) {
  'use strict';
  const records = [];
  let dropped = 0;
  let journal;
  const journalFailures = {initialization: 0, writes: 0, lastError: null};
  try {
    const candidate = scope.document?.createElement('script');
    if (candidate) {
      candidate.type = 'application/json';
      candidate.id = 'nvwa-export-followup-journal';
      scope.document.body.append(candidate);
      journal = candidate;
    }
  } catch (error) {
    journalFailures.initialization++;
    journalFailures.lastError = String(error).slice(0, 4096);
  }
  function publishJournal() {
    if (!journal) return;
    try {
      journal.textContent = JSON.stringify({records, dropped, journalFailures});
    } catch (error) {
      journalFailures.writes++;
      journalFailures.lastError = String(error).slice(0, 4096);
    }
  }
  function record(kind, data) {
    if (records.length >= 64) {
      dropped++;
    } else {
      records.push({kind, utc: new Date().toISOString(), navigation_ms: performance.now(), ...data});
    }
    publishJournal();
  }
  scope.nvwaExportFollowup = {records, journalFailures, get dropped() { return dropped; }};
  for (const level of ['log', 'info', 'warn', 'error', 'debug']) {
    const original = scope.console[level];
    scope.console[level] = function (...args) {
      // Restrict retained text to this application's declared evidence/errors.
      const message = args.filter(value => typeof value === 'string').join(' ').slice(0, 16384);
      if (message.includes('NVWA_EVIDENCE') || level === 'error') record('console', {level, message});
      return Reflect.apply(original, this, args);
    };
  }
  scope.addEventListener('error', event => record('error', {message: String(event.message).slice(0, 4096)}));
  scope.addEventListener('unhandledrejection', event => record('unhandledrejection', {message: String(event.reason).slice(0, 4096)}));
  scope.addEventListener('click', event => {
    if (event.target?.textContent === 'Download actual benchmark canvas PNG') {
      record('original-button-click', {isTrusted: event.isTrusted, activation: {isActive: navigator.userActivation?.isActive, hasBeenActive: navigator.userActivation?.hasBeenActive}});
    }
  }, true);
  record('observer-ready', {topLevel: scope === scope.top, href: location.href, userAgent: navigator.userAgent, timeOrigin: performance.timeOrigin, viewport:{width:scope.innerWidth,height:scope.innerHeight,dpr:scope.devicePixelRatio}});
})(window);
