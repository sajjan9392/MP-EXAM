// Pariksha Sarthi — Service Worker (offline support for the web/PWA version)
// index.html / questions.json update karne ke baad CACHE ka number badhao (v2 -> v3) taaki purana cache hat jaye.
const CACHE = 'psarthi-v28';
const ASSETS = ['./','./index.html','./manifest.json','./qindex.json','./ca.json','./privacy.html','./icon-192.png','./icon-512.png','./icon-180.png','./logo.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  const req = e.request; if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin === location.origin) {
    // network-first for data files, cache-first for the rest
    if (url.pathname.endsWith('.json')) {
      e.respondWith(fetch(req).then(r => { caches.open(CACHE).then(c => c.put(req, r.clone())); return r; }).catch(() => caches.match(req)));
    } else {
      e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(r => { caches.open(CACHE).then(c => c.put(req, r.clone())); return r; }).catch(() => caches.match('./index.html'))));
    }
    return;
  }
  if (url.hostname.endsWith('googleapis.com') || url.hostname.endsWith('gstatic.com')) {
    e.respondWith(fetch(req).then(r => { caches.open(CACHE).then(c => c.put(req, r.clone())); return r; }).catch(() => caches.match(req)));
  }
});
