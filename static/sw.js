// NHM Coach Service Worker — Web Push Notifications
const CACHE_NAME = 'nhm-portal-v1';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(clients.claim());
});

// Handle Push Notifications
self.addEventListener('push', (event) => {
  let data = { title: 'NHM Portal', body: 'Du hast eine neue Nachricht!', icon: '/static/img/icon-192.png' };
  if (event.data) {
    try { data = { ...data, ...event.data.json() }; } catch(e) {}
  }
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon || '/static/img/icon-192.png',
      badge: '/static/img/icon-192.png',
      tag: data.tag || 'nhm-notification',
      data: { url: data.url || '/portal/dashboard' },
      actions: data.actions || []
    })
  );
});

// Handle Notification Click
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/portal/dashboard';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes('/portal') && 'focus' in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});

// Offline Cache (basic)
self.addEventListener('fetch', (event) => {
  // Only cache GET requests to our own origin
  if (event.request.method !== 'GET') return;
  if (!event.request.url.startsWith(self.location.origin)) return;
});
