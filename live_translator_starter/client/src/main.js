let peerConnection = null;
let localStream = null;
let dataChannel = null;

const els = {
  startButton: document.querySelector('#startButton'),
  stopButton: document.querySelector('#stopButton'),
  clearLogButton: document.querySelector('#clearLogButton'),
  connectionDot: document.querySelector('#connectionDot'),
  connectionStatus: document.querySelector('#connectionStatus'),
  sourceLanguage: document.querySelector('#sourceLanguage'),
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

    for (const track of localStream.getAudioTracks()) {
      peerConnection.addTrack(track, localStream);
    }

    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);
    await waitForIceGatheringComplete(peerConnection);

    const response = await fetch('/offer', {
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
        voice_matching: els.voiceMatching.checked,
      }),
    });

    if (!response.ok) {
      throw new Error(`Offer failed: ${response.status} ${response.statusText}`);
    }

    const answer = await response.json();
    await peerConnection.setRemoteDescription(answer);
    els.stopButton.disabled = false;
    logEvent('Session started. Speak into the microphone.');
  } catch (error) {
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

  if (message.type === 'translation') {
    appendUtterance(els.sourceTranscript, message.source.text);
    appendUtterance(els.translationTranscript, message.translation.text);
    const ttftStr = message.ttft_ms !== undefined ? ` [TTFT: ${message.ttft_ms}ms]` : '';
    const ttfaStr = message.ttfa_ms !== undefined ? ` [TTFA: ${message.ttfa_ms}ms]` : '';
    logEvent(`Translated with ${message.translation.model}: ${message.translation.text}${ttftStr}${ttfaStr}`);

    if (els.browserTts.checked) {
      speak(message.translation.text, els.targetLanguage.value);
    } else if (message.audio && message.audio.data) {
      const audioUrl = `data:${message.audio.content_type};base64,${message.audio.data}`;
      const audio = new Audio(audioUrl);
      audio.play().catch(err => logEvent(`Audio play error: ${err.message}`));
    }
    return;
  }

  if (message.type === 'asr_partial') {
    logEvent(`ASR partial: ${message.source.text}`);
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

