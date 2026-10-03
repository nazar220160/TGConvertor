export type OfflineState = 'saving' | 'ready' | 'error' | 'unsupported';

export function registerOffline(
  onState: (state: OfflineState, update: boolean) => void,
  canReload: () => boolean,
) {
  if (!('serviceWorker' in navigator) || !import.meta.env.PROD) {
    onState('unsupported', false);
    return { applyUpdate() {}, check() {} };
  }
  let registration: ServiceWorkerRegistration | undefined;
  let offline: OfflineState = 'saving';
  let reloadForUpdate = false;
  let checking = false;
  let lastUpdateCheck = 0;
  const applyUpdate = () => {
    if (!registration?.waiting || reloadForUpdate) return;
    reloadForUpdate = true;
    registration.waiting.postMessage({ type: 'APPLY_UPDATE' });
  };
  const check = async () => {
    const waiting = registration?.waiting;
    if (!waiting || checking || reloadForUpdate || !canReload()) return;
    checking = true;
    // A worker activation affects every tab. Never automatically interrupt another tab.
    const alone = await new Promise<boolean>((resolve) => {
      const channel = new MessageChannel();
      const timer = setTimeout(() => {
        channel.port1.close();
        resolve(false);
      }, 2000);
      channel.port1.onmessage = (event) => {
        clearTimeout(timer);
        channel.port1.close();
        resolve(event.data.alone === true);
      };
      waiting.postMessage({ type: 'CAN_AUTO_UPDATE' }, [channel.port2]);
    });
    checking = false;
    // Input can arrive while the worker checks other clients.
    if (alone && registration?.waiting === waiting && canReload()) applyUpdate();
  };
  const report = () => onState(offline, !!registration?.waiting);
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (reloadForUpdate) {
      reloadForUpdate = false;
      location.reload();
    }
  });
  const refresh = () => {
    void check();
    if (!registration || !navigator.onLine || document.visibilityState === 'hidden') return;
    if (Date.now() - lastUpdateCheck < 60000) return;
    lastUpdateCheck = Date.now();
    // A failed update check must not invalidate a working offline copy.
    void registration.update().catch(() => {});
  };
  window.addEventListener('online', refresh);
  document.addEventListener('visibilitychange', refresh);
  onState('saving', false);
  navigator.serviceWorker
    .register(new URL('sw.js', document.baseURI), { updateViaCache: 'none' })
    .then(async (installed) => {
      registration = installed;
      const watch = (worker: ServiceWorker | null) =>
        worker?.addEventListener('statechange', () => {
          if (worker.state === 'redundant' && !installed.active) offline = 'error';
          if (worker.state === 'installed' || worker.state === 'redundant') {
            report();
            void check();
          }
        });
      watch(installed.installing);
      installed.addEventListener('updatefound', () => watch(installed.installing));
      report();
      refresh();
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
      void check();
    })
    .catch(() => {
      offline = 'error';
      report();
    });
  return { applyUpdate, check };
}
