import asyncio
import json
from typing import Awaitable, Callable, Optional

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.rtcdatachannel import RTCDataChannel
from aiortc.mediastreams import MediaStreamTrack
import av

from server.app.config import config
from server.app.pipeline.session import TranslationSession
from server.app.schemas import OfferRequest
from server.app.pipeline.vad import WebRTCEndpointDetector


PEER_CONNECTIONS: set[RTCPeerConnection] = set()


async def create_answer(request: OfferRequest) -> dict[str, str]:
    """Create a WebRTC answer for a browser offer.

    The starter receives the browser audio track and emits JSON events over a
    WebRTC data channel. Server-side TTS audio can be added later by adding
    a custom MediaStreamTrack back to the peer connection.
    """
    print(f"[WebRTC] Creating answer for session: asr={request.asr_model}, tts={request.tts_model}, translator={request.model}")

    peer_connection = RTCPeerConnection()
    PEER_CONNECTIONS.add(peer_connection)

    session = TranslationSession(
        source_language=request.source_language,
        target_language=request.target_language,
        model_name=request.model,
        asr_model=request.asr_model,
        tts_model=request.tts_model,
        voice_matching=request.voice_matching,
    )
    data_channel: Optional[RTCDataChannel] = None

    async def emit(message: dict) -> None:
        if data_channel and data_channel.readyState == "open":
            data_channel.send(json.dumps(message, ensure_ascii=False))

    @peer_connection.on("datachannel")
    def on_datachannel(channel: RTCDataChannel) -> None:
        nonlocal data_channel
        data_channel = channel
        print(f"[WebRTC] Data channel opened: {channel.label}")

        @channel.on("message")
        def on_message(message: str) -> None:
            # Add client-side commands here later, for example:
            # - update glossary
            # - change target language
            # - interrupt TTS playback
            print(f"[WebRTC] Client data channel message: {message}")

    @peer_connection.on("track")
    def on_track(track: MediaStreamTrack) -> None:
        print(f"[WebRTC] Received track: kind={track.kind}")
        if track.kind == "audio":
            asyncio.create_task(consume_audio_track(track, session, emit))

    @peer_connection.on("connectionstatechange")
    async def on_connectionstatechange() -> None:
        state = peer_connection.connectionState
        print(f"[WebRTC] Peer connection state changed to: {state}")
        if state in {"failed", "closed", "disconnected"}:
            await peer_connection.close()
            PEER_CONNECTIONS.discard(peer_connection)

    offer = RTCSessionDescription(sdp=request.sdp, type=request.type)
    await peer_connection.setRemoteDescription(offer)
    answer = await peer_connection.createAnswer()
    await peer_connection.setLocalDescription(answer)

    print("[WebRTC] Signaling handshake complete (remote SDP set, answer SDP generated)")
    return {
        "sdp": peer_connection.localDescription.sdp,
        "type": peer_connection.localDescription.type,
    }


async def consume_audio_track(
    track: MediaStreamTrack,
    session: TranslationSession,
    emit: Callable[[dict], Awaitable[None]],
) -> None:
    """Collect WebRTC audio frames, run VAD, and feed sentences to ASR."""
    print("[WebRTC] Starting consume_audio_track background worker loop")

    frames = []
    detector = WebRTCEndpointDetector()
    
    # We resample browser audio to 16kHz mono (standard format for VAD and ASR)
    resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)

    while True:
        try:
            frame = await track.recv()
        except Exception as exc:
            print(f"[WebRTC] Audio track stream ended / closed: {exc}")
            await emit({"type": "track_closed", "detail": str(exc)})
            return

        # Resample the browser's raw audio frame
        resampled_frames = resampler.resample(frame)
        
        for r_frame in resampled_frames:
            # Convert audio samples to raw bytes
            pcm_bytes = r_frame.to_ndarray().tobytes()
            
            # Feed bytes into VAD to check if user is speaking or silent
            endpoint_triggered = detector.process_audio_chunk(pcm_bytes)
            
            # If the user is speaking, accumulate the frame
            if detector.in_speech:
                frames.append(r_frame)
                
            # If the user stopped speaking (endpoint triggered), send to ASR!
            if endpoint_triggered:
                if frames:
                    print(f"[WebRTC] VAD endpoint triggered. Transcribing {len(frames)} audio frames...")
                    event = await session.process_audio_window(frames)
                    if event:
                        await emit(event)
                    frames = []


async def shutdown_peer_connections() -> None:
    coroutines = [pc.close() for pc in PEER_CONNECTIONS]
    if coroutines:
        await asyncio.gather(*coroutines)
    PEER_CONNECTIONS.clear()
