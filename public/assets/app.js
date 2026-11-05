/* Shared pieces for the study pages: navigation, saving progress, the lesson catalog and the question card.
   Loads after auth.js and study.js. All text from the server goes through textContent. */
(function () {
  'use strict';

  var E = window.EstSat, S = window.EstSatStudy;

  var ICONS = {
    home: '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/>',
    today: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
    book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    vault: '<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/><path d="M12 8v4l3 2"/>',
    trend: '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    trophy: '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M7 6H4v2a3 3 0 0 0 3 3M17 6h3v2a3 3 0 0 1-3 3"/>',
    layers: '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    spark: '<path d="M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z"/><path d="M19 3v4M17 5h4"/>',
    pen: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    timer: '<circle cx="12" cy="14" r="8"/><path d="M12 10v4l2 2M9 2h6"/>',
    users: '<circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0"/><path d="M17 4a4 4 0 0 1 0 8M22 21a7 7 0 0 0-4-6.3"/>',
    live: '<rect x="2" y="6" width="14" height="12" rx="2"/><path d="M22 8l-6 4 6 4z"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    more: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>'
  };
  var PAGES = [
    { href: 'index.html', label: 'Home', icon: 'home', note: 'Daily mission and arena' },
    { href: 'today.html', label: 'Today', icon: 'today', note: 'Your 15-minute plan' },
    { href: 'learn.html', label: 'Lessons', icon: 'book', note: 'Rules, examples, practice' },
    { href: 'exam.html', label: 'Exam', icon: 'target', note: 'Timed practice exams' },
    { href: 'review.html', label: 'Review', icon: 'vault', note: 'Mistakes and flashcards' },
    { href: 'progress.html', label: 'Progress', icon: 'trend', note: 'Scores and weak topics' },
    { href: 'rewards.html', label: 'Rewards', icon: 'trophy', note: 'XP, levels and badges' },
    { href: 'revision.html', label: 'Revision', icon: 'layers', note: 'Every rule, searchable' },
    { href: 'coach.html', label: 'AI Coach', icon: 'spark', note: 'Ask, or snap a question' },
    { href: 'pad.html', label: 'Visual Pad', icon: 'pen', note: 'Sketch a solution' },
    { href: 'focus.html', label: 'Focus', icon: 'timer', note: 'Timer and music' },
    { href: 'parent.html', label: 'Parent view', icon: 'users', note: 'Progress, goals, messages' },
    { href: 'live.html', label: 'Live class', icon: 'live', note: 'Join your teacher' },
    { href: 'student-portal.html', label: 'My account', icon: 'user', note: 'Profile and password' }
  ];
  var TABS = ['index.html', 'today.html', 'learn.html', 'exam.html'];
  var HEADER_LINKS = ['today.html', 'learn.html', 'exam.html', 'review.html', 'progress.html'];

  // ---------- DOM helpers ----------
  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }
  function clear(node) { node.textContent = ''; return node; }
  function byId(id) { return document.getElementById(id); }
  function icon(name, cls) {
    var span = el('span', cls || 'ico');
    span.setAttribute('aria-hidden', 'true');
    span.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + ICONS[name] + '</svg>';
    return span;
  }
  function param(name) {
    var match = new RegExp('[?&]' + name + '=([^&#]*)').exec(location.search);
    return match ? decodeURIComponent(match[1].replace(/\+/g, ' ')) : '';
  }
  function formatDate(key) {
    if (!key) return '';
    var p = key.split('-');
    return new Date(+p[0], p[1] - 1, +p[2]).toLocaleDateString('en', { day: 'numeric', month: 'short' });
  }
  function clock(seconds) {
    seconds = Math.max(0, Math.round(seconds));
    return Math.floor(seconds / 60) + ':' + ('0' + (seconds % 60)).slice(-2);
  }
  function subjectLabel(s) { return s === 'math' ? 'Math' : s === 'english' ? 'English' : s === 'physics' ? 'Physics' : 'Mixed'; }
  function ring(percent, label, tone) {
    var box = el('div', 'ring-c' + (tone ? ' ' + tone : ''));
    box.style.setProperty('--p', Math.max(0, Math.min(100, percent)) + '%');
    box.setAttribute('role', 'img');
    box.setAttribute('aria-label', label);
    box.appendChild(el('b', null, label));
    return box;
  }
  function meter(fraction, tone) {
    var bar = el('div', 'bar' + (tone ? ' ' + tone : ''));
    var fill = el('i');
    fill.style.width = Math.round(Math.max(0, Math.min(1, fraction)) * 100) + '%';
    bar.appendChild(fill);
    return bar;
  }
  function modes(group, options, value, onChange) {
    clear(group);
    options.forEach(function (opt) {
      var b = el('button', 'mode', opt[1]);
      b.type = 'button';
      b.setAttribute('aria-pressed', opt[0] === value ? 'true' : 'false');
      b.addEventListener('click', function () {
        Array.prototype.forEach.call(group.children, function (c) { c.setAttribute('aria-pressed', c === b ? 'true' : 'false'); });
        onChange(opt[0]);
      });
      group.appendChild(b);
    });
  }
  function toast(text) {
    var t = el('div', 'toast', text);
    t.setAttribute('role', 'status');
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 4500);
  }

  // ---------- Progress ----------
  var pushTimer = null;
  function load() { return S.normalize(E.readState()); }
  function pushNow(keepalive) {
    pushTimer = null;
    return E.pushState(E.readState(), keepalive).catch(function () { E.markDirty(); });
  }
  function save(state) {
    E.writeState(state);
    if (!E.loggedIn()) return;
    E.markDirty();
    clearTimeout(pushTimer);
    pushTimer = setTimeout(pushNow, 1500);
  }
  window.addEventListener('pagehide', function () {
    if (pushTimer) { clearTimeout(pushTimer); pushNow(true); }
  });
  // Save after anything that could move a streak or unlock a goal.
  function commit(state) {
    S.updateFreezes(state);
    save(state);
    catalog().then(function (c) {
      var fresh = S.unlockGoals(state, c);
      if (!fresh.length) return;
      save(state);
      S.celebrate(true);
      toast('Goal reached: ' + fresh[0].label + '. A message is waiting on your Rewards page.');
    }).catch(function () { /* goals are checked again next time */ });
  }
  // Paints with what is on this device, then again with the account copy once it arrives.
  function boot(render) {
    var state = load();
    if (S.updateFreezes(state)) save(state);
    render(state);
    if (!E.loggedIn()) return;
    E.pullState(false).then(function (remote) {
      var fresh = S.normalize(remote);
      if (S.updateFreezes(fresh)) save(fresh);
      render(fresh);
    }).catch(function () { /* offline: keep local progress, it syncs on the next save */ });
  }

  var catalogRequest = null;
  function catalog() {
    if (!catalogRequest) {
      catalogRequest = Promise.all([
        E.api('/practice/math/topics', { auth: false }),
        E.api('/practice/english/topics', { auth: false }),
        E.api('/practice/physics/topics', { auth: false })
      ]).then(function (r) { return { math: r[0], english: r[1], physics: r[2] }; })
        .catch(function (err) { catalogRequest = null; throw err; });
    }
    return catalogRequest;
  }
  function chunks(list, size) {
    var out = [];
    for (var i = 0; i < list.length; i += size) out.push(list.slice(i, i + size));
    return out;
  }
  function questionsById(ids) {
    if (!ids.length) return Promise.resolve([]);
    return Promise.all(chunks(ids, 60).map(function (part) {
      return E.api('/practice/questions?ids=' + encodeURIComponent(part.join(',')), { auth: false });
    })).then(function (parts) {
      return parts.reduce(function (all, p) { return all.concat(p.questions || []); }, []);
    });
  }

  // ---------- A question graded by the server ----------
  // opts: tag, onGraded(result, seconds), nextLabel, onNext()
  function questionCard(q, opts) {
    opts = opts || {};
    var started = Date.now(), locked = false;
    var card = el('article', 'card q-card practice-card');
    card.tabIndex = -1;
    if (opts.tag) card.appendChild(el('p', 'eyebrow', opts.tag));
    card.appendChild(el('p', 'q-text', q.question));
    var box = el('div', 'opts');
    var fb = el('p', 'feedback');
    fb.setAttribute('role', 'status');
    fb.setAttribute('aria-live', 'polite');
    var buttons = [];

    function choose(letter, btn) {
      if (locked) return;
      locked = true;
      btn.classList.add('selected');
      E.api('/practice/grade', { method: 'POST', auth: false, body: { items: [{ id: q.id, answer: letter }] } }).then(function (res) {
        var r = (res.results || [])[0];
        if (!r || r.error) throw new Error('grade');
        buttons.forEach(function (b) {
          b.disabled = true;
          if (b.dataset.letter === r.answer) b.classList.add('correct');
          else if (b.dataset.letter === letter) b.classList.add('wrong');
        });
        fb.textContent = '';
        fb.className = 'feedback show ' + (r.correct ? 'ok' : 'no');
        fb.appendChild(el('strong', null, r.correct ? 'Correct. ' : 'Not quite: the answer is ' + r.answer + '. '));
        fb.appendChild(document.createTextNode((r.explanation || []).join(' ')));
        if (r.correct) S.celebrate(false);
        if (opts.onGraded) opts.onGraded(r, Math.min(300, Math.round((Date.now() - started) / 1000)));
        if (opts.onNext) {
          var next = el('button', 'btn btn-primary btn-sm q-next', opts.nextLabel || 'Next');
          next.type = 'button';
          next.addEventListener('click', opts.onNext);
          card.appendChild(next);
          next.focus();
        }
      }).catch(function () {
        locked = false;
        btn.classList.remove('selected');
        fb.className = 'feedback show no';
        fb.textContent = 'Could not check that answer. Check your connection and try again.';
      });
    }

    (q.choices || []).forEach(function (c) {
      var b = el('button', 'opt');
      b.type = 'button';
      b.dataset.letter = c.id;
      b.setAttribute('aria-label', 'Answer ' + c.id + ': ' + c.text);
      var letter = el('span', 'letter', c.id);
      letter.setAttribute('aria-hidden', 'true');
      b.appendChild(letter);
      b.appendChild(el('span', 'txt', c.text));
      b.addEventListener('click', function () { choose(c.id, b); });
      buttons.push(b);
      box.appendChild(b);
    });
    card.addEventListener('keydown', function (e) {
      if (e.altKey || e.ctrlKey || e.metaKey || locked) return;
      var i = '1234'.indexOf(e.key.toLowerCase());
      if (i < 0) i = 'abcd'.indexOf(e.key.toLowerCase());
      if (i >= 0 && buttons[i]) { e.preventDefault(); buttons[i].click(); }
    });
    card.appendChild(box);
    card.appendChild(fb);
    return card;
  }

  // ---------- Navigation ----------
  function currentPage() {
    var name = location.pathname.split('/').pop();
    return name || 'index.html';
  }
  function moreSheet() {
    var sheet = el('dialog', 'more-sheet');
    sheet.setAttribute('aria-label', 'All pages');
    var head = el('div', 'more-head');
    head.appendChild(el('h2', null, 'Everything'));
    var close = el('button', 'btn btn-ghost btn-sm', 'Close');
    close.type = 'button';
    close.addEventListener('click', function () { sheet.close(); });
    head.appendChild(close);
    sheet.appendChild(head);
    var grid = el('div', 'more-grid');
    PAGES.forEach(function (p) {
      var a = el('a', 'more-item');
      a.href = p.href;
      if (p.href === currentPage()) a.setAttribute('aria-current', 'page');
      a.appendChild(icon(p.icon));
      var text = el('span');
      text.appendChild(el('strong', null, p.label));
      text.appendChild(el('small', null, p.note));
      a.appendChild(text);
      grid.appendChild(a);
    });
    sheet.appendChild(grid);
    sheet.addEventListener('click', function (e) { if (e.target === sheet) sheet.close(); });
    document.body.appendChild(sheet);
    return sheet;
  }
  function renderNav() {
    var sheet = moreSheet();
    function open() { sheet.showModal(); }

    var tabbar = el('nav', 'tabbar');
    tabbar.setAttribute('aria-label', 'Main');
    TABS.forEach(function (href) {
      var p = PAGES.filter(function (x) { return x.href === href; })[0];
      var a = el('a', 'tab-link');
      a.href = p.href;
      if (p.href === currentPage()) a.setAttribute('aria-current', 'page');
      a.appendChild(icon(p.icon));
      a.appendChild(el('span', null, p.label));
      tabbar.appendChild(a);
    });
    var moreTab = el('button', 'tab-link');
    moreTab.type = 'button';
    moreTab.appendChild(icon('more'));
    moreTab.appendChild(el('span', null, 'More'));
    moreTab.addEventListener('click', open);
    tabbar.appendChild(moreTab);
    document.body.appendChild(tabbar);
    document.body.classList.add('has-tabbar');

    var login = document.querySelector('.nav-in [data-auth-link]');
    if (login) {
      var more = el('button', 'btn btn-ghost btn-sm more-btn', 'More');
      more.type = 'button';
      more.addEventListener('click', open);
      login.parentNode.insertBefore(more, login);
    }
  }
  // The new pages share one header, filled in here.
  function renderHeader() {
    var header = document.querySelector('[data-app-header]');
    if (!header) return;
    var wrap = el('div', 'wrap nav-in');
    var brand = el('a', 'brand');
    brand.href = 'index.html';
    brand.setAttribute('aria-label', 'EST · SAT home');
    var mark = el('span', 'mark', 'E');
    mark.setAttribute('aria-hidden', 'true');
    brand.appendChild(mark);
    var txt = el('span', 'brand-txt');
    txt.appendChild(el('b', null, 'EST · SAT'));
    txt.appendChild(el('small', null, 'with Ahmed Labib'));
    brand.appendChild(txt);
    wrap.appendChild(brand);
    var links = el('nav', 'links');
    links.setAttribute('aria-label', 'Sections');
    HEADER_LINKS.forEach(function (href) {
      var p = PAGES.filter(function (x) { return x.href === href; })[0];
      var a = el('a', null, p.label);
      a.href = p.href;
      if (p.href === currentPage()) a.setAttribute('aria-current', 'page');
      links.appendChild(a);
    });
    wrap.appendChild(links);
    var login = el('a', 'btn btn-ghost btn-sm', 'Log in');
    login.href = 'login.html';
    login.setAttribute('data-auth-link', '');
    wrap.appendChild(login);
    header.appendChild(wrap);
    E.renderAuthLinks();
  }

  // ---------- AI replies ----------
  // Draws a reply with text nodes only, so nothing in it can become HTML.
  function richText(box, text) {
    function fill(node, parts) {
      parts.forEach(function (part) {
        if (part.bold) node.appendChild(el('strong', null, part.text));
        else if (part.italic) node.appendChild(el('em', null, part.text));
        else if (part.code) node.appendChild(el('code', null, part.text));
        else node.appendChild(document.createTextNode(part.text));
      });
      node.setAttribute('dir', 'auto');
      return node;
    }
    clear(box);
    S.replyBlocks(text).forEach(function (block) {
      if (block.type === 'heading') { box.appendChild(fill(el('h3'), block.parts)); return; }
      if (block.type === 'para') { box.appendChild(fill(el('p'), block.parts)); return; }
      var list = el(block.ordered ? 'ol' : 'ul');
      if (block.ordered && block.start > 1) list.start = block.start;
      block.items.forEach(function (parts) { list.appendChild(fill(el('li'), parts)); });
      box.appendChild(list);
    });
  }

  // ---------- One screen at a time ----------
  // Panels become tabs so a page never grows past the window. Every panel needs an
  // id and a data-view attribute holding its tab label.
  function tabStrip(label, panels, onShow) {
    var bar = el('div', 'view-bar no-print');
    bar.setAttribute('role', 'tablist');
    bar.setAttribute('aria-label', label);
    var tabs = panels.map(function (panel) {
      var tab = el('button', 'view-tab', panel.getAttribute('data-view'));
      tab.type = 'button';
      tab.id = 'tab-' + panel.id;
      tab.setAttribute('role', 'tab');
      tab.setAttribute('aria-controls', panel.id);
      panel.classList.add('view');
      panel.setAttribute('role', 'tabpanel');
      panel.setAttribute('aria-labelledby', tab.id);
      tab.addEventListener('click', function () { show(panel.id, true); });
      bar.appendChild(tab);
      return tab;
    });
    function show(id, byUser) {
      panels.forEach(function (panel, i) {
        var on = panel.id === id;
        panel.hidden = !on;
        tabs[i].setAttribute('aria-selected', on ? 'true' : 'false');
        tabs[i].tabIndex = on ? 0 : -1;
        if (on) {
          panel.scrollTop = 0;
          bar.scrollLeft = tabs[i].offsetLeft - (bar.clientWidth - tabs[i].offsetWidth) / 2;
        }
      });
      if (onShow) onShow(id, byUser);
      // Charts measure themselves, so they need to redraw once they are visible.
      window.dispatchEvent(new Event('resize'));
    }
    bar.addEventListener('keydown', function (e) {
      var step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      var at = tabs.indexOf(document.activeElement);
      if (!step || at < 0) return;
      e.preventDefault();
      var next = tabs[(at + step + tabs.length) % tabs.length];
      next.click();
      next.focus();
    });
    return { bar: bar, show: show };
  }
  // Tabs built by a page's own script, such as the results of an exam.
  function tabs(parent, label, panels) {
    var strip = tabStrip(label, panels);
    var holder = el('div', 'view-panels');
    parent.appendChild(strip.bar);
    parent.appendChild(holder);
    panels.forEach(function (panel) { holder.appendChild(panel); });
    strip.show(panels[0].id, false);
    return strip;
  }
  // Tabs written in a page's markup: <main data-views="Label"> with data-view children.
  // The open tab follows the URL hash, so links like index.html#practice still work.
  var showView = function () {};
  function initViews() {
    var root = document.querySelector('[data-views]');
    if (!root) return;
    var panels = Array.prototype.filter.call(root.children, function (c) { return c.hasAttribute('data-view'); });
    if (!panels.length) return;
    var strip = tabStrip(root.getAttribute('data-views') || 'Sections', panels, function (id, byUser) {
      if (byUser && window.history && history.replaceState) history.replaceState(null, '', '#' + id);
    });
    var holder = el('div', 'view-panels');
    root.insertBefore(strip.bar, panels[0]);
    root.insertBefore(holder, panels[0]);
    panels.forEach(function (panel) { holder.appendChild(panel); });
    function fromHash() {
      var target = location.hash.length > 1 && document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (!target) return '';
      var match = panels.filter(function (panel) { return panel === target || panel.contains(target); })[0];
      return match ? match.id : '';
    }
    window.addEventListener('hashchange', function () {
      var id = fromHash();
      if (id) strip.show(id, false);
    });
    strip.show(fromHash() || panels[0].id, false);
    showView = function (id) { strip.show(id, true); };
  }
  // Splits a list into pages. sizes is [phone, tablet, laptop] items per page.
  // barAfter is where the Previous and Next buttons go, if not right after the list.
  function pager(box, sizes, barAfter) {
    var nodes = [], page = 0, printing = false;
    var bar = el('div', 'pager no-print');
    var prev = el('button', 'btn btn-ghost btn-sm', 'Previous');
    var next = el('button', 'btn btn-ghost btn-sm', 'Next');
    var status = el('span', 'pager-status');
    status.setAttribute('aria-live', 'polite');
    prev.type = next.type = 'button';
    bar.appendChild(prev);
    bar.appendChild(status);
    bar.appendChild(next);
    var anchor = barAfter || box;
    anchor.parentNode.insertBefore(bar, anchor.nextSibling);
    function perPage() {
      var w = window.innerWidth;
      return w <= 600 ? sizes[0] : w <= 1020 ? sizes[1] : sizes[2];
    }
    var lastSize = perPage();
    function paint() {
      var size = perPage(), total = Math.max(1, Math.ceil(nodes.length / size));
      if (page >= total) page = total - 1;
      clear(box);
      nodes.slice(printing ? 0 : page * size, printing ? nodes.length : (page + 1) * size).forEach(function (n) { box.appendChild(n); });
      bar.hidden = total < 2;
      status.textContent = 'Page ' + (page + 1) + ' of ' + total;
      prev.disabled = page === 0;
      next.disabled = page >= total - 1;
      box.scrollTop = 0;
    }
    prev.addEventListener('click', function () { page -= 1; paint(); });
    next.addEventListener('click', function () { page += 1; paint(); });
    window.addEventListener('resize', function () {
      if (perPage() === lastSize) return;
      lastSize = perPage();
      paint();
    });
    window.addEventListener('beforeprint', function () { printing = true; paint(); });
    window.addEventListener('afterprint', function () { printing = false; paint(); });
    return { set: function (list, keepPage) { nodes = list; if (!keepPage) page = 0; paint(); } };
  }

  function registerWorker() {
    if (!('serviceWorker' in navigator) || /^(localhost|127\.)/.test(location.hostname)) return;
    navigator.serviceWorker.register('sw.js').catch(function () { /* offline support is optional */ });
  }

  renderHeader();
  initViews();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', renderNav);
  else renderNav();
  registerWorker();

  window.App = {
    el: el, clear: clear, byId: byId, icon: icon, param: param, formatDate: formatDate, clock: clock, subjectLabel: subjectLabel,
    ring: ring, meter: meter, modes: modes, toast: toast, load: load, save: save, commit: commit, boot: boot, catalog: catalog,
    chunks: chunks, questionsById: questionsById, questionCard: questionCard,
    richText: richText, tabs: tabs, pager: pager, showView: function (id) { showView(id); }
  };
})();
