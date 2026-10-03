// BUILD_ID and RESOURCES are generated from the tested production artifact.
const ROOT = new URL('./', self.location.href);
const PREFIX = `tgconvertor-static-${encodeURIComponent(ROOT.pathname)}-`;
const CACHE = PREFIX + BUILD_ID;
const ASSETS = new Map(RESOURCES.map((file) => [new URL(file.path, ROOT).href, file.sha256]));

async function cacheStaticAssets() {
  try {
    const cache = await caches.open(CACHE);
    for (const [url, expected] of ASSETS) {
      const response = await fetch(url, { cache: 'reload', credentials: 'omit' });
      if (!response.ok || response.type === 'opaque') throw Error('Static asset unavailable');
      const digest = await crypto.subtle.digest('SHA-256', await response.clone().arrayBuffer());
      const actual = [...new Uint8Array(digest)]
        .map((byte) => byte.toString(16).padStart(2, '0'))
        .join('');
      if (actual !== expected) throw Error('Static asset changed during installation');
      await cache.put(url, response);
    }
  } catch (error) {
    await caches.delete(CACHE);
    throw error;
  }
}
self.addEventListener('install', (event) => event.waitUntil(cacheStaticAssets()));
self.addEventListener('activate', (event) =>
  event.waitUntil(
    (async () => {
      for (const name of await caches.keys()) {
        if (name.startsWith(PREFIX) && name !== CACHE) await caches.delete(name);
      }
      await self.clients.claim();
    })(),
  ),
);
self.addEventListener('message', (event) => {
  if (event.data?.type === 'APPLY_UPDATE') event.waitUntil(self.skipWaiting());
  if (event.data?.type === 'OFFLINE_STATUS')
    event.waitUntil(
      (async () => {
        const cache = await caches.open(CACHE);
        const ready = (await cache.keys()).length === ASSETS.size;
        event.ports[0]?.postMessage({ ready, build: BUILD_ID });
      })(),
    );
});
self.addEventListener('fetch', (event) => {
  // Never cache uploads, session strings, Blob URLs, queries or arbitrary routes.
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== ROOT.origin || url.search) return;
  const navigation = event.request.mode === 'navigate' && url.pathname === ROOT.pathname;
  const key = navigation ? new URL('index.html', ROOT).href : url.href;
  if (!ASSETS.has(key)) return;
  event.respondWith(
    (async () => {
      const cache = await caches.open(CACHE);
      return (await cache.match(key)) || fetch(event.request);
    })(),
  );
});
