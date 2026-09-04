const CACHE_NAME = 'jmb-perf-v1';
const ASSETS = [
  '/',
  '/static/index.html',
  '/static/css/style.css',
  '/static/js/app.js'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
});

self.addEventListener('fetch', (e) => {
  if (e.request.url.includes('/api/')) {
    return fetch(e.request);
  }
  e.respondWith(
    caches.match(e.request).then((res) => res || fetch(e.request))
  );
});
