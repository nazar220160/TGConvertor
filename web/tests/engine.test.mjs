import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadPyodide } from 'pyodide';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fixtures = path.resolve(process.argv[2] || path.join(root, '../.test-envs/web-fixtures'));
const py = await loadPyodide({
  indexURL: path.join(root, 'public/runtime/'),
  stdout() {},
  stderr() {},
});
await py.loadPackage('pycryptodome');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'public/runtime/manifest.json')));
const sitePackages = py.runPython("import sysconfig; sysconfig.get_path('purelib')");
for (const name of manifest.archives)
  py.unpackArchive(
    new Uint8Array(fs.readFileSync(path.join(root, 'public/runtime/', name))),
    'zip',
    { extractDir: sitePackages },
  );
await py.runPythonAsync(fs.readFileSync(path.join(root, 'src/browser_engine.py'), 'utf8'));
const operation = py.globals.get('operate');
const strings = JSON.parse(fs.readFileSync(path.join(fixtures, 'strings.json')));
const native = JSON.parse(fs.readFileSync(path.join(fixtures, 'crypto.json')));
py.globals.set('vectors_json', JSON.stringify(native));
py.runPython(`
vectors = json.loads(vectors_json)
assert ige(bytes(vectors['data']), bytes(vectors['key']), bytes(vectors['iv'])) == bytes(vectors['encrypted'])
assert ige(bytes(vectors['encrypted']), bytes(vectors['key']), bytes(vectors['iv']), True) == bytes(vectors['data'])
assert pbkdf2_hmac('sha512', b'local-passcode', b'test-salt', 120, 256) == bytes(vectors['pbkdf2'])
`);

const kinds = [
  'telethon_file',
  'telethon_string',
  'pyrogram_file',
  'kurigram_file',
  'pyrogram_string',
  'tdata_plain',
  'tdata_encrypted',
];
const format = (kind) =>
  kind.startsWith('telethon') ? 'telethon' : kind.startsWith('tdata') ? 'tdata' : 'pyrogram';
const inputFile = (kind) => (kind.startsWith('tdata') ? kind + '.zip' : kind + '.session');
let passed = 0;
const outputs = [];
async function call(payload, buffer) {
  const input = buffer ? py.toPy(new Uint8Array(buffer)) : undefined;
  let result;
  try {
    result = await operation(JSON.stringify(payload), input);
    const converted = result.toJs({ dict_converter: Object.fromEntries });
    if (converted.bytes) converted.bytes = new Uint8Array(converted.bytes).slice();
    return converted;
  } finally {
    result?.destroy();
    input?.destroy();
  }
}
for (const source of kinds)
  for (const target of kinds) {
    const payload = {
      sourceFormat: format(source),
      targetFormat: format(target),
      inputMode: source.endsWith('string') ? 'string' : 'file',
      sessionString: strings[source] || '',
      outputMode: target.endsWith('string') ? 'string' : 'file',
      backend: target === 'kurigram_file' ? 'kurigram' : 'pyrogram',
      options: {
        userId: '1099511627793',
        passcode: source === 'tdata_encrypted' ? 'source-local-passcode' : '',
        outputPasscode: target === 'tdata_encrypted' ? 'different-output-passcode' : '',
      },
    };
    const input =
      payload.inputMode === 'file'
        ? fs.readFileSync(path.join(fixtures, inputFile(source)))
        : undefined;
    const result = await call(payload, input);
    assert.equal(result.error, undefined, `${source} → ${target}: ${result.error}`);
    const name = `${source}--${target}`;
    if (result.bytes) fs.writeFileSync(path.join(fixtures, 'outputs', name), result.bytes);
    else fs.writeFileSync(path.join(fixtures, 'outputs', name), result.sessionString);
    outputs.push({ file: name, target, passcode: payload.options.outputPasscode });
    const inspect = await call(
      {
        action: 'inspect',
        sourceFormat: format(target),
        inputMode: target.endsWith('string') ? 'string' : 'file',
        sessionString: result.sessionString || '',
        options: { passcode: payload.options.outputPasscode },
      },
      result.bytes,
    );
    assert.equal(inspect.error, undefined, `${name}: inspect`);
    assert.equal(inspect.metadata.dc, 2);
    assert.equal(
      inspect.metadata.userId ?? null,
      format(target) === 'telethon' ? null : '1099511627793',
    );
    passed++;
  }
fs.writeFileSync(path.join(fixtures, 'outputs/manifest.json'), JSON.stringify(outputs));

// All demo modes use the real API and never represent a real authorization.
for (const source of ['telethon', 'pyrogram', 'tdata'])
  for (const target of ['telethon', 'pyrogram', 'tdata']) {
    const result = await call({
      sourceFormat: source,
      targetFormat: target,
      inputMode: 'demo',
      outputMode: 'file',
      options: {},
    });
    assert.equal(result.error, undefined, `demo ${source} → ${target}`);
    assert.ok(result.bytes.length);
    passed++;
  }
for (const sourceFormat of ['telethon', 'pyrogram']) {
  const result = await call({
    sourceFormat,
    targetFormat: 'telethon',
    inputMode: 'string',
    sessionString: 'private-invalid-input',
    outputMode: 'string',
    options: {},
  });
  assert.ok(result.error);
  assert.ok(!result.error.includes('private-invalid-input'));
  passed++;
}
assert.ok(
  (
    await call(
      {
        sourceFormat: 'tdata',
        targetFormat: 'telethon',
        inputMode: 'file',
        outputMode: 'file',
        options: {},
      },
      new Uint8Array([1, 2, 3]),
    )
  ).error,
);
assert.ok(
  (
    await call({
      sourceFormat: 'telethon',
      targetFormat: 'pyrogram',
      inputMode: 'string',
      sessionString: strings.telethon_string,
      outputMode: 'file',
      options: {},
    })
  ).error,
);
assert.ok(
  (
    await call(
      {
        sourceFormat: 'tdata',
        targetFormat: 'telethon',
        inputMode: 'file',
        outputMode: 'file',
        options: { passcode: 'wrong' },
      },
      fs.readFileSync(path.join(fixtures, 'tdata_encrypted.zip')),
    )
  ).error,
);
passed += 3;
for (const file of fs.readdirSync(path.join(fixtures, 'invalid'))) {
  const rejected = await call(
    {
      sourceFormat: 'tdata',
      targetFormat: 'telethon',
      inputMode: 'file',
      outputMode: 'file',
      options: {},
    },
    fs.readFileSync(path.join(fixtures, 'invalid', file)),
  );
  assert.ok(rejected.error, `unsafe ZIP accepted: ${file}`);
  passed++;
}
assert.ok(
  (
    await call({
      sourceFormat: 'telethon',
      targetFormat: 'telethon',
      inputMode: 'string',
      sessionString: 'x'.repeat(513),
      outputMode: 'string',
      options: {},
    })
  ).error,
);
assert.ok(
  (
    await call({
      sourceFormat: 'telethon',
      targetFormat: 'telethon',
      inputMode: 'demo',
      outputMode: 'string',
      options: { apiId: '12345' },
    })
  ).error,
);
const custom = await call({
  sourceFormat: 'telethon',
  targetFormat: 'pyrogram',
  inputMode: 'demo',
  outputMode: 'string',
  options: { apiId: '12345', apiHash: '0123456789abcdef0123456789abcdef' },
});
assert.equal(custom.metadata.apiId, 12345);
passed += 3;
py.runPython(`
try:
    socket.socket().connect(('127.0.0.1', 80))
except OSError:
    pass
else:
    raise AssertionError('Python network transport was not blocked')
`);
assert.equal(
  py.runPython(
    "len([p for p in Path(tempfile.gettempdir()).iterdir() if p.name.startswith('tgconvertor-browser-')])",
  ),
  0,
);
operation.destroy();
console.log(
  `Browser Python: ${passed} conversion/error tests passed; AES-IGE and PBKDF2 match native vectors; temporary files cleaned.`,
);
