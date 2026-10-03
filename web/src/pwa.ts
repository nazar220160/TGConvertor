export type OfflineState = 'saving' | 'ready' | 'error' | 'unsupported';

export function registerOffline(onState: (state: OfflineState, update: boolean) => void) {
  if (!('serviceWorker' in navigator) || !import.meta.env.PROD) {
    onState('unsupported', false);
    return () => {};
  }
  let registration: ServiceWorkerRegistration | undefined;
  let offline: OfflineState = 'saving';
  let reloadForUpdate = false;
  const report = () => onState(offline, !!registration?.waiting);
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (reloadForUpdate) location.reload();
  });
  onState('saving', false);
  navigator.serviceWorker
    .register(new URL('sw.js', document.baseURI), { updateViaCache: 'none' })
    .then(async (installed) => {
      registration = installed;
      const watch = (worker: ServiceWorker | null) =>
        worker?.addEventListener('statechange', () => {
          if (worker.state === 'redundant' && !installed.active) offline = 'error';
          if (worker.state === 'installed' || worker.state === 'redundant') report();
        });
      watch(installed.installing);
      installed.addEventListener('updatefound', () => watch(installed.installing));
      report();
      const active = (await navigator.serviceWorker.ready).active;
      if (!active) throw Error('No active offline worker');
      const available = await new Promise<boolean>((resolve) => {
        const channel = new MessageChannel();
        const timer = setTimeout(() => {
          channel.port1.close();
          resolve(false);
        }, 10000);
        channel.port1.onmessage = (event) => {
          clearTimeout(timer);
          channel.port1.close();
          resolve(event.data.ready === true);
        };
        active.postMessage({ type: 'OFFLINE_STATUS' }, [channel.port2]);
      });
      offline = available ? 'ready' : 'error';
      report();
    })
    .catch(() => {
      offline = 'error';
      report();
    });
  return () => {
    if (!registration?.waiting) return;
    reloadForUpdate = true;
    registration.waiting.postMessage({ type: 'APPLY_UPDATE' });
  };
}
