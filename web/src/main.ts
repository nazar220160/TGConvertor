import './style.css';
import { registerOffline, type OfflineState } from './pwa';

type Language = 'en' | 'ru';
type Format = 'telethon' | 'pyrogram' | 'tdata';
type Result = {
  error?: string;
  metadata?: { dc: number; userId: string | null; apiId: number; bot: boolean; testMode: boolean };
  bytes?: Uint8Array;
  sessionString?: string;
  filename?: string;
};
const copy = {
  en: {
    offlineSaving: 'Saving the app for offline use…',
    offlineReady: 'Available offline · Python and app cached on this device',
    offlineRunning: 'You are offline · using the saved app and Python',
    offlineError: 'Offline copy unavailable. Reopen online to try again.',
    offlineUnsupported: 'Offline reopening requires service workers in a production build.',
    applyUpdate: 'Apply update and clear workspace',
    licenses: 'Licenses',
    schema: 'SQLite format',
    workspace: 'Session workspace',
    local: 'Runs on your device',
    nav: 'Converter',
    docs: 'Documentation',
    source: 'Source',
    destination: 'Destination',
    heading: 'A new format. The same session.',
    subheading: 'Move between Telegram clients, without moving your data off your device.',
    demo: 'Try a demo',
    privacy: 'Private by design',
    privacyText: 'Files stay in your browser. No upload, no account, no Telegram connection.',
    format: 'Session format',
    file: 'File',
    string: 'String',
    zip: 'ZIP archive',
    drop: 'Drop your session here',
    dropZip: 'Drop a tdata ZIP here',
    dropText: 'or choose a file from your device',
    choose: 'Choose file',
    limit: 'Up to 32 MB · processed locally',
    selected: 'Selected locally',
    pasted: 'Paste a session string',
    pasteHint: 'Your string stays in this tab.',
    demoTitle: 'A safe session to experiment with',
    demoText: 'This example uses a synthetic key and cannot log in to a Telegram account.',
    demoActive: 'Demo session selected',
    resultType: 'Output type',
    fileOutput: 'Session file',
    zipOutput: 'tdata ZIP',
    owner: 'Owner user ID',
    ownerHint:
      'Needed when converting a Telethon source to Pyrogram or tdata. Use the real account ID.',
    optional: 'If not stored in source',
    advanced: 'Additional options',
    advancedHint: 'Passcodes, account selection & API credentials',
    inputPass: 'Source tdata passcode',
    outputPass: 'Output tdata passcode',
    passHint: 'Local Desktop passcode (ASCII). Not your Telegram login password.',
    account: 'tdata account index',
    accountHint: 'Leave empty for the main account. Other accounts start at 0.',
    apiId: 'Custom API ID',
    apiHash: 'Custom API hash',
    apiHint: 'Optional: enter both fields to use your application identity.',
    clear: 'Clear workspace',
    inspect: 'Inspect source',
    convert: 'Convert session',
    converting: 'Converting locally…',
    inspecting: 'Reading local metadata…',
    initializing: 'Preparing local converter…',
    loadingPython: 'Loading local Python runtime…',
    loadingLibrary: 'Loading the conversion library…',
    ready: 'Ready · offline conversion',
    bootError: 'Could not start the converter. Reload the page and try again.',
    retry: 'Reload converter',
    noFile: 'Choose a session file first.',
    noString: 'Paste a session string first.',
    sizeError: 'Choose a nonempty file smaller than 32 MB.',
    noZip: 'Choose a ZIP archive containing the tdata folder.',
    noOwner: 'Enter the real owner user ID for this conversion.',
    badNumber: 'User ID must be a positive whole number.',
    converted: 'Conversion complete',
    inspected: 'Source information',
    resultHint: 'Your result is ready. Download it to keep a local copy.',
    download: 'Download result',
    copy: 'Copy string',
    copied: 'Copied',
    reveal: 'Show string',
    hide: 'Hide string',
    secretHidden: 'Session string hidden',
    secretHint: 'Reveal only when you need it. Downloading does not require revealing it.',
    dc: 'Data center',
    user: 'Owner ID',
    unknown: 'Not stored',
    environment: 'Environment',
    production: 'Production',
    test: 'Test server',
    accountType: 'Account type',
    bot: 'Bot',
    human: 'User',
    offline: 'Authorization is not checked online.',
    stepsTitle: 'One session. Four clients.',
    steps: [
      'Choose a file or paste a string.',
      'Select the format you need.',
      'Download the converted session.',
    ],
    footer: 'Free & open source',
    library: 'Powered by TGConvertor',
    helpTitle: 'A few things to know',
    help: 'Telethon usually does not store the owner ID. tdata requires a production user account; bot and test-server exports are rejected. Only the selected account is converted. Messages and cache are not transferred.',
    errorTitle: 'Check the source and options',
    reset: 'Workspace cleared',
    used: 'Session file · ZIP · session string',
    github: 'View source',
    support: 'Supported: Telethon 1.x · Pyrogram 2 · Kurigram 2 · Desktop tdata',
    clipboardError: 'Clipboard access is unavailable. Download the string instead.',
    encrypted: 'Local passcode protected',
    plain: 'No local passcode',
    metadataHint: 'Metadata is read locally and never sent to Telegram.',
  },
  ru: {
    offlineSaving: 'Сохраняем панель для работы без интернета…',
    offlineReady: 'Доступно офлайн · Python и панель сохранены на устройстве',
    offlineRunning: 'Вы офлайн · используем сохранённую панель и Python',
    offlineError: 'Офлайн-копия недоступна. Откройте панель с интернетом ещё раз.',
    offlineUnsupported: 'Офлайн-запуск требует service worker и production-сборку.',
    applyUpdate: 'Обновить и очистить панель',
    licenses: 'Лицензии',
    schema: 'Формат SQLite',
    workspace: 'Рабочее пространство',
    local: 'На вашем устройстве',
    nav: 'Конвертер',
    docs: 'Документация',
    source: 'Исходная сессия',
    destination: 'Результат',
    heading: 'Новый формат. Та же сессия.',
    subheading: 'Переносите сессии между клиентами Telegram, сохраняя данные на своём устройстве.',
    demo: 'Попробовать демо',
    privacy: 'Данные остаются у вас',
    privacyText:
      'Файлы обрабатываются в браузере. Без загрузки на сервер, регистрации и подключения к Telegram.',
    format: 'Формат сессии',
    file: 'Файл',
    string: 'Строка',
    zip: 'ZIP-архив',
    drop: 'Перетащите сессию сюда',
    dropZip: 'Перетащите ZIP с tdata',
    dropText: 'или выберите файл на устройстве',
    choose: 'Выбрать файл',
    limit: 'До 32 МБ · обработка локально',
    selected: 'Выбран локально',
    pasted: 'Вставьте строку сессии',
    pasteHint: 'Строка останется в этой вкладке.',
    demoTitle: 'Пример для экспериментов',
    demoText: 'В примере используется синтетический ключ. Войти в аккаунт Telegram с ним нельзя.',
    demoActive: 'Выбран пример сессии',
    resultType: 'Вид результата',
    fileOutput: 'Файл сессии',
    zipOutput: 'tdata в ZIP',
    owner: 'ID владельца аккаунта',
    ownerHint: 'Нужен при конвертации Telethon в Pyrogram или tdata. Укажите настоящий ID.',
    optional: 'Если не сохранён в сессии',
    advanced: 'Дополнительные параметры',
    advancedHint: 'Пароли, выбор аккаунта и API',
    inputPass: 'Пароль исходной tdata',
    outputPass: 'Пароль новой tdata',
    passHint: 'Локальный пароль Desktop (ASCII), не пароль входа в Telegram.',
    account: 'Номер аккаунта в tdata',
    accountHint: 'Оставьте пустым для основного аккаунта. Нумерация остальных — с 0.',
    apiId: 'Свой API ID',
    apiHash: 'Свой API hash',
    apiHint: 'Необязательно: заполните оба поля для своего приложения.',
    clear: 'Очистить',
    inspect: 'Проверить метаданные',
    convert: 'Конвертировать',
    converting: 'Конвертируем локально…',
    inspecting: 'Читаем метаданные…',
    initializing: 'Подготовка конвертера…',
    loadingPython: 'Загрузка Python…',
    loadingLibrary: 'Загрузка библиотеки…',
    ready: 'Готов · локальная конвертация',
    bootError: 'Не удалось запустить конвертер. Перезагрузите страницу и попробуйте снова.',
    retry: 'Перезапустить',
    noFile: 'Сначала выберите файл сессии.',
    noString: 'Сначала вставьте строку сессии.',
    sizeError: 'Выберите непустой файл до 32 МБ.',
    noZip: 'Выберите ZIP-архив с папкой tdata.',
    noOwner: 'Укажите настоящий ID владельца для этой конвертации.',
    badNumber: 'ID должен быть положительным целым числом.',
    converted: 'Конвертация завершена',
    inspected: 'Информация о сессии',
    resultHint: 'Скачайте результат, чтобы сохранить его на устройстве.',
    download: 'Скачать результат',
    copy: 'Копировать строку',
    copied: 'Скопировано',
    reveal: 'Показать строку',
    hide: 'Скрыть строку',
    secretHidden: 'Строка сессии скрыта',
    secretHint: 'Показывайте её только при необходимости. Для скачивания это не нужно.',
    dc: 'Дата-центр',
    user: 'ID владельца',
    unknown: 'Не сохранён',
    environment: 'Окружение',
    production: 'Основное',
    test: 'Тестовый сервер',
    accountType: 'Тип аккаунта',
    bot: 'Бот',
    human: 'Пользователь',
    offline: 'Авторизация в Telegram не проверяется.',
    stepsTitle: 'Одна сессия. Четыре клиента.',
    steps: [
      'Выберите файл или вставьте строку.',
      'Укажите нужный формат.',
      'Скачайте новую сессию.',
    ],
    footer: 'Бесплатно · открытый код',
    library: 'На базе TGConvertor',
    helpTitle: 'Полезно знать',
    help: 'Telethon обычно не хранит ID владельца. Экспорт в tdata доступен для обычных аккаунтов на основном сервере; боты и тестовые сессии не поддерживаются. Конвертируется выбранный аккаунт. Сообщения и кэш не переносятся.',
    errorTitle: 'Проверьте сессию и параметры',
    reset: 'Данные очищены',
    used: 'Файл сессии · ZIP · строка',
    github: 'Исходный код',
    support: 'Поддержка: Telethon 1.x · Pyrogram 2 · Kurigram 2 · Desktop tdata',
    clipboardError: 'Буфер обмена недоступен. Скачайте строку в файл.',
    encrypted: 'С локальным паролем',
    plain: 'Без локального пароля',
    metadataHint: 'Метаданные читаются локально, без запросов к Telegram.',
  },
};
let language: Language = navigator.language.startsWith('ru') ? 'ru' : 'en';
try {
  language = (localStorage.getItem('tgconvertor-language') as Language) || language;
} catch {
  /* optional preference */
}
if (!(language in copy)) language = 'en';
const t = (key: keyof typeof copy.en) => copy[language][key] as string;
const icon = (name: string, size = 20) => {
  const paths: Record<string, string> = {
    plane: '<path d="m3 10 18-7-6 18-4-7-8-4Zm8 4L21 3"/>',
    arrows: '<path d="M4 7h16m-4-4 4 4-4 4M20 17H4m4-4-4 4 4 4"/>',
    shield: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
    upload: '<path d="M12 16V3m-5 5 5-5 5 5M4 16v4h16v-4"/>',
    file: '<path d="M14 3H5v18h14V8l-5-5Zm0 0v5h5M8 13h8M8 17h5"/>',
    arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    download: '<path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>',
    book: '<path d="M12 6c-3-3-8-2-9-1v14c3-1 6-1 9 1 3-2 6-2 9-1V5c-3-1-6-1-9 1Zm0 0v14"/>',
    github:
      '<path d="M9 19c-5 1-5-3-7-3m14 6v-4c0-1-.3-2-1-2 4 0 6-2 6-5a5 5 0 0 0-1-3 4 4 0 0 0 0-4 7 7 0 0 0-4 2 13 13 0 0 0-8 0 7 7 0 0 0-4-2 4 4 0 0 0 0 4 5 5 0 0 0-1 3c0 3 2 5 6 5-.7.5-1 1-1 2v4"/>',
    spark: '<path d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3 3-7ZM20 2v4m-2-2h4"/>',
    trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
    eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    copy: '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/>',
  };
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.file}</svg>`;
};
const translate = (key: keyof typeof copy.en) => `<span data-i18n="${key}">${t(key)}</span>`;
const formats =
  '<option value="telethon">Telethon</option><option value="pyrogram">Pyrogram / Kurigram</option><option value="tdata">Telegram Desktop · tdata</option>';
document.querySelector('#app')!.innerHTML = `
<aside class="sidebar">
  <a class="brand" href="./" aria-label="TGConvertor"><span class="brand-mark">${icon('plane', 25)}</span><span>TGConvertor<small>SESSION TOOLS</small></span></a>
  <div class="sidebar-label">WORKSPACE</div>
  <a class="nav-item active" href="#converter">${icon('arrows')}${translate('nav')}<span class="nav-dot"></span></a>
  <a class="nav-item" href="https://github.com/nazar220160/TGConvertor#readme" target="_blank" rel="noopener noreferrer">${icon('book')}${translate('docs')}${icon('arrow', 14)}</a>
  <div class="sidebar-note"><span class="note-icon">${icon('shield', 23)}</span><strong>${translate('privacy')}</strong><p>${translate('privacyText')}</p><span class="local-pill"><i></i>${translate('local')}</span></div>
  <a class="sidebar-github" href="https://github.com/nazar220160/TGConvertor" target="_blank" rel="noopener noreferrer">${icon('github', 18)} GitHub ${icon('arrow', 14)}</a>
</aside>
<div class="main-wrap">
  <header class="topbar"><div class="breadcrumb">TGConvertor <span>/</span> ${translate('workspace')}</div><div class="topbar-right"><span id="library-version" class="version"></span><button id="language" class="language-button" type="button" aria-label="Switch language">${language === 'en' ? 'RU' : 'EN'}</button><a class="github-top" aria-label="GitHub" href="https://github.com/nazar220160/TGConvertor" target="_blank" rel="noopener noreferrer">${icon('github')}</a></div></header>
  <main id="converter">
    <section class="hero"><div><div class="eyebrow"><span class="status-dot" aria-hidden="true"></span>${translate('local')}</div><h1>${translate('heading')}</h1><p>${translate('subheading')}</p></div><button id="demo" class="secondary-button">${icon('spark', 18)}${translate('demo')}</button></section>
    <div class="status-row"><span id="runtime-status" role="status" aria-live="polite"><span class="spinner"></span><span id="runtime-text">${t('initializing')}</span></span><button id="retry" class="text-button" hidden>${translate('retry')}</button><span class="privacy-inline">${icon('lock', 14)}${translate('privacy')}</span></div>
    <div class="offline-bar"><span id="offline-cache-status" role="status" aria-live="polite"></span><button id="apply-update" class="text-button" hidden>${translate('applyUpdate')}</button></div>
    <div id="error" class="error-banner" role="alert" hidden></div>
    <section class="conversion-grid" aria-label="Converter">
      <article class="panel source-panel"><div class="panel-heading"><div class="heading-icon">${icon('upload')}</div><div><h2>${translate('source')}</h2><p>${translate('used')}</p></div><span class="step-number">01</span></div>
        <label class="field-label" for="source-format">${translate('format')}</label><select id="source-format">${formats}</select>
        <div class="segments" id="input-modes"><button data-mode="file" class="selected" type="button">${icon('file', 16)}<span id="input-file-label">${t('file')}</span></button><button data-mode="string" type="button">&lt;/&gt; ${translate('string')}</button></div>
        <div id="file-area"><div id="dropzone" class="dropzone" role="button" tabindex="0" aria-label="Choose session file"><span class="upload-icon">${icon('upload', 30)}</span><strong id="drop-title">${t('drop')}</strong><span id="drop-subtitle">${t('dropText')}</span><span class="choose-file">${translate('choose')} ${icon('arrow', 15)}</span><span class="file-limit">${translate('limit')}</span></div><input id="file-input" type="file" accept=".session,.db,.sqlite,.zip" class="visually-hidden" aria-label="Session file" /></div>
        <div id="string-area" hidden><label for="session-string" class="field-label">${translate('pasted')}</label><textarea id="session-string" rows="7" placeholder="1… / Ag…" spellcheck="false" autocomplete="off" autocapitalize="off"></textarea><p class="field-hint">${icon('lock', 12)} ${translate('pasteHint')}</p></div>
        <div id="demo-area" class="demo-area" hidden><span class="demo-orb">${icon('spark', 30)}</span><strong>${translate('demoTitle')}</strong><p>${translate('demoText')}</p><span class="demo-tag">${icon('check', 13)}${translate('demoActive')}</span></div>
      </article>
      <div class="flow-arrow">${icon('arrow', 22)}</div>
      <article class="panel target-panel"><div class="panel-heading"><div class="heading-icon target">${icon('download')}</div><div><h2>${translate('destination')}</h2><p>Telethon · Pyrogram · Kurigram · tdata</p></div><span class="step-number">02</span></div>
        <label class="field-label" for="target-format">${translate('format')}</label><select id="target-format">${formats}</select>
        <label class="field-label output-label">${translate('resultType')}</label><div class="segments" id="output-modes"><button data-output="file" class="selected" type="button">${icon('file', 16)}<span id="output-file-label">${t('fileOutput')}</span></button><button data-output="string" type="button">&lt;/&gt; ${translate('string')}</button></div>
        <div id="backend-field" class="field-row"><label class="field-label" for="backend">${translate('schema')}</label><select id="backend"><option value="kurigram">Kurigram 2</option><option value="pyrogram">Pyrogram 2</option></select></div>
        <div id="owner-field"><label class="field-label" for="user-id">${translate('owner')} <span class="optional-tag">${translate('optional')}</span></label><input id="user-id" type="text" inputmode="numeric" autocomplete="off" placeholder="123456789" /><p id="owner-hint" class="field-hint">${translate('ownerHint')}</p></div>
        <div class="target-note">${icon('shield', 19)}<p>${translate('privacyText')}</p></div>
      </article>
    </section>
    <details class="advanced"><summary><span class="advanced-icon">${icon('arrows', 17)}</span><span><strong>${translate('advanced')}</strong><small>${translate('advancedHint')}</small></span><span class="chevron">⌄</span></summary><div class="advanced-content"><div class="advanced-group" id="source-tdata-options"><label class="field-label" for="input-passcode">${translate('inputPass')}</label><input id="input-passcode" type="password" autocomplete="off" /><p class="field-hint">${translate('passHint')}</p><label class="field-label" for="account-index">${translate('account')}</label><input id="account-index" type="number" min="0" placeholder="Main" /><p class="field-hint">${translate('accountHint')}</p></div><div class="advanced-group" id="target-tdata-options"><label class="field-label" for="output-passcode">${translate('outputPass')}</label><input id="output-passcode" type="password" autocomplete="off" /><p class="field-hint">${translate('passHint')}</p></div><div class="advanced-group"><label class="field-label" for="api-id">${translate('apiId')}</label><input id="api-id" type="text" inputmode="numeric" autocomplete="off" placeholder="2040" /><label class="field-label" for="api-hash">${translate('apiHash')}</label><input id="api-hash" type="password" autocomplete="off" /><p class="field-hint">${translate('apiHint')}</p></div></div></details>
    <div class="action-bar"><button id="clear" class="text-button">${icon('trash', 16)}${translate('clear')}</button><div class="primary-actions"><button id="inspect" class="secondary-button" disabled>${icon('eye', 18)}${translate('inspect')}</button><button id="convert" class="primary-button" disabled>${translate('convert')}${icon('arrow', 18)}</button></div></div>
    <section id="result" class="result-panel" aria-live="polite" hidden><div class="result-header"><span class="success-icon">${icon('check', 22)}</span><div><h2 id="result-title"></h2><p id="result-hint"></p></div><span id="result-filename" class="filename-tag"></span></div><div id="metadata" class="metadata-grid"></div><div id="string-result" class="string-result" hidden><div id="hidden-string" class="hidden-string">${icon('lock', 18)}${translate('secretHidden')}</div><textarea id="output-string" readonly rows="3" spellcheck="false" hidden></textarea><div class="string-actions"><span>${translate('secretHint')}</span><button id="reveal" class="text-button">${translate('reveal')}</button><button id="copy" class="text-button">${icon('copy', 14)}${translate('copy')}</button></div></div><div id="download-row" class="download-row" hidden><p>${icon('lock', 14)}${translate('local')}</p><a id="download" class="primary-button" href="#" download>${icon('download', 17)}${translate('download')}</a></div><p class="offline-note">${icon('info', 13)}${translate('offline')}</p></section>
    <section class="how-it-works"><h3>${translate('stepsTitle')}</h3><div class="steps">${copy[language].steps.map((step, index) => `<div><span>${index + 1}</span><p data-step="${index}">${step}</p></div>`).join('')}</div></section>
    <details class="help"><summary>${icon('info', 15)}${translate('helpTitle')}<span>+</span></summary><p>${translate('help')}</p></details>
    <footer><span>${translate('footer')}<i>·</i>${translate('library')} <span id="footer-version"></span></span><a href="./THIRD-PARTY.txt" target="_blank" rel="noopener noreferrer">${translate('licenses')}</a><a href="https://github.com/nazar220160/TGConvertor" target="_blank" rel="noopener noreferrer">${translate('github')}${icon('arrow', 13)}</a></footer>
  </main>
</div>`;
const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const value = (id: string) => $<HTMLInputElement>(id).value.trim();
let inputMode: 'file' | 'string' | 'demo' = 'file';
let outputMode: 'file' | 'string' = 'file';
let selectedFile: File | null = null;
let worker: Worker;
let ready = false;
let busy = false;
let bootFailed = false;
let startupStage: 'initializing' | 'loadingPython' | 'loadingLibrary' = 'initializing';
let result: Result | null = null;
let downloadURL: string | null = null;
let requestId = 0;
let activeAction: 'inspect' | 'convert' = 'convert';
let startTime = 0;
let offlineState: OfflineState = 'saving';
let updateAvailable = false;
function showOfflineState() {
  const key = {
    saving: 'offlineSaving',
    ready: 'offlineReady',
    error: 'offlineError',
    unsupported: 'offlineUnsupported',
  } as const;
  $('offline-cache-status').textContent = t(
    offlineState === 'ready' && !navigator.onLine ? 'offlineRunning' : key[offlineState],
  );
  $('offline-cache-status').classList.toggle('is-ready', offlineState === 'ready');
  $('apply-update').hidden = !updateAvailable;
  $<HTMLButtonElement>('apply-update').disabled = busy;
}
const applyUpdate = registerOffline((state, update) => {
  offlineState = state;
  updateAvailable = update;
  showOfflineState();
});
$('apply-update').addEventListener('click', () => {
  if (!busy) applyUpdate();
});
window.addEventListener('online', showOfflineState);
window.addEventListener('offline', showOfflineState);
function updateButtons() {
  showOfflineState();
  $<HTMLButtonElement>('convert').disabled = !ready || busy;
  $<HTMLButtonElement>('inspect').disabled = !ready || busy;
  $('convert').innerHTML =
    busy && activeAction === 'convert'
      ? `<span class="spinner"></span>${t('converting')}`
      : `${t('convert')}${icon('arrow', 18)}`;
  $('inspect').innerHTML =
    busy && activeAction === 'inspect'
      ? `<span class="spinner"></span>${t('inspecting')}`
      : `${icon('eye', 18)}${t('inspect')}`;
  document
    .querySelectorAll<
      HTMLInputElement | HTMLSelectElement | HTMLButtonElement | HTMLTextAreaElement
    >('input, select, textarea, [data-mode], [data-output], #demo')
    .forEach((control) => (control.disabled = busy));
  $('dropzone').setAttribute('aria-disabled', String(busy));
  updateForm();
}
function clearResult() {
  if (downloadURL) URL.revokeObjectURL(downloadURL);
  downloadURL = null;
  result?.bytes?.fill(0);
  result = null;
  $('result').hidden = true;
  $<HTMLTextAreaElement>('output-string').value = '';
  $<HTMLAnchorElement>('download').removeAttribute('href');
}
function showError(message: string) {
  $('error').textContent = message;
  $('error').hidden = false;
}
function updateForm() {
  const source = value('source-format') as Format,
    target = value('target-format') as Format;
  if (source === 'tdata' && inputMode === 'string') inputMode = 'file';
  if (target === 'tdata') outputMode = 'file';
  $('file-area').hidden = inputMode !== 'file';
  $('string-area').hidden = inputMode !== 'string';
  $('demo-area').hidden = inputMode !== 'demo';
  $('input-modes').hidden = inputMode === 'demo';
  $<HTMLButtonElement>('input-modes').querySelector<HTMLButtonElement>(
    '[data-mode="string"]',
  )!.disabled = busy || source === 'tdata';
  $<HTMLButtonElement>('output-modes').querySelector<HTMLButtonElement>(
    '[data-output="string"]',
  )!.disabled = busy || target === 'tdata';
  document.querySelectorAll('[data-mode]').forEach((button) => {
    button.classList.toggle('selected', (button as HTMLElement).dataset.mode === inputMode);
    button.setAttribute('aria-pressed', String((button as HTMLElement).dataset.mode === inputMode));
  });
  document.querySelectorAll('[data-output]').forEach((button) => {
    button.classList.toggle('selected', (button as HTMLElement).dataset.output === outputMode);
    button.setAttribute(
      'aria-pressed',
      String((button as HTMLElement).dataset.output === outputMode),
    );
  });
  $('input-file-label').textContent = t(source === 'tdata' ? 'zip' : 'file');
  $('output-file-label').textContent = t(target === 'tdata' ? 'zipOutput' : 'fileOutput');
  $('drop-title').textContent = selectedFile?.name || t(source === 'tdata' ? 'dropZip' : 'drop');
  $('drop-subtitle').textContent = selectedFile
    ? `${(selectedFile.size / 1024).toFixed(1)} KB · ${t('selected')}`
    : t('dropText');
  $('dropzone').classList.toggle('has-file', !!selectedFile);
  $<HTMLInputElement>('file-input').accept = source === 'tdata' ? '.zip' : '.session,.db,.sqlite';
  $('backend-field').hidden = target !== 'pyrogram';
  $('owner-field').hidden = target === 'telethon';
  $('owner-hint').hidden = source !== 'telethon';
  $('source-tdata-options').hidden = source !== 'tdata';
  $('target-tdata-options').hidden = target !== 'tdata';
}
function setFile(file: File) {
  if (busy) return;
  clearResult();
  $('error').hidden = true;
  if (!file.size || file.size > 32 * 1024 * 1024) {
    showError(t('sizeError'));
    return;
  }
  if (value('source-format') === 'tdata' && !file.name.toLowerCase().endsWith('.zip')) {
    showError(t('noZip'));
    return;
  }
  selectedFile = file;
  inputMode = 'file';
  updateForm();
}
function displayResult() {
  if (!result) return;
  if (result.error) {
    showError(result.error);
    return;
  }
  $('result').hidden = false;
  const downloadable = !!(result.bytes || result.sessionString);
  $('result-title').textContent = t(downloadable ? 'converted' : 'inspected');
  $('result-hint').textContent = t(downloadable ? 'resultHint' : 'metadataHint');
  $('result-filename').textContent = result.filename || '';
  $('result-filename').hidden = !result.filename;
  const info = result.metadata!;
  const entries = [
    [t('dc'), String(info.dc)],
    [t('user'), info.userId || t('unknown')],
    [t('environment'), t(info.testMode ? 'test' : 'production')],
    [t('accountType'), t(info.bot ? 'bot' : 'human')],
  ];
  $('metadata').replaceChildren(
    ...entries.map(([label, data]) => {
      const item = document.createElement('div'),
        key = document.createElement('span'),
        text = document.createElement('strong');
      key.textContent = label;
      text.textContent = data;
      item.append(key, text);
      return item;
    }),
  );
  if (info.userId && !value('user-id')) $<HTMLInputElement>('user-id').value = info.userId;
  $('string-result').hidden = !result.sessionString;
  $('hidden-string').hidden = false;
  $('output-string').hidden = true;
  $<HTMLTextAreaElement>('output-string').value = result.sessionString || '';
  $('reveal').textContent = t('reveal');
  $('download-row').hidden = !downloadable;
  if (downloadable) {
    if (downloadURL) URL.revokeObjectURL(downloadURL);
    const bytes = result.bytes ? new Uint8Array(result.bytes).buffer : result.sessionString! + '\n';
    downloadURL = URL.createObjectURL(
      new Blob([bytes], {
        type: result.sessionString ? 'text/plain;charset=utf-8' : 'application/octet-stream',
      }),
    );
    const link = $<HTMLAnchorElement>('download');
    link.href = downloadURL;
    link.download = result.filename!;
  }
}
function initialize() {
  worker?.terminate();
  ready = false;
  busy = false;
  bootFailed = false;
  startupStage = 'initializing';
  $('retry').hidden = true;
  $('runtime-status').classList.remove('is-ready', 'is-error');
  $('runtime-text').textContent = t('initializing');
  updateButtons();
  worker = new Worker(new URL('./worker.ts', import.meta.url), { type: 'module' });
  worker.onmessage = ({ data }) => {
    if (data.type === 'progress') {
      startupStage = data.stage === 'python' ? 'loadingPython' : 'loadingLibrary';
      $('runtime-text').textContent = t(startupStage);
    }
    if (data.type === 'ready') {
      ready = true;
      $('library-version').textContent = `v${data.version}`;
      $('footer-version').textContent = data.version;
      $('runtime-status').classList.add('is-ready');
      $('runtime-text').textContent = t('ready');
      updateButtons();
    }
    if (data.type === 'boot-error') bootError(data.detail);
    if (data.type === 'result' && data.id === requestId) {
      busy = false;
      result = data.result;
      updateButtons();
      displayResult();
      if (!result?.error)
        $('result').scrollIntoView({
          behavior: performance.now() - startTime > 2000 ? 'smooth' : 'auto',
          block: 'nearest',
        });
    }
  };
  worker.onerror = (error) => {
    if (import.meta.env.DEV) console.error('Converter worker:', error.message);
    bootError(error.message);
  };
}
function bootError(detail = '') {
  ready = false;
  busy = false;
  bootFailed = true;
  $('retry').hidden = false;
  $('runtime-status').classList.add('is-error');
  $('runtime-text').textContent = t('bootError') + (import.meta.env.DEV ? ' ' + detail : '');
  updateButtons();
}
async function submit(action: 'inspect' | 'convert') {
  if (!ready || busy) {
    if (bootFailed) initialize();
    return;
  }
  $('error').hidden = true;
  clearResult();
  if (inputMode === 'file' && !selectedFile) {
    showError(t('noFile'));
    return;
  }
  if (inputMode === 'string' && !value('session-string')) {
    showError(t('noString'));
    return;
  }
  const userId = value('user-id');
  if (
    userId &&
    (!/^\d+$/.test(userId) || BigInt(userId) < 1n || BigInt(userId) > 9223372036854775807n)
  ) {
    showError(t('badNumber'));
    return;
  }
  if (
    action === 'convert' &&
    inputMode !== 'demo' &&
    value('source-format') === 'telethon' &&
    value('target-format') !== 'telethon' &&
    !userId
  ) {
    showError(t('noOwner'));
    $<HTMLInputElement>('user-id').focus();
    return;
  }
  activeAction = action;
  busy = true;
  startTime = performance.now();
  updateButtons();
  const id = ++requestId,
    activeWorker = worker,
    activeFile = selectedFile;
  const payload = {
    action,
    sourceFormat: value('source-format'),
    targetFormat: value('target-format'),
    inputMode,
    outputMode,
    backend: value('backend'),
    sessionString: inputMode === 'string' ? value('session-string') : '',
    options: {
      userId,
      passcode: $<HTMLInputElement>('input-passcode').value,
      outputPasscode: $<HTMLInputElement>('output-passcode').value,
      accountIndex: value('account-index'),
      apiId: value('api-id'),
      apiHash: value('api-hash'),
    },
  };
  try {
    const fileBytes = inputMode === 'file' ? await activeFile!.arrayBuffer() : undefined;
    if (id !== requestId || activeWorker !== worker) return;
    activeWorker.postMessage({ id, payload, fileBytes }, fileBytes ? [fileBytes] : []);
  } catch {
    busy = false;
    updateButtons();
    showError(t('noFile'));
  }
}
$('source-format').addEventListener('change', () => {
  selectedFile = null;
  $<HTMLInputElement>('file-input').value = '';
  clearResult();
  updateForm();
});
$('target-format').addEventListener('change', () => {
  clearResult();
  updateForm();
});
$('backend').addEventListener('change', clearResult);
document.querySelectorAll<HTMLElement>('[data-mode]').forEach((button) =>
  button.addEventListener('click', () => {
    inputMode = button.dataset.mode as 'file' | 'string';
    clearResult();
    updateForm();
  }),
);
document.querySelectorAll<HTMLElement>('[data-output]').forEach((button) =>
  button.addEventListener('click', () => {
    outputMode = button.dataset.output as 'file' | 'string';
    clearResult();
    updateForm();
  }),
);
$('demo').addEventListener('click', () => {
  inputMode = 'demo';
  selectedFile = null;
  $<HTMLInputElement>('user-id').value = '123456789';
  $('error').hidden = true;
  clearResult();
  updateForm();
});
$('dropzone').addEventListener('click', () => {
  if (!busy) $<HTMLInputElement>('file-input').click();
});
$('dropzone').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    $<HTMLInputElement>('file-input').click();
  }
});
$('file-input').addEventListener('change', () => {
  const file = $<HTMLInputElement>('file-input').files?.[0];
  if (file) setFile(file);
});
$('dropzone').addEventListener('dragover', (e) => {
  e.preventDefault();
  $('dropzone').classList.add('drag-over');
});
$('dropzone').addEventListener('dragleave', () => $('dropzone').classList.remove('drag-over'));
$('dropzone').addEventListener('drop', (e) => {
  e.preventDefault();
  $('dropzone').classList.remove('drag-over');
  const file = e.dataTransfer?.files[0];
  if (file) setFile(file);
});
$('convert').addEventListener('click', () => submit('convert'));
$('inspect').addEventListener('click', () => submit('inspect'));
$('retry').addEventListener('click', initialize);
$('clear').addEventListener('click', () => {
  ++requestId;
  selectedFile = null;
  inputMode = 'file';
  outputMode = 'file';
  clearResult();
  [
    'file-input',
    'session-string',
    'user-id',
    'input-passcode',
    'output-passcode',
    'account-index',
    'api-id',
    'api-hash',
  ].forEach((id) => ($<HTMLInputElement>(id).value = ''));
  $('error').hidden = true;
  updateForm();
  initialize();
});
$('reveal').addEventListener('click', () => {
  const reveal = $('output-string').hidden;
  $('output-string').hidden = !reveal;
  $('hidden-string').hidden = reveal;
  $('reveal').textContent = t(reveal ? 'hide' : 'reveal');
});
$('copy').addEventListener('click', async () => {
  if (!result?.sessionString) return;
  try {
    await navigator.clipboard.writeText(result.sessionString);
    $('copy').textContent = t('copied');
  } catch {
    showError(t('clipboardError'));
  }
});
$('language').addEventListener('click', () => {
  language = language === 'en' ? 'ru' : 'en';
  document.documentElement.lang = language;
  try {
    localStorage.setItem('tgconvertor-language', language);
  } catch {
    /* preferences only */
  }
  document
    .querySelectorAll<HTMLElement>('[data-i18n]')
    .forEach((element) => (element.textContent = t(element.dataset.i18n as keyof typeof copy.en)));
  document
    .querySelectorAll<HTMLElement>('[data-step]')
    .forEach(
      (element) => (element.textContent = copy[language].steps[Number(element.dataset.step)]),
    );
  $('language').textContent = language === 'en' ? 'RU' : 'EN';
  if (ready) $('runtime-text').textContent = t('ready');
  else if (bootFailed) $('runtime-text').textContent = t('bootError');
  else $('runtime-text').textContent = t(startupStage);
  updateForm();
  updateButtons();
  displayResult();
  showOfflineState();
});
document.documentElement.lang = language;
$<HTMLSelectElement>('target-format').value = 'pyrogram';
updateForm();
initialize();
