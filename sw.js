// Service Worker - Cache + Firebase Cloud Messaging
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js');

// === Firebase Messaging ===
firebase.initializeApp({
    apiKey: "AIzaSyC_kzJSCqPM09v5FeIXrMQbvuBQUlEKiNg",
    authDomain: "studiolab-1b0fd.firebaseapp.com",
    projectId: "studiolab-1b0fd",
    storageBucket: "studiolab-1b0fd.firebasestorage.app",
    messagingSenderId: "699467626495",
    appId: "1:699467626495:web:9b67989481975f9c94d9ca"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
    const title = payload.notification?.title || 'קטלוג מותגים';
    const options = {
        body: payload.notification?.body || 'יש מוצרים חדשים בקטלוג!',
        icon: './icon-192.png',
        badge: './icon-192.png',
        dir: 'rtl',
        lang: 'he',
        data: { url: './' }
    };
    self.registration.showNotification(title, options);
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const url = event.notification.data?.url || './';
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
            for (const client of windowClients) {
                if (client.url.includes('my-catalog') && 'focus' in client) {
                    return client.focus();
                }
            }
            return clients.openWindow(url);
        })
    );
});

// === Caching ===
const CACHE_NAME = 'catalog-v2';
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
