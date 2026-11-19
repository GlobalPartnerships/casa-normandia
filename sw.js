const CACHE_NAME = 'casa-normandia-pwa-v2';

// Recursos esenciales para carga inmediata y modo offline
const PRECACHE_ASSETS = [
  './',
  './index.html',
  './index-en.html',
  './nilo.html',
  './concierge.html',
  './galeria.html',
  './politicas.html',
  './policies.html',
  './manifest.json',
  './favicon.svg',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './logo_casa_normandia.svg',
  './logo_granja_nilo.svg'
];

// 1. Instalación: precachea archivos estáticos prioritarios
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Precacheando recursos iniciales de Casa Normandía');
      return cache.addAll(PRECACHE_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// 2. Activación: purga versiones antiguas del cache
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log('[SW] Purgando caché obsoleta:', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// 3. Fetch: Estrategia Stale-While-Revalidate para recursos locales
self.addEventListener('fetch', (event) => {
  // Solo procesar peticiones GET dentro del mismo origen
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);

  if (url.origin === location.origin) {
    event.respondWith(
      caches.open(CACHE_NAME).then(async (cache) => {
        const cachedResponse = await cache.match(event.request);

        const fetchPromise = fetch(event.request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            cache.put(event.request, networkResponse.clone());
          }
          return networkResponse;
        }).catch(() => {
          // Si falla la red (offline), retorna lo que haya en caché
          return cachedResponse;
        });

        // Retorna la versión en caché de inmediato; actualiza en background
        return cachedResponse || fetchPromise;
      })
    );
  }
});
