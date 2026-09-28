const CACHE = 'stock-analista-v3';
const NETWORK_FIRST = ['/', '/index.html'];
const ASSETS = ['./', './index.html', './manifest.webmanifest', './icon.svg'];

// Install: pre-cache static assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

// Activate: delete old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: network-first for HTML, cache-first for other assets
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);

  // External requests (Finnhub, TradingView) → always network
  if (url.origin !== location.origin) return;

  const isHtml = NETWORK_FIRST.some(p => url.pathname === p || url.pathname.endsWith('.html'));

  if (isHtml) {
    // Network-first strategy for HTML
    event.respondWith(
      fetch(event.request)
        .then(res => {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(event.request, clone));
          return res;
        })
        .catch(() => caches.match(event.request))
    );
  } else {
    // Cache-first strategy for static assets
    event.respondWith(
      caches.match(event.request).then(hit => hit || fetch(event.request))
    );
  }
});
