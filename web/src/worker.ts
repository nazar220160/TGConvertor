/// <reference lib="webworker" />
import pythonSource from './browser_engine.py?raw';

const runtimeURL = new URL('../runtime/', self.location.href).href;
let interpreter: any;
let operation: any;

async function start() {
  self.postMessage({ type: 'progress', stage: 'python' });
  // Self-hosted assets are pinned at build time. No third-party requests in the app.
  const { loadPyodide } = await import(/* @vite-ignore */ `${runtimeURL}pyodide.mjs`);
  interpreter = await loadPyodide({ indexURL: runtimeURL, stdout: () => {}, stderr: () => {} });
  self.postMessage({ type: 'progress', stage: 'library' });
  await interpreter.loadPackage('pycryptodome');
  const manifest = await fetch(`${runtimeURL}manifest.json`).then((r) => {
    if (!r.ok) throw Error('runtime');
    return r.json();
  });
  const sitePackages = interpreter.runPython("import sysconfig; sysconfig.get_path('purelib')");
  for (const archive of manifest.archives) {
    const response = await fetch(`${runtimeURL}${archive}`);
    if (!response.ok) throw Error('package');
    interpreter.unpackArchive(new Uint8Array(await response.arrayBuffer()), 'zip', {
      extractDir: sitePackages,
    });
  }
  await interpreter.runPythonAsync(pythonSource);
  const version = interpreter.runPython('import TGConvertor; TGConvertor.__version__');
  if (version !== manifest.version) throw Error('Embedded library version mismatch');
  operation = interpreter.globals.get('operate');
  // Assets are now loaded; disable all network transports inside the worker.
  self.fetch = (() => Promise.reject(Error('Offline conversion'))) as typeof fetch;
  self.WebSocket = class {
    constructor() {
      throw Error('Offline conversion');
    }
  } as any;
  self.XMLHttpRequest = class {
    constructor() {
      throw Error('Offline conversion');
    }
  } as any;
  self.postMessage({ type: 'ready', version });
}

const ready = start().catch((error) => {
  if (import.meta.env.DEV) console.error('Converter startup:', error);
  self.postMessage({ type: 'boot-error', detail: import.meta.env.DEV ? String(error) : '' });
});
self.onmessage = async ({ data }) => {
  await ready;
  if (!operation) return;
  let result: any;
  let input: any;
  try {
    input = data.fileBytes ? interpreter.toPy(new Uint8Array(data.fileBytes)) : undefined;
    result = await operation(JSON.stringify(data.payload), input);
    const converted = result.toJs({ dict_converter: Object.fromEntries });
    if (converted.bytes) {
      converted.bytes = new Uint8Array(converted.bytes).slice();
      self.postMessage({ type: 'result', id: data.id, result: converted }, [
        converted.bytes.buffer,
      ]);
    } else {
      self.postMessage({ type: 'result', id: data.id, result: converted });
    }
  } catch {
    self.postMessage({
      type: 'result',
      id: data.id,
      result: { error: 'Unexpected conversion error' },
    });
  } finally {
    result?.destroy?.();
    input?.destroy?.();
  }
};
