/* Shared session, API and progress-sync helpers for the EST · SAT pages. */
(function () {
  'use strict';

  var TOKEN_KEY = 'estsat.token';
  var USER_KEY = 'estsat.user';
  var STATE_KEY = 'estsat.v1';
  var DIRTY_KEY = 'estsat.dirty';

  function read(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function write(key, value) {
    try {
      if (value === null) localStorage.removeItem(key); else localStorage.setItem(key, value);
    } catch (e) { /* storage blocked: the session simply won't persist */ }
  }

  function token() { return read(TOKEN_KEY); }
  function user() { try { return JSON.parse(read(USER_KEY)); } catch (e) { return null; } }
  function loggedIn() { return !!token(); }
  function setSession(t, u) { write(TOKEN_KEY, t); write(USER_KEY, JSON.stringify(u)); }
  function setUser(u) { write(USER_KEY, JSON.stringify(u)); }
  function clearSession(clearProgress) {
    write(TOKEN_KEY, null);
    write(USER_KEY, null);
    write(DIRTY_KEY, null);
    if (clearProgress) write(STATE_KEY, null);
  }

  function apiError(message, status) { var e = new Error(message); e.status = status; return e; }

  function api(path, opts) {
    opts = opts || {};
    var t = token();
    var headers = { Accept: 'application/json' };
    if (opts.body !== undefined) headers['Content-Type'] = 'application/json';
    if (t && opts.auth !== false) headers.Authorization = 'Bearer ' + t;
    return fetch('/api' + path, {
      method: opts.method || 'GET',
      headers: headers,
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
      keepalive: !!opts.keepalive
    }).catch(function () {
      throw apiError('Can’t reach the server. Check your connection and try again.', 0);
    }).then(function (res) {
      return res.json().catch(function () { return null; }).then(function (data) {
        if (res.status === 401 && t && opts.auth !== false) clearSession(false);
        if (!res.ok) throw apiError((data && data.error) || 'Something went wrong. Please try again.', res.status);
        return data;
      });
    });
  }

  // ---------- Progress sync ----------
  function readState() { try { return JSON.parse(read(STATE_KEY)); } catch (e) { return null; } }
  function writeState(s) { write(STATE_KEY, JSON.stringify(s)); }
  function isEmpty(s) {
    if (!s) return true;
    var answered = s.stats && s.stats.answered;
    return !answered && !(s.chapters && s.chapters.length) && !s.exam && !(s.days && Object.keys(s.days).length);
  }
  function union(a, b) {
    var out = [];
    (a || []).concat(b || []).forEach(function (x) { if (out.indexOf(x) < 0) out.push(x); });
    return out;
  }
  // Wrong answers waiting to be reviewed, newest last, deduped by question id.
  function unionMistakes(a, b) {
    var out = [], seen = {};
    (a || []).concat(b || []).forEach(function (m) {
      if (!m || typeof m.id !== 'string' || seen[m.id]) { return; }
      seen[m.id] = 1;
      out.push({ id: m.id, date: m.date || '' });
    });
    return out.slice(-100);
  }
  function mergeState(local, remote) {
    local = local || {}; remote = remote || {};
    var ls = local.stats || {}, rs = remote.stats || {};
    var stats = (rs.answered || 0) > (ls.answered || 0) ? rs : ls;
    var days = {};
    [local.days || {}, remote.days || {}].forEach(function (d) {
      Object.keys(d).forEach(function (k) { days[k] = Math.max(days[k] || 0, d[k] || 0); });
    });
    var lm = local.mission || {}, rm = remote.mission || {};
    var mission = lm.date === rm.date ? { date: lm.date || '', done: union(lm.done, rm.done) }
      : ((lm.date || '') > (rm.date || '') ? lm : rm);
    return {
      stats: { answered: stats.answered || 0, correct: stats.correct || 0, time: stats.time || 0 },
      days: days,
      chapters: union(local.chapters, remote.chapters),
      exam: remote.exam || local.exam || '',
      mission: { date: mission.date || '', done: (mission.done || []).slice() },
      mistakes: unionMistakes(local.mistakes, remote.mistakes)
    };
  }
  function pushState(s, keepalive) {
    return api('/user/state', { method: 'PUT', body: { data: s }, keepalive: keepalive }).then(function (res) {
      write(DIRTY_KEY, null);
      return res.data;
    });
  }
  function markDirty() { write(DIRTY_KEY, '1'); }

  // The account is the source of truth once logged in. Local changes that never reached the
  // server (offline, closed tab) are merged in; anonymous progress is merged in at first login.
  function pullState(mergeLocal) {
    return api('/user/state').then(function (res) {
      var remote = res.data || {};
      var local = readState();
      var result;
      if (isEmpty(remote)) result = local || remote;
      else if (mergeLocal || read(DIRTY_KEY)) result = mergeState(local, remote);
      else result = remote;
      writeState(result);
      if (result !== remote && !isEmpty(result)) return pushState(result).catch(function () { markDirty(); return result; });
      return result;
    });
  }

  // ---------- Small UI helpers ----------
  function firstName(u) {
    var name = ((u && (u.full_name || u.username)) || '').trim();
    return name ? name.split(/\s+/)[0] : 'there';
  }
  function renderAuthLinks() {
    var u = user();
    var links = document.querySelectorAll('[data-auth-link]');
    Array.prototype.forEach.call(links, function (a) {
      if (loggedIn() && u) {
        var staff = u.role === 'admin' || u.role === 'teacher';
        a.textContent = staff ? 'Dashboard' : 'Hi, ' + firstName(u);
        a.href = staff ? 'admin.html' : 'student-portal.html';
      }
      else { a.textContent = 'Log in'; a.href = 'login.html'; }
    });
  }
  function safeNext(value, fallback) {
    return /^[a-z0-9-]+\.html(#[a-z0-9-]+)?$/i.test(value || '') ? value : fallback;
  }
  function logout() {
    clearSession(true);
    window.location.href = 'index.html';
  }

  function liveBanner() {
    if (document.body.getAttribute('data-live-banner') === 'off') return;
    fetch('/api/live/status').then(function (r) { return r.ok ? r.json() : null; }).then(function (s) {
      if (!s || !s.live || document.querySelector('.live-banner')) return;
      var a = document.createElement('a');
      a.className = 'live-banner';
      a.href = 'live.html';
      a.innerHTML = '<span class="live-dot" aria-hidden="true"></span><span>Live now:</span>';
      var title = document.createElement('b');
      title.textContent = s.live.title;
      var join = document.createElement('span');
      join.textContent = 'Join →';
      a.appendChild(title);
      a.appendChild(join);
      document.body.appendChild(a);
    }).catch(function () { /* banner is optional */ });
  }

  window.EstSat = {
    api: api, token: token, user: user, loggedIn: loggedIn, setSession: setSession, setUser: setUser,
    clearSession: clearSession, logout: logout, readState: readState, writeState: writeState,
    mergeState: mergeState, pullState: pullState, pushState: pushState, markDirty: markDirty,
    firstName: firstName, renderAuthLinks: renderAuthLinks, safeNext: safeNext
  };

  function onReady() { renderAuthLinks(); liveBanner(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', onReady);
  else onReady();
})();
