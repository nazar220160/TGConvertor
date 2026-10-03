import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { stripTypeScriptTypes } from 'node:module';
import { test } from 'node:test';
import vm from 'node:vm';

// Execute the production TypeScript controller, rather than a parallel implementation.
const source = stripTypeScriptTypes(
  await fs.readFile(new URL('../src/pwa.ts', import.meta.url), 'utf8'),
)
  .replace('import.meta.env.PROD', 'true')
  .replace('export function', 'function');
const settle = async () => {
  for (let i = 0; i < 5; i++) await new Promise(setImmediate);
};
function setup({
  waiting = true,
  alone = true,
  editable = false,
  supported = true,
  legacy = false,
  probe,
} = {}) {
  const serviceWorker = new EventTarget();
  const document = Object.assign(new EventTarget(), {
    baseURI: 'https://example.test/TGConvertor/',
    visibilityState: 'visible',
  });
  const window = new EventTarget();
  const timers = new Map();
  const states = [];
  const messages = [];
  const state = { editable, reloads: 0, updates: 0, now: 1000000 };
  class Channel {
    constructor() {
      this.port1 = { close() {}, onmessage: null };
      this.port2 = { postMessage: (data) => this.port1.onmessage?.({ data }) };
    }
  }
  const candidate = Object.assign(new EventTarget(), {
    state: 'installed',
    postMessage(data, ports) {
      messages.push(data.type);
      if (data.type === 'CAN_AUTO_UPDATE' && !legacy) {
        probe?.(state);
        ports[0].postMessage({ alone });
      }
    },
  });
  const active = { postMessage: (_data, ports) => ports[0].postMessage({ ready: true }) };
  const registration = Object.assign(new EventTarget(), {
    waiting: waiting ? candidate : null,
    active,
    installing: null,
    async update() {
      state.updates++;
      if (!navigator.onLine) throw Error('offline');
    },
  });
  const navigator = { onLine: true, ...(supported ? { serviceWorker } : {}) };
  serviceWorker.register = async (url, options) => {
    assert.equal(url.href, document.baseURI + 'sw.js');
    assert.equal(options.updateViaCache, 'none');
    return registration;
  };
  serviceWorker.ready = Promise.resolve(registration);
  const context = vm.createContext({
    navigator,
    document,
    window,
    URL,
    MessageChannel: Channel,
    Date: { now: () => state.now },
    setTimeout: (callback) => {
      const id = Symbol();
      timers.set(id, callback);
      return id;
    },
    clearTimeout: (id) => timers.delete(id),
    location: { reload: () => state.reloads++ },
  });
  vm.runInContext(source + '\nthis.registerOffline = registerOffline;', context);
  const control = context.registerOffline(
    (status, update) => states.push({ status, update }),
    () => !state.editable,
  );
  return {
    state,
    states,
    messages,
    control,
    registration,
    candidate,
    serviceWorker,
    navigator,
    document,
    window,
    timers,
  };
}

test('fresh empty panel applies an already waiting complete update and reloads once', async () => {
  const p = setup();
  await settle();
  assert.ok(p.messages.includes('CAN_AUTO_UPDATE'));
  assert.equal(p.messages.filter((m) => m === 'APPLY_UPDATE').length, 1);
  p.serviceWorker.dispatchEvent(new Event('controllerchange'));
  p.serviceWorker.dispatchEvent(new Event('controllerchange'));
  assert.equal(p.state.reloads, 1);
});

test('session input, options, demos, results or conversion activity prevent automatic clearing', async () => {
  const p = setup({ editable: true });
  await settle();
  assert.deepEqual(p.messages, []);
  assert.deepEqual(p.states.at(-1), { status: 'ready', update: true });
  p.serviceWorker.dispatchEvent(new Event('controllerchange'));
  assert.equal(p.state.reloads, 0);
  p.control.applyUpdate();
  p.control.applyUpdate();
  assert.equal(p.messages.filter((m) => m === 'APPLY_UPDATE').length, 1);
  p.serviceWorker.dispatchEvent(new Event('controllerchange'));
  assert.equal(p.state.reloads, 1);
});

test('work entered while checking other tabs cancels the automatic update', async () => {
  const p = setup({
    probe: (state) => {
      state.editable = true;
    },
  });
  await settle();
  assert.ok(p.messages.includes('CAN_AUTO_UPDATE'));
  assert.ok(!p.messages.includes('APPLY_UPDATE'));
});

test('another controlled tab prevents automatic activation', async () => {
  const p = setup({ alone: false });
  await settle();
  assert.ok(!p.messages.includes('APPLY_UPDATE'));
  assert.equal(p.state.reloads, 0);
});

test('finishing initialization or clearing the workspace rechecks a pending update', async () => {
  const p = setup({ editable: true });
  await settle();
  p.state.editable = false;
  await p.control.check();
  assert.ok(p.messages.includes('APPLY_UPDATE'));
});

test('a newly installed update is checked without another page reload', async () => {
  const p = setup({ waiting: false });
  await settle();
  p.registration.installing = p.candidate;
  p.registration.dispatchEvent(new Event('updatefound'));
  p.registration.waiting = p.candidate;
  p.candidate.dispatchEvent(new Event('statechange'));
  await settle();
  assert.ok(p.messages.includes('APPLY_UPDATE'));
});

test('legacy workers that do not implement the probe still support the explicit update button', async () => {
  const p = setup({ legacy: true });
  await settle();
  for (const callback of [...p.timers.values()]) callback();
  await settle();
  assert.ok(!p.messages.includes('APPLY_UPDATE'));
  p.control.applyUpdate();
  assert.ok(p.messages.includes('APPLY_UPDATE'));
});

test('first installation never reloads the page just because it gains a controller', async () => {
  const p = setup({ waiting: false });
  await settle();
  p.serviceWorker.dispatchEvent(new Event('controllerchange'));
  assert.equal(p.state.reloads, 0);
  assert.deepEqual(p.states.at(-1), { status: 'ready', update: false });
});

test('update checks run on reopening and reconnecting, are throttled, and preserve the offline status', async () => {
  const p = setup({ waiting: false });
  await settle();
  assert.equal(p.state.updates, 1);
  p.document.dispatchEvent(new Event('visibilitychange'));
  assert.equal(p.state.updates, 1);
  p.state.now += 60001;
  p.document.visibilityState = 'hidden';
  p.document.dispatchEvent(new Event('visibilitychange'));
  assert.equal(p.state.updates, 1);
  p.document.visibilityState = 'visible';
  p.navigator.onLine = false;
  p.document.dispatchEvent(new Event('visibilitychange'));
  assert.equal(p.state.updates, 1);
  p.navigator.onLine = true;
  p.window.dispatchEvent(new Event('online'));
  assert.equal(p.state.updates, 2);
  p.state.now += 60001;
  p.registration.update = async () => {
    throw Error('server unavailable');
  };
  p.window.dispatchEvent(new Event('online'));
  await settle();
  assert.deepEqual(p.states.at(-1), { status: 'ready', update: false });
});

test('browsers without service workers receive harmless controls', async () => {
  const p = setup({ supported: false });
  assert.deepEqual(p.states, [{ status: 'unsupported', update: false }]);
  p.control.check();
  p.control.applyUpdate();
  assert.equal(p.state.reloads, 0);
});
