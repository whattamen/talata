/* Talata Laro service worker: only handles the game page, its images and the game libraries. */
const CACHE = 'talata-laro-v2';
const PRECACHE = ['/laro.html', '/img/salpakan-rebolusyon.jpg', '/favicon.png', '/img/icon-192.png'];
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).catch(() => {}));
  self.skipWaiting();
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k.startsWith('talata-laro-') && k !== CACHE).map((k) => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const u = new URL(req.url);
  const page = u.origin === location.origin && u.pathname === '/laro.html';
  const asset = u.origin === location.origin && (u.pathname.startsWith('/img/') || u.pathname.startsWith('/models/') || u.pathname === '/favicon.png' || u.pathname === '/manifest.webmanifest');
  const lib = /^https:\/\/cdn\.jsdelivr\.net\/npm\/(three@0\.128\.0|peerjs@1\.5\.4)\//.test(u.href) || u.host === 'fonts.gstatic.com' || u.host === 'fonts.googleapis.com';
  if (!page && !asset && !lib) return;
  if (page) {
    e.respondWith(fetch(req).then((r) => { const copy = r.clone(); caches.open(CACHE).then((c) => c.put('/laro.html', copy)); return r; })
      .catch(() => caches.match('/laro.html')));
    return;
  }
  e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((r) => {
    if (r && (r.ok || r.type === 'opaque')) { const copy = r.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
    return r;
  })));
});
