// Firebase Messaging Service Worker
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js');

firebase.initializeApp({
    apiKey: "AIzaSyC_kzJSCqPM09v5FeIXrMQbvuBQUlEKiNg",
    authDomain: "studiolab-1b0fd.firebaseapp.com",
    projectId: "studiolab-1b0fd",
    storageBucket: "studiolab-1b0fd.firebasestorage.app",
    messagingSenderId: "699467626495",
    appId: "1:699467626495:web:9b67989481975f9c94d9ca"
});

const messaging = firebase.messaging();

// Handle background messages
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

// Handle notification click
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
