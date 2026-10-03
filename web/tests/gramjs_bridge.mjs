// Native GramJS reader/writer. Requests use stdin; authorizations never enter argv.
import fs from 'node:fs';
import net from 'node:net';
import { createHash } from 'node:crypto';
import { StringSession } from 'telegram/sessions/index.js';
import { TelegramClient } from 'telegram';
import { AuthKey } from 'telegram/crypto/AuthKey.js';

const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const keyHash = (key) => createHash('sha256').update(key).digest('hex');
let client;
try {
  if (request.action !== 'live') {
    net.Socket.prototype.connect = () => {
      throw new Error('Offline GramJS must not connect');
    };
  }
  const session = new StringSession(request.session || '');
  await session.load();
  if (request.action === 'write') {
    session.setDC(request.dc, request.address, request.port);
    session.authKey = new AuthKey();
    await session.authKey.setKey(Buffer.from(request.key));
  }
  let result;
  if (request.action === 'live') {
    console.log = () => {};
    console.warn = () => {};
    console.error = () => {};
    if (keyHash(session.authKey.getKey()) !== request.expectedKeyHash)
      throw new Error('KeyMismatch');
    client = new TelegramClient(session, request.apiId, request.apiHash, {
      connectionRetries: 1,
      requestRetries: 1,
      autoReconnect: false,
      deviceModel: 'TGConvertor integration test',
      useIPV6: session.serverAddress.includes(':'),
    });
    client.setLogLevel('none');
    const deadline = setTimeout(() => {
      process.exit(2);
    }, 150000);
    try {
      await client.connect();
      const user = await client.getMe();
      if (!user || keyHash(session.authKey.getKey()) !== request.expectedKeyHash)
        throw new Error('KeyMismatch');
      result = { id: user.id.toString(), bot: !!user.bot };
    } finally {
      await client.destroy();
      client = undefined;
      clearTimeout(deadline);
    }
  } else {
    result = {
      dc: session.dcId,
      address: session.serverAddress,
      port: session.port,
      keyHash: keyHash(session.authKey.getKey()),
      session: session.save(),
    };
    // The native writer can produce ambiguous short addresses (e.g. ::1).
    // Python canonicalizes those before our exported string is read back.
    const reloaded = new StringSession(request.action === 'write' ? '' : result.session);
    await reloaded.load();
    if (request.action !== 'write' && keyHash(reloaded.authKey.getKey()) !== result.keyHash)
      throw new Error('KeyMismatch');
  }
  process.stdout.write(JSON.stringify(result));
} catch (error) {
  if (client) await client.destroy();
  // No exception message: RPC diagnostics may contain account information.
  process.stderr.write(error.constructor.name);
  process.exitCode = 1;
}
