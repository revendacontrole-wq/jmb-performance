const CACHE_NAME = 'jmb-perf-v12';

self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.map(key => caches.delete(key))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  // Always fetch fresh network requests for index.html and static files
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
