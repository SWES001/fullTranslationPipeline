let peerConnection = null;
let localStream = null;
let dataChannel = null;

const els = {
  startButton: document.querySelector('#startButton'),
  stopButton: document.querySelector('#stopButton'),
  clearLogButton: document.querySelector('#clearLogButton'),
  connectionDot: document.querySelector('#connectionDot'),
  connectionStatus: document.querySelector('#connectionStatus'),
  username: document.querySelector('#username'),
  sessionMode: document.querySelector('#sessionMode'),
  roomGroup: document.querySelector('#roomGroup'),
  roomId: document.querySelector('#roomId'),
  sourceLanguage: document.querySelector('#sourceLanguage'),
  targetLanguageGroup: document.querySelector('#targetLanguageGroup'),
  targetLanguage: document.querySelector('#targetLanguage'),
  modelName: document.querySelector('#modelName'),
  ttsModel: document.querySelector('#ttsModel'),
  asrModel: document.querySelector('#asrModel'),
  browserTts: document.querySelector('#browserTts'),
  voiceMatching: document.querySelector('#voiceMatching'),
  sourceTranscript: document.querySelector('#sourceTranscript'),
  translationTranscript: document.querySelector('#translationTranscript'),
  eventLog: document.querySelector('#eventLog'),
};

const TRANSLATIONS = {
  en: {
    select_language_title: "Select your language",
    eyebrow: "Real-time speech translator",
    subtitle: "Mic → WebRTC → ASR → translation → TTS.",
    username_label: "Username",
    username_placeholder: "e.g. Ben, Phone, Mac",
    session_mode_label: "Session Mode",
    mode_one_way: "One-way (Single Device)",
    mode_room: "Two-way Room (Multi-Device)",
    channel_label: "Channel",
    channel_prefix: "Channel",
    target_language_label: "Target language",
    lang_en: "English",
    lang_es: "Spanish",
    lang_ja: "Japanese",
    lang_zh: "Mandarin Chinese",
    asr_model_label: "ASR model",
    translation_model_label: "Translation model",
    tts_model_label: "TTS model",
    browser_tts_label: "Use browser TTS placeholder",
    voice_matching_label: "Enable voice matching placeholder",
    start_session: "Start session",
    stop_session: "Stop session",
    clear_log: "Clear",
    source_transcript_header: "Source transcript",
    source_transcript_waiting: "Waiting for speech...",
    translation_header: "Translation",
    translation_waiting: "Waiting for translated text...",
    event_log_header: "Event log",
    status_idle: "Idle",
    status_connecting: "Connecting",
    status_connected: "Connected",
    status_failed: "Failed"
  },
  es: {
    select_language_title: "Selecciona tu idioma",
    eyebrow: "Traductor de voz en tiempo real",
    subtitle: "Micrófono → WebRTC → ASR → Traducción → TTS.",
    username_label: "Nombre de usuario",
    username_placeholder: "ej. Ben, Teléfono, Mac",
    session_mode_label: "Modo de sesión",
    mode_one_way: "Unidireccional (Un dispositivo)",
    mode_room: "Sala bidireccional (Varios dispositivos)",
    channel_label: "Canal",
    channel_prefix: "Canal",
    target_language_label: "Idioma de destino",
    lang_en: "Inglés",
    lang_es: "Español",
    lang_ja: "Japonés",
    lang_zh: "Chino mandarín",
    asr_model_label: "Modelo ASR",
    translation_model_label: "Modelo de traducción",
    tts_model_label: "Modelo TTS",
    browser_tts_label: "Usar TTS del navegador",
    voice_matching_label: "Habilitar coincidencia de voz",
    start_session: "Iniciar sesión",
    stop_session: "Detener sesión",
    clear_log: "Limpiar",
    source_transcript_header: "Transcripción original",
    source_transcript_waiting: "Esperando voz...",
    translation_header: "Traducción",
    translation_waiting: "Esperando texto traducido...",
    event_log_header: "Registro de eventos",
    status_idle: "Inactivo",
    status_connecting: "Conectando",
    status_connected: "Conectado",
    status_failed: "Error"
  },
  ja: {
    select_language_title: "言語を選択してください",
    eyebrow: "リアルタイム音声翻訳機",
    subtitle: "マイク → WebRTC → ASR → 翻訳 → TTS",
    username_label: "ユーザー名",
    username_placeholder: "例: Ben, スマホ, Mac",
    session_mode_label: "セッションモード",
    mode_one_way: "一方通行 (単一デバイス)",
    mode_room: "双方向ルーム (複数デバイス)",
    channel_label: "チャンネル",
    channel_prefix: "チャンネル",
    target_language_label: "翻訳先言語",
    lang_en: "英語",
    lang_es: "スペイン語",
    lang_ja: "日本語",
    lang_zh: "中国語（普通話）",
    asr_model_label: "ASRモデル",
    translation_model_label: "翻訳モデル",
    tts_model_label: "TTSモデル",
    browser_tts_label: "ブラウザのTTSを使用",
    voice_matching_label: "音声マッチングを有効化",
    start_session: "セッション開始",
    stop_session: "セッション停止",
    clear_log: "クリア",
    source_transcript_header: "音声テキスト",
    source_transcript_waiting: "音声入力待ち...",
    translation_header: "翻訳結果",
    translation_waiting: "翻訳テキスト待ち...",
    event_log_header: "イベントログ",
    status_idle: "待機中",
    status_connecting: "接続中",
    status_connected: "接続完了",
    status_failed: "接続失敗"
  },
  zh: {
    select_language_title: "选择您的语言",
    eyebrow: "实时语音翻译器",
    subtitle: "麦克风 → WebRTC → ASR → 翻译 → TTS",
    username_label: "用户名",
    username_placeholder: "例如: Ben, 手机, Mac",
    session_mode_label: "会话模式",
    mode_one_way: "单向 (单设备)",
    mode_room: "双向房间 (多设备)",
    channel_label: "频道",
    channel_prefix: "频道",
    target_language_label: "目标语言",
    lang_en: "英语",
    lang_es: "西班牙语",
    lang_ja: "日语",
    lang_zh: "中文（普通话）",
    asr_model_label: "ASR模型",
    translation_model_label: "翻译模型",
    tts_model_label: "TTS模型",
    browser_tts_label: "使用浏览器TTS",
    voice_matching_label: "启用声音匹配",
    start_session: "开始会话",
    stop_session: "停止会话",
    clear_log: "清除",
    source_transcript_header: "原始语音",
    source_transcript_waiting: "等待语音输入...",
    translation_header: "翻译文本",
    translation_waiting: "等待翻译文本...",
    event_log_header: "事件日志",
    status_idle: "空闲",
    status_connecting: "连接中",
    status_connected: "已连接",
    status_failed: "连接失败"
  }
};

let currentLanguage = "en";

function setLanguage(lang) {
  currentLanguage = lang;
  if (els.sourceLanguage) {
    els.sourceLanguage.value = lang;
  }

  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });

  const t = TRANSLATIONS[lang] || TRANSLATIONS.en;

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (t[key]) {
      el.textContent = t[key];
    }
  });

  if (els.targetLanguage) {
    for (const option of els.targetLanguage.options) {
      const key = `lang_${option.value}`;
      if (t[key]) {
        option.text = t[key];
      }
    }
  }

  if (els.roomId) {
    const prefix = t.channel_prefix || "Channel";
    for (let i = 0; i < els.roomId.options.length; i++) {
      els.roomId.options[i].text = `${prefix} ${i + 1}`;
    }
  }

  if (els.username && t.username_placeholder) els.username.placeholder = t.username_placeholder;
  if (els.roomId && t.room_name_placeholder) els.roomId.placeholder = t.room_name_placeholder;

  if (els.sessionMode && els.sessionMode.options.length >= 2) {
    els.sessionMode.options[0].text = t.mode_one_way;
    els.sessionMode.options[1].text = t.mode_room;
  }

  const sourceWaitingEl = document.querySelector('#sourceTranscript.empty');
  if (sourceWaitingEl) sourceWaitingEl.textContent = t.source_transcript_waiting;

  const transWaitingEl = document.querySelector('#translationTranscript.empty');
  if (transWaitingEl) transWaitingEl.textContent = t.translation_waiting;

  localStorage.setItem('live_translator_language', lang);
  logEvent(`Language set to: ${lang.toUpperCase()}`);
}

document.querySelectorAll('.lang-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    setLanguage(btn.dataset.lang);
  });
});

const savedUsername = localStorage.getItem('live_translator_username') || `User-${Math.floor(100 + Math.random() * 900)}`;
els.username.value = savedUsername;
els.username.addEventListener('change', () => {
  if (els.username.value.trim()) {
    localStorage.setItem('live_translator_username', els.username.value.trim());
  }
});

function updateModeVisibility() {
  const isRoom = els.sessionMode.value === 'room';
  els.roomGroup.style.display = isRoom ? 'grid' : 'none';
  els.targetLanguageGroup.style.display = isRoom ? 'none' : 'grid';
}

els.sessionMode.addEventListener('change', updateModeVisibility);
updateModeVisibility();

// Initialize language from saved setting or default to English
const initialLang = localStorage.getItem('live_translator_language') || 'en';
setLanguage(initialLang);

function getClientId() {
  const customName = els.username.value.trim();
  if (customName) {
    localStorage.setItem('live_translator_username', customName);
    return customName;
  }
  let clientId = localStorage.getItem('live_translator_username');
  if (!clientId) {
    clientId = 'User-' + Math.floor(100 + Math.random() * 900);
    localStorage.setItem('live_translator_username', clientId);
  }
  return clientId;
}

els.startButton.addEventListener('click', () => {
  unlockAudio();
  startSession();
});
els.stopButton.addEventListener('click', stopSession);
els.clearLogButton.addEventListener('click', () => { els.eventLog.textContent = ''; });

async function startSession() {
  setStatus('connecting', 'Connecting');
  els.startButton.disabled = true;
  logEvent('Requesting microphone permission...');

  try {
    localStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
      video: false,
    });

    peerConnection = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
    });

    dataChannel = peerConnection.createDataChannel('events');
    dataChannel.onopen = () => logEvent('Data channel opened.');
    dataChannel.onmessage = (event) => handleServerEvent(event.data);
    dataChannel.onclose = () => logEvent('Data channel closed.');

    peerConnection.onconnectionstatechange = () => {
      const state = peerConnection.connectionState;
      logEvent(`Peer connection state: ${state}`);
      if (state === 'connected') setStatus('connected', 'Connected');
      if (state === 'failed' || state === 'disconnected') setStatus('failed', state);
    };

    peerConnection.oniceconnectionstatechange = () => {
      logEvent(`ICE connection state: ${peerConnection.iceConnectionState}`);
    };

    peerConnection.onicegatheringstatechange = () => {
      logEvent(`ICE gathering state: ${peerConnection.iceGatheringState}`);
    };

    for (const track of localStream.getAudioTracks()) {
      peerConnection.addTrack(track, localStream);
    }

    logEvent('Creating WebRTC offer and gathering local ICE candidates...');
    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);
    await waitForIceGatheringComplete(peerConnection);
    logEvent(`Local ICE gathering complete. Sending offer to remote server...`);

    const clientId = getClientId();
    const isRoom = els.sessionMode.value === 'room';
    const roomName = els.roomId.value.trim() || 'Testing Room';

    if (isRoom) {
      logEvent(`Joining Room: '${roomName}' as Client ID '${clientId}'`);
    } else {
      logEvent(`Starting One-way (Single Device) session`);
    }

    const response = await fetch('http://74.2.96.26:8000/offer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sdp: peerConnection.localDescription.sdp,
        type: peerConnection.localDescription.type,
        source_language: els.sourceLanguage.value,
        target_language: els.targetLanguage.value,
        model: els.modelName.value,
        asr_model: els.asrModel.value,
        tts_model: els.ttsModel.value,
        voice_matching: els.voiceMatching?.checked || false,
        session_mode: els.sessionMode.value,
        room_id: roomName,
        client_id: clientId,
      }),
    });

    if (!response.ok) {
      let errBody = "";
      try {
        errBody = await response.text();
      } catch (e) {}
      throw new Error(`Offer failed with status ${response.status} (${response.statusText}). Server Response: ${errBody}`);
    }

    const answer = await response.json();
    logEvent('Received SDP answer from remote server. Setting remote description...');
    await peerConnection.setRemoteDescription(answer);
    els.stopButton.disabled = false;
    logEvent('Session negotiation successful. WebRTC audio channel is open. Speak into the microphone.');
  } catch (error) {
    console.error("WebRTC Session Startup Error:", error);
    logEvent(`Error: ${error.message}`);
    setStatus('failed', 'Failed');
    await stopSession();
  }
}

async function stopSession() {
  els.stopButton.disabled = true;
  els.startButton.disabled = false;

  if (dataChannel) {
    dataChannel.close();
    dataChannel = null;
  }

  if (peerConnection) {
    peerConnection.close();
    peerConnection = null;
  }

  if (localStream) {
    for (const track of localStream.getTracks()) track.stop();
    localStream = null;
  }

  window.speechSynthesis?.cancel();
  setStatus('idle', 'Idle');
  logEvent('Session stopped.');
}

function handleServerEvent(rawData) {
  let message;
  try {
    message = JSON.parse(rawData);
  } catch {
    logEvent(`Non-JSON message: ${rawData}`);
    return;
  }

  if (message.type === 'self_caption') {
    if (message.source && message.source.text) {
      appendUtterance(els.sourceTranscript, `[You]: ${message.source.text}`);
    }
    if (message.translation && message.translation.text) {
      appendUtterance(els.translationTranscript, `[You -> ${message.translation.language}]: ${message.translation.text}`);
    }
    logEvent(`[Self caption]: ${message.source?.text} -> ${message.translation?.text}`);
    return;
  }

  if (message.type === 'translation') {
    const senderTag = message.sender_client_id ? `[${message.sender_client_id}] ` : '';
    appendUtterance(els.sourceTranscript, `${senderTag}${message.source.text}`);
    appendUtterance(els.translationTranscript, `${senderTag}${message.translation.text}`);

    const asrStr = message.asr_ms !== undefined ? `ASR: ${message.asr_ms}ms` : '';
    const transStr = message.trans_ms !== undefined ? `Trans: ${message.trans_ms}ms` : '';
    const ttftStr = message.ttft_ms !== undefined ? `TTFT: ${message.ttft_ms}ms` : '';
    const ttsStr = message.tts_ms !== undefined ? `TTS: ${message.tts_ms}ms` : '';
    const ttfaStr = message.ttfa_ms !== undefined ? `TTFA: ${message.ttfa_ms}ms` : '';

    const breakdown = [asrStr, transStr, ttftStr, ttsStr, ttfaStr].filter(Boolean).join(' | ');
    const breakdownMsg = breakdown ? ` [${breakdown}]` : '';

    logEvent(`Translated from ${senderTag || 'peer'}: ${message.translation.text}${breakdownMsg}`);

    if (els.browserTts.checked) {
      speak(message.translation.text, els.targetLanguage.value);
    } else if (message.audio && message.audio.data) {
      const audioUrl = `data:${message.audio.content_type};base64,${message.audio.data}`;
      const audio = new Audio(audioUrl);
      audio.play().catch(err => logEvent(`Audio play error: ${err.message}`));
    } else if (message.audio && message.audio.error) {
      logEvent(`TTS Error: ${message.audio.error}`);
    }
    return;
  }

  if (message.type === 'asr_partial') {
    const asrStr = message.asr_ms !== undefined ? ` [ASR: ${message.asr_ms}ms]` : '';
    logEvent(`ASR partial: ${message.source.text}${asrStr}`);
    return;
  }

  if (message.type === 'track_closed') {
    logEvent(`[Backend Track Closed] Audio track closed on server: ${message.detail}`);
    return;
  }

  logEvent(JSON.stringify(message));
}

function appendUtterance(container, text) {
  if (container.classList.contains('empty')) {
    container.classList.remove('empty');
    container.textContent = '';
  }
  const item = document.createElement('div');
  item.className = 'utterance';
  item.textContent = text;
  container.prepend(item);
}

function speak(text, language) {
  if (!('speechSynthesis' in window)) {
    logEvent('Browser speechSynthesis is not available.');
    return;
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = language === 'ja' ? 'ja-JP' : 'en-US';
  utterance.rate = 1.04;
  window.speechSynthesis.speak(utterance);
}

function setStatus(kind, label) {
  els.connectionDot.className = `dot ${kind}`;
  els.connectionStatus.textContent = label;
}

function logEvent(text) {
  const timestamp = new Date().toLocaleTimeString();
  els.eventLog.textContent = `[${timestamp}] ${text}\n` + els.eventLog.textContent;
}

function waitForIceGatheringComplete(pc) {
  if (pc.iceGatheringState === 'complete') return Promise.resolve();

  return new Promise((resolve) => {
    const timeout = setTimeout(resolve, 2000);
    function checkState() {
      if (pc.iceGatheringState === 'complete') {
        clearTimeout(timeout);
        pc.removeEventListener('icegatheringstatechange', checkState);
        resolve();
      }
    }
    pc.addEventListener('icegatheringstatechange', checkState);
  });
}


let unlockedAudioContext = null;

function unlockAudio() {
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (AudioContextClass) {
      unlockedAudioContext = new AudioContextClass();
      if (unlockedAudioContext.state === 'suspended') {
        unlockedAudioContext.resume();
      }
    }
    // Play a brief silent sound to unlock standard Audio tag autoplay in Chrome/Safari/iOS
    const silentBeep = new Audio("data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA==");
    silentBeep.play().catch(() => {});
  } catch (e) {
    logEvent(`Audio unlock warning: ${e.message}`);
  }
}

