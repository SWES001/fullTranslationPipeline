import asyncio
import json
from typing import Awaitable, Callable, Optional

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.rtcdatachannel import RTCDataChannel
from aiortc.mediastreams import MediaStreamTrack

from server.app.config import config
from server.app.pipeline.session import TranslationSession
from server.app.schemas import OfferRequest


PEER_CONNECTIONS: set[RTCPeerConnection] = set()


async def create_answer(request: OfferRequest) -> dict[str, str]:
    """Create a WebRTC answer for a browser offer.

    The starter receives the browser audio track and emits JSON events over a
    WebRTC data channel. Server-side TTS audio can be added later by adding
    a custom MediaStreamTrack back to the peer connection.
    """

    peer_connection = RTCPeerConnection()
    PEER_CONNECTIONS.add(peer_connection)

    session = TranslationSession(
        source_language=request.source_language,
        target_language=request.target_language,
        model_name=request.model,
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

        @channel.on("message")
        def on_message(message: str) -> None:
            # Add client-side commands here later, for example:
            # - update glossary
            # - change target language
            # - interrupt TTS playback
            print(f"client message: {message}")

    @peer_connection.on("track")
    def on_track(track: MediaStreamTrack) -> None:
        if track.kind == "audio":
            asyncio.create_task(consume_audio_track(track, session, emit))

    @peer_connection.on("connectionstatechange")
    async def on_connectionstatechange() -> None:
        if peer_connection.connectionState in {"failed", "closed", "disconnected"}:
            await peer_connection.close()
            PEER_CONNECTIONS.discard(peer_connection)

    offer = RTCSessionDescription(sdp=request.sdp, type=request.type)
    await peer_connection.setRemoteDescription(offer)
    answer = await peer_connection.createAnswer()
    await peer_connection.setLocalDescription(answer)

    return {
        "sdp": peer_connection.localDescription.sdp,
        "type": peer_connection.localDescription.type,
    }


async def consume_audio_track(
    track: MediaStreamTrack,
    session: TranslationSession,
    emit: Callable[[dict], Awaitable[None]],
) -> None:
    """Collect WebRTC audio frames and pass windows into the AI pipeline.

    aiortc decodes the browser's Opus audio and exposes PCM-like AudioFrame
    objects. The fake pipeline ignores the actual audio, but this function is
    where a real ASR implementation would resample and feed frames to the
    model.
    """

    frames = []
    accumulated_seconds = 0.0

    while True:
        try:
            frame = await track.recv()
        except Exception as exc:
            await emit({"type": "track_closed", "detail": str(exc)})
            return

        frames.append(frame)
        sample_rate = getattr(frame, "sample_rate", 48000) or 48000
        samples = getattr(frame, "samples", 0) or 0
        accumulated_seconds += samples / sample_rate

        if accumulated_seconds >= config.fake_chunk_seconds:
            event = await session.process_audio_window(frames)
            if event:
                await emit(event)
            frames = []
            accumulated_seconds = 0.0


async def shutdown_peer_connections() -> None:
    coroutines = [pc.close() for pc in PEER_CONNECTIONS]
    if coroutines:
        await asyncio.gather(*coroutines)
    PEER_CONNECTIONS.clear()
