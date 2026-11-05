// Offline support for the installed app.
// Pages and question content: network first, falling back to the saved copy when offline.
// Accounts, grading, the AI coach and live classes always need the network and are never saved.
// Pages hold no personal data (progress lives in the browser's own storage), so sharing a device is safe.

var VERSION = 'v1';
var CACHE = 'estsat-' + VERSION;
var SHELL = [
  'index.html', 'today.html', 'learn.html', 'exam.html', 'review.html', 'progress.html', 'rewards.html', 'revision.html',
  'coach.html', 'pad.html', 'focus.html', 'parent.html', 'student-portal.html', 'manifest.webmanifest',
  'assets/site.css', 'assets/auth.js', 'assets/study.js', 'assets/app.js', 'assets/icons/icon.svg', 'assets/icons/icon-192.png'
];
var CONTENT = ['/api/practice/subjects', '/api/practice/math/topics', '/api/practice/english/topics'];

self.addEventListener('install', function (event) {
  event.waitUntil(caches.open(CACHE).then(function (cache) {
    // One page failing to save must not stop the rest, or the update.
    return Promise.all(SHELL.concat(CONTENT).map(function (url) { return cache.add(url).catch(function () {}); }));
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (event) {
  event.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (key) { return key !== CACHE; }).map(function (key) { return caches.delete(key); }));
  }).then(function () { return self.clients.claim(); }));
});

function networkFirst(request) {
  return caches.open(CACHE).then(function (cache) {
    return fetch(request).then(function (response) {
      if (response.ok) cache.put(request, response.clone());
      return response;
    }).catch(function () {
      return cache.match(request, { ignoreSearch: request.mode === 'navigate' }).then(function (saved) {
        if (saved) return saved;
        if (request.mode === 'navigate') return cache.match('today.html');
        return new Response(JSON.stringify({ error: 'You are offline and this has not been saved yet.' }), { status: 503, headers: { 'Content-Type': 'application/json' } });
      });
    });
  });
}

self.addEventListener('fetch', function (event) {
  var request = event.request;
  if (request.method !== 'GET') return;
  var url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.indexOf('/api/') === 0) {
    // Question text only, which is the same for everyone and never includes answers.
    var isContent = url.pathname.indexOf('/api/practice/') === 0 && url.pathname !== '/api/practice/review';
    if (isContent) event.respondWith(networkFirst(request));
    return;
  }
  if (url.pathname.indexOf('/login') === 0 || url.pathname.indexOf('/admin') === 0 || url.pathname.indexOf('/live') === 0) return;
  event.respondWith(networkFirst(request));
});
