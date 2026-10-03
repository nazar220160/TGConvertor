import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const dist = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../dist');
const source = await fs.readFile(path.join(dist, 'sw.js'), 'utf8');
const scope = 'https://example.test/TGConvertor/';
const resources = JSON.parse(source.match(/const RESOURCES = (.*);\n/)[1]);
const bytes = new Map(
  await Promise.all(
    resources.map(async (file) => [
      new URL(file.path, scope).href,
      await fs.readFile(path.join(dist, file.path)),
    ]),
  ),
);

class Storage {
  stores = new Map();
  async keys() {
    return [...this.stores.keys()];
  }
  async delete(name) {
    return this.stores.delete(name);
  }
  async open(name) {
    if (!this.stores.has(name)) this.stores.set(name, new Map());
    const entries = this.stores.get(name);
    return {
      async put(url, response) {
        entries.set(url, response.clone());
      },
      async match(url) {
        return entries.get(url)?.clone();
      },
      async keys() {
        return [...entries.keys()];
      },
    };
  }
}
function worker({ storage = new Storage(), build = null, corrupt = null, fail = null } = {}) {
  const listeners = new Map();
  const state = { online: true, requests: [], skipped: 0, claimed: 0 };
  const code = build
    ? source.replace(/const BUILD_ID = .*;\n/, `const BUILD_ID = ${JSON.stringify(build)};\n`)
    : source;
  vm.runInNewContext(code, {
    URL,
    Uint8Array,
    crypto: webcrypto,
    caches: storage,
    self: {
      location: { href: scope + 'sw.js' },
      addEventListener(type, callback) {
        listeners.set(type, callback);
      },
      async skipWaiting() {
        state.skipped++;
      },
      clients: {
        async claim() {
          state.claimed++;
        },
      },
    },
    async fetch(input) {
      const url = typeof input === 'string' ? input : input.url;
      state.requests.push(url);
      if (!state.online) throw Error('Network disconnected');
      if (url === fail) return new Response('unavailable', { status: 404 });
      return new Response(url === corrupt ? 'invalid build bytes' : bytes.get(url));
    },
  });
  return {
    state,
    storage,
    async event(type, extra = {}) {
      let response;
      const promises = [];
      listeners.get(type)({
        waitUntil(value) {
          promises.push(value);
        },
        respondWith(value) {
          response = value;
        },
        ...extra,
      });
      await Promise.all(promises);
      return response ? await response : undefined;
    },
    async read(url, method = 'GET', mode = 'same-origin') {
      return this.event('fetch', { request: { url, method, mode } });
    },
  };
}

test('complete artifact is installed, then page and entire Python runtime reopen offline at a repository subpath', async () => {
  const w = worker();
  await w.event('install');
  await w.event('activate');
  assert.equal(w.state.claimed, 1);
  w.state.online = false;
  const before = w.state.requests.length;
  for (const file of resources) {
    const result = await w.read(new URL(file.path, scope).href);
    assert.deepEqual(
      Buffer.from(await result.arrayBuffer()),
      bytes.get(new URL(file.path, scope).href),
    );
  }
  assert.ok((await (await w.read(scope, 'GET', 'navigate')).text()).includes('id="app"'));
  assert.equal(w.state.requests.length, before, 'offline opening contacted the server');
  assert.ok(resources.some((file) => file.path.endsWith('.wasm')));
  assert.ok(resources.some((file) => file.path.includes('tgconvertor-')));
});

test('sessions, uploads, query strings, unrelated sites and Blob results are never handled or cached', async () => {
  const w = worker();
  await w.event('install');
  const before = w.state.requests.length;
  for (const [url, method] of [
    [scope + 'runtime/manifest.json', 'POST'],
    [scope + 'private.session', 'GET'],
    [scope + 'index.html?session=synthetic-secret', 'GET'],
    ['blob:' + scope + 'result', 'GET'],
    ['https://another.test/index.html', 'GET'],
  ])
    assert.equal(await w.read(url, method), undefined);
  assert.equal(w.state.requests.length, before);
  assert.ok(resources.every((file) => !/\.session$|web-fixtures|tdata_plain/.test(file.path)));
});

test('corrupt update is discarded atomically and existing offline copy survives', async () => {
  const old = worker();
  await old.event('install');
  const names = await old.storage.keys();
  const updated = worker({
    storage: old.storage,
    build: 'next-build',
    corrupt: scope + 'index.html',
  });
  await assert.rejects(updated.event('install'), /changed during installation/);
  assert.deepEqual(await old.storage.keys(), names);
  old.state.online = false;
  assert.ok(await old.read(scope, 'GET', 'navigate'));
});

test('a missing runtime asset prevents partial installation', async () => {
  const w = worker({ fail: scope + 'runtime/manifest.json' });
  await assert.rejects(w.event('install'), /unavailable/);
  assert.deepEqual(await w.storage.keys(), []);
});

test('updates wait for user action and activation preserves caches of other applications', async () => {
  const old = worker();
  await old.event('install');
  await old.storage.open('unrelated-app-cache');
  const update = worker({ storage: old.storage, build: 'next-build' });
  await update.event('install');
  assert.equal(update.state.skipped, 0, 'update interrupted an existing workspace');
  await update.event('message', { data: { type: 'APPLY_UPDATE' } });
  assert.equal(update.state.skipped, 1);
  await update.event('activate');
  const names = await update.storage.keys();
  assert.equal(names.length, 2);
  assert.ok(names.includes('unrelated-app-cache'));
  assert.ok(names.some((name) => name.endsWith('next-build')));
});

test('offline readiness is reported only for a complete cache', async () => {
  const w = worker();
  let message;
  const status = () =>
    w.event('message', {
      data: { type: 'OFFLINE_STATUS' },
      ports: [
        {
          postMessage(value) {
            message = value;
          },
        },
      ],
    });
  await status();
  assert.equal(message.ready, false);
  await w.event('install');
  await status();
  assert.equal(message.ready, true);
  w.storage.stores
    .values()
    .next()
    .value.delete(scope + 'runtime/pyodide.asm.wasm');
  await status();
  assert.equal(message.ready, false);
});
