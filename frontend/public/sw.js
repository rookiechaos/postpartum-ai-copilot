// Service Worker for Postpartum AI Copilot
const CACHE_NAME = 'postpartum-copilot-v2'
const RUNTIME_CACHE = 'postpartum-runtime-v2'
const urlsToCache = [
  '/',
  '/index.html',
  '/manifest.json',
  '/offline.html'
]

// Cache strategies
const CACHE_STRATEGIES = {
  CACHE_FIRST: 'cache-first',
  NETWORK_FIRST: 'network-first',
  STALE_WHILE_REVALIDATE: 'stale-while-revalidate'
}

// Install event - cache resources
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Opened cache')
        return cache.addAll(urlsToCache.map(url => new Request(url, { cache: 'reload' })))
          .catch(err => {
            console.warn('[SW] Failed to cache some resources:', err)
            // Continue even if some resources fail to cache
          })
      })
      .then(() => {
        // Force activation of new service worker
        return self.skipWaiting()
      })
  )
})

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE) {
            console.log('[SW] Deleting old cache:', cacheName)
            return caches.delete(cacheName)
          }
        })
      )
    })
    .then(() => {
      // Take control of all pages immediately
      return self.clients.claim()
    })
  )
})

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return
  }

  // API calls - network first with cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstStrategy(request))
    return
  }

  // Static assets - cache first
  if (url.pathname.match(/\.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)$/)) {
    event.respondWith(cacheFirstStrategy(request))
    return
  }

  // HTML pages - network first with cache fallback
  if (request.headers.get('accept').includes('text/html')) {
    event.respondWith(networkFirstStrategy(request))
    return
  }

  // Default: stale-while-revalidate
  event.respondWith(staleWhileRevalidateStrategy(request))
})

// Network first strategy
async function networkFirstStrategy(request) {
  try {
    const networkResponse = await fetch(request)
    if (networkResponse.ok) {
      const cache = await caches.open(RUNTIME_CACHE)
      cache.put(request, networkResponse.clone())
    }
    return networkResponse
  } catch (error) {
    const cachedResponse = await caches.match(request)
    if (cachedResponse) {
      return cachedResponse
    }
    // Return offline page for HTML requests
    if (request.headers.get('accept').includes('text/html')) {
      return caches.match('/offline.html')
    }
    throw error
  }
}

// Cache first strategy
async function cacheFirstStrategy(request) {
  const cachedResponse = await caches.match(request)
  if (cachedResponse) {
    return cachedResponse
  }
  try {
    const networkResponse = await fetch(request)
    if (networkResponse.ok) {
      const cache = await caches.open(RUNTIME_CACHE)
      cache.put(request, networkResponse.clone())
    }
    return networkResponse
  } catch (error) {
    // Return a placeholder or error response
    return new Response('Resource not available offline', { status: 503 })
  }
}

// Stale while revalidate strategy
async function staleWhileRevalidateStrategy(request) {
  const cache = await caches.open(RUNTIME_CACHE)
  const cachedResponse = await cache.match(request)
  
  const fetchPromise = fetch(request).then((networkResponse) => {
        if (networkResponse.ok) {
          cache.put(request, networkResponse.clone())
        }
        return networkResponse
      })
      .catch(() => cachedResponse)

  return cachedResponse || fetchPromise
}

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag)
  
  if (event.tag === 'sync-tracking') {
    event.waitUntil(syncTrackingData())
  } else if (event.tag === 'sync-chat') {
    event.waitUntil(syncChatMessages())
  } else if (event.tag === 'sync-all') {
    event.waitUntil(syncAllPendingData())
  }
})

async function syncTrackingData() {
  try {
    const pendingData = await getPendingData('tracking')
    for (const data of pendingData) {
      try {
        const response = await fetch('/api/tracking', {
          method: 'POST',
          body: JSON.stringify(data.data),
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${data.token || ''}`
          }
        })
        if (response.ok) {
          await removePendingData('tracking', data.id)
        }
      } catch (error) {
        console.error('[SW] Sync tracking failed:', error)
      }
    }
  } catch (error) {
    console.error('[SW] Background sync error:', error)
  }
}

async function syncChatMessages() {
  try {
    const pendingData = await getPendingData('chat')
    for (const data of pendingData) {
      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          body: JSON.stringify(data.data),
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${data.token || ''}`
          }
        })
        if (response.ok) {
          await removePendingData('chat', data.id)
        }
      } catch (error) {
        console.error('[SW] Sync chat failed:', error)
      }
    }
  } catch (error) {
    console.error('[SW] Background sync error:', error)
  }
}

async function syncAllPendingData() {
  await Promise.all([
    syncTrackingData(),
    syncChatMessages()
  ])
}

// IndexedDB helpers for offline storage
async function getPendingData(type) {
  return new Promise((resolve) => {
    const request = indexedDB.open('postpartum-offline', 1)
    request.onerror = () => resolve([])
    request.onsuccess = (event) => {
      const db = event.target.result
      const transaction = db.transaction(['pending'], 'readonly')
      const store = transaction.objectStore('pending')
      const index = store.index('type')
      const query = index.getAll(type)
      query.onsuccess = () => resolve(query.result || [])
      query.onerror = () => resolve([])
    }
    request.onupgradeneeded = (event) => {
      const db = event.target.result
      if (!db.objectStoreNames.contains('pending')) {
        const store = db.createObjectStore('pending', { keyPath: 'id', autoIncrement: true })
        store.createIndex('type', 'type', { unique: false })
      }
    }
  })
}

async function removePendingData(type, id) {
  return new Promise((resolve) => {
    const request = indexedDB.open('postpartum-offline', 1)
    request.onsuccess = (event) => {
      const db = event.target.result
      const transaction = db.transaction(['pending'], 'readwrite')
      const store = transaction.objectStore('pending')
      store.delete(id)
      transaction.oncomplete = () => resolve()
      transaction.onerror = () => resolve()
    }
  })
}

// Push notifications
self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch (e) {
    data = { body: event.data ? event.data.text() : 'New reminder from Postpartum Copilot' }
  }

  const options = {
    body: data.body || data.message || 'New reminder from Postpartum Copilot',
    icon: data.icon || '/icon-192x192.png',
    badge: '/icon-192x192.png',
    vibrate: data.vibrate || [200, 100, 200],
    tag: data.tag || 'postpartum-reminder',
    data: data.data || {},
    requireInteraction: data.requireInteraction || false,
    actions: data.actions || [],
    image: data.image,
    timestamp: Date.now()
  }

  event.waitUntil(
    self.registration.showNotification(
      data.title || 'Postpartum AI Copilot',
      options
    )
  )
})

// Notification click
self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  const urlToOpen = event.notification.data?.url || '/'
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Check if there's already a window open
        for (const client of clientList) {
          if (client.url === urlToOpen && 'focus' in client) {
            return client.focus()
          }
        }
        // Open new window
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen)
        }
      })
  )
})

// Notification close
self.addEventListener('notificationclose', (event) => {
  console.log('[SW] Notification closed:', event.notification.tag)
})
