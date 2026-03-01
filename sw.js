// Service Worker - Cache for offline & speed
const CACHE_NAME = 'catalog-v3';
const PRECACHE = [
    './',
    './index.html',
    './data.json',
    './manifest.json',
    './icon-192.png',
    'https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500;600;700&display=swap'
];

self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then((keys) => Promise.all(
            keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
        ))
    );
    self.clients.claim();
});

self.addEventListener('fetch', (e) => {
    const url = new URL(e.request.url);
    if (e.request.method !== 'GET') return;
    if (url.hostname.includes('firebase') || url.hostname.includes('counterapi') || url.hostname.includes('gstatic')) return;

    if (url.hostname.includes('r2.dev') || e.request.destination === 'image') {
        e.respondWith(
            caches.match(e.request).then((cached) => {
                if (cached) return cached;
                return fetch(e.request).then((response) => {
                    if (response.ok) {
                        const clone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
                    }
                    return response;
                }).catch(() => new Response('', { status: 404 }));
            })
        );
        return;
    }

    e.respondWith(
        fetch(e.request).then((response) => {
            if (response.ok) {
                const clone = response.clone();
                caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
            }
            return response;
        }).catch(() => caches.match(e.request))
    );
});
