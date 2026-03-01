// Firebase Messaging Service Worker
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js');

firebase.initializeApp({
    apiKey: "AIzaSyBVQ8IxgDCMFOVKcOCMjXjrU-3VsB5VMWE",
    authDomain: "studiolab-31e28.firebaseapp.com",
    projectId: "studiolab-31e28",
    storageBucket: "studiolab-31e28.firebasestorage.app",
    messagingSenderId: "930498498498",
    appId: "1:930498498498:web:6e2b6b6e6a7f21d7ea4aee"
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
