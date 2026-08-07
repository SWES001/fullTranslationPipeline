import asyncio
import json
from uuid import uuid4
from typing import Awaitable, Callable, Optional

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.rtcdatachannel import RTCDataChannel
from aiortc.mediastreams import MediaStreamTrack
import av
from fastapi import HTTPException

from server.app.config import config
from server.app.pipeline.session import TranslationSession
from server.app.schemas import OfferRequest
from server.app.pipeline.vad import WebRTCEndpointDetector


PEER_CONNECTIONS: set[RTCPeerConnection] = set()
PEER_CLEANUPS: dict[RTCPeerConnection, Callable[[str], Awaitable[None]]] = {}


class RoomManager:
    """Manages multi-device rooms and cross-routes audio translation events."""

    def __init__(self):
        # room_id -> dict of client_id -> {"emit": emit_func, "session": session}
        self.rooms: dict[str, dict[str, dict]] = {}

    def register_client(
        self,
        room_id: str,
        client_id: str,
        session: TranslationSession,
        emit_func: Callable[[dict], Awaitable[None]],
    ) -> None:
        if self.has_client(room_id, client_id):
            raise ValueError(f"Username '{client_id}' is already in room '{room_id}'.")
        if room_id not in self.rooms:
            self.rooms[room_id] = {}
        self.rooms[room_id][client_id] = {
            "session": session,
            "emit": emit_func,
        }
        print(f"[RoomManager] Client '{client_id}' joined room '{room_id}'. Active clients in room: {list(self.rooms[room_id].keys())}")

    def has_client(self, room_id: str, client_id: str) -> bool:
        normalized = client_id.casefold()
        return any(existing.casefold() == normalized for existing in self.rooms.get(room_id, {}))

    def unregister_client(
        self,
        room_id: str,
        client_id: str,
        session: Optional[TranslationSession] = None,
    ) -> None:
        if room_id in self.rooms and client_id in self.rooms[room_id]:
            if session is not None and self.rooms[room_id][client_id]["session"] is not session:
                return
            del self.rooms[room_id][client_id]
            print(f"[RoomManager] Client '{client_id}' left room '{room_id}'. Remaining clients: {list(self.rooms[room_id].keys())}")
            if not self.rooms[room_id]:
                del self.rooms[room_id]

    async def route_event(self, room_id: str, sender_client_id: str, event: dict) -> None:
        """Cross-route translation event: send translation + TTS audio to peers, and self-caption to sender."""
        room_clients = self.rooms.get(room_id, {})
        other_clients = [c_id for c_id in room_clients if c_id != sender_client_id]

        event["sender_client_id"] = sender_client_id

        if not other_clients:
            print(f"[RoomManager] Client '{sender_client_id}' spoke in room '{room_id}', but no other devices are in the room yet.")

        sender_data = room_clients.get(sender_client_id)
        sender_session = sender_data["session"] if sender_data else None

        # 1. Send full translation + TTS audio payload to ALL OTHER peers in the room
        for peer_id in other_clients:
            peer_data = room_clients[peer_id]
            peer_session = peer_data["session"]
            peer_emit = peer_data["emit"]

            target_lang = peer_session.source_language  # The language this peer speaks & wants to hear

            # If the event translation language differs from the peer's language, translate dynamically for them
            if event.get("type") == "translation" and event.get("translation", {}).get("language") != target_lang and sender_session:
                committed_text = event["source"]["text"]
                translated_text = await sender_session.translator.translate(
                    committed_text,
                    source_language=sender_session.source_language,
                    target_language=target_lang,
                )
                voice = sender_session.voice_selector.select(target_lang, sender_session.voice_matching)
                tts_result = await sender_session.tts.synthesize(translated_text, voice.voice_id)

                import base64
                audio_base64 = base64.b64encode(tts_result.audio_bytes).decode("utf-8") if tts_result.audio_bytes else ""

                peer_event = {
                    "type": "translation",
                    "session_id": event.get("session_id"),
                    "sender_client_id": sender_client_id,
                    "source": event["source"],
                    "translation": {
                        "text": translated_text,
                        "language": target_lang,
                        "model": event["translation"]["model"],
                    },
                    "voice": {
                        "voice_id": voice.voice_id,
                        "presentation": voice.presentation,
                        "pitch_bucket": voice.pitch_bucket,
                    },
                    "audio": {
                        "data": audio_base64,
                        "content_type": tts_result.content_type,
                        "error": tts_result.error if hasattr(tts_result, "error") else "",
                    }
                }
                print(f"[RoomManager] Routed dynamically translated audio ({sender_session.source_language}->{target_lang}) from '{sender_client_id}' to peer '{peer_id}'")
                await peer_emit(peer_event)
            else:
                print(f"[RoomManager] Routing translated audio from '{sender_client_id}' to peer '{peer_id}' in room '{room_id}'")
                await peer_emit(event)

        # 2. Send self-caption feedback to the speaker (text only, NO TTS audio)
        if sender_data:
            self_caption_event = {
                "type": "self_caption",
                "session_id": event.get("session_id"),
                "sender_client_id": sender_client_id,
                "source": event.get("source"),
                "translation": event.get("translation"),
            }
            await sender_data["emit"](self_caption_event)


ROOM_MANAGER = RoomManager()


def finish_session(session: TranslationSession, client_id: str) -> None:
    try:
        metrics_path = session.save_metrics()
        if metrics_path:
            print(f"[Metrics] Saved session metrics for '{client_id}' to {metrics_path}")
    except OSError as exc:
        print(f"[Metrics] Could not save session metrics for '{client_id}': {exc}")


async def create_answer(request: OfferRequest) -> dict[str, str]:
    """Create a WebRTC answer for a browser offer.

    The starter receives the browser audio track and emits JSON events over a
    WebRTC data channel. Server-side TTS audio can be added later by adding
    a custom MediaStreamTrack back to the peer connection.
    """
    requested_client_id = (request.client_id or "").strip()
    client_id = requested_client_id or f"client-{str(uuid4())[:6]}"
    requested_room_id = request.room_id.strip()
    is_room_mode = request.session_mode == "room" and bool(requested_room_id)
    room_id = requested_room_id if is_room_mode else ""

    if is_room_mode and ROOM_MANAGER.has_client(room_id, client_id):
        raise HTTPException(
            status_code=409,
            detail=f"Username '{client_id}' is already in use in '{room_id}'. Choose another username.",
        )

    print(f"[WebRTC] Creating answer (mode={request.session_mode}, room='{room_id}', client='{client_id}'): asr={request.asr_model}, tts={request.tts_model}, translator={request.model}")

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
    audio_tasks: set[asyncio.Task] = set()
    timeout_tasks: set[asyncio.Task] = set()
    cleanup_lock = asyncio.Lock()
    cleaned_up = False

    async def emit(message: dict) -> None:
        if data_channel and data_channel.readyState == "open":
            data_channel.send(json.dumps(message, ensure_ascii=False))

    if is_room_mode:
        ROOM_MANAGER.register_client(room_id, client_id, session, emit)

    async def cleanup(reason: str) -> None:
        nonlocal cleaned_up
        async with cleanup_lock:
            if cleaned_up:
                return
            cleaned_up = True

        print(f"[WebRTC] Cleaning up client '{client_id}': {reason}")
        current_task = asyncio.current_task()
        for task in list(timeout_tasks):
            if task is not current_task:
                task.cancel()

        if peer_connection.connectionState != "closed":
            await peer_connection.close()

        pending_audio = [task for task in audio_tasks if task is not current_task]
        if pending_audio:
            await asyncio.gather(*pending_audio, return_exceptions=True)

        if is_room_mode:
            ROOM_MANAGER.unregister_client(room_id, client_id, session)
        finish_session(session, client_id)
        PEER_CONNECTIONS.discard(peer_connection)
        PEER_CLEANUPS.pop(peer_connection, None)

    PEER_CLEANUPS[peer_connection] = cleanup

    async def enforce_connection_timeout() -> None:
        await asyncio.sleep(config.connection_timeout_seconds)
        if peer_connection.connectionState != "connected":
            await cleanup("connection setup timed out")

    async def enforce_session_limit() -> None:
        await asyncio.sleep(config.max_session_seconds)
        await cleanup("maximum session duration reached")

    for coroutine in (enforce_connection_timeout(), enforce_session_limit()):
        task = asyncio.create_task(coroutine)
        timeout_tasks.add(task)
        task.add_done_callback(timeout_tasks.discard)

    @peer_connection.on("datachannel")
    def on_datachannel(channel: RTCDataChannel) -> None:
        nonlocal data_channel
        data_channel = channel
        print(f"[WebRTC] Data channel opened: {channel.label} (client='{client_id}')")

        @channel.on("message")
        def on_message(message: str) -> None:
            print(f"[WebRTC] Client '{client_id}' data channel message: {message}")

    @peer_connection.on("track")
    def on_track(track: MediaStreamTrack) -> None:
        print(f"[WebRTC] Received track: kind={track.kind} (client='{client_id}')")
        if track.kind == "audio":
            task = asyncio.create_task(
                consume_audio_track(
                    track=track,
                    session=session,
                    emit=emit,
                    is_room_mode=is_room_mode,
                    room_id=room_id,
                    client_id=client_id,
                )
            )
            audio_tasks.add(task)

            def on_audio_done(done_task: asyncio.Task) -> None:
                audio_tasks.discard(done_task)
                if not cleaned_up:
                    asyncio.create_task(cleanup("audio track ended"))

            task.add_done_callback(on_audio_done)

    @peer_connection.on("connectionstatechange")
    async def on_connectionstatechange() -> None:
        state = peer_connection.connectionState
        print(f"[WebRTC] Peer connection state changed to: {state} (client='{client_id}')")
        if state in {"failed", "closed"}:
            await cleanup(f"connection state changed to {state}")

    try:
        offer = RTCSessionDescription(sdp=request.sdp, type=request.type)
        await peer_connection.setRemoteDescription(offer)
        answer = await peer_connection.createAnswer()
        await peer_connection.setLocalDescription(answer)
    except Exception:
        await cleanup("signaling failed")
        raise

    print(f"[WebRTC] Signaling handshake complete for client '{client_id}'")
    return {
        "sdp": peer_connection.localDescription.sdp,
        "type": peer_connection.localDescription.type,
    }


async def consume_audio_track(
    track: MediaStreamTrack,
    session: TranslationSession,
    emit: Callable[[dict], Awaitable[None]],
    is_room_mode: bool = False,
    room_id: str = "",
    client_id: str = "",
) -> None:
    """Collect WebRTC audio frames, run VAD, and feed sentences to ASR."""
    print(f"[WebRTC] Starting consume_audio_track background worker loop for client '{client_id}'")

    frames = []
    detector = WebRTCEndpointDetector()
    # ponytail: cap queued utterances to bound memory; use external inference workers for lossless sustained load.
    utterances: asyncio.Queue[Optional[list]] = asyncio.Queue(maxsize=4)

    def enqueue(utterance_frames: list) -> None:
        if utterances.full():
            utterances.get_nowait()
            utterances.task_done()
            print(f"[WebRTC] Dropped oldest queued utterance for '{client_id}' to preserve real-time latency.")
        utterances.put_nowait(utterance_frames)

    async def process_utterances() -> None:
        while True:
            utterance_frames = await utterances.get()
            try:
                if utterance_frames is None:
                    return
                print(f"[WebRTC] Processing {len(utterance_frames)} audio frames for '{client_id}'...")
                event = await session.process_audio_window(utterance_frames)
                if event:
                    if is_room_mode and room_id:
                        await ROOM_MANAGER.route_event(room_id, client_id, event)
                    else:
                        await emit(event)
            except Exception as exc:
                print(f"[WebRTC] Utterance processing failed for '{client_id}': {exc}")
            finally:
                utterances.task_done()

    worker_task = asyncio.create_task(process_utterances())

    # We resample browser audio to 16kHz mono (standard format for VAD and ASR)
    resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
    track_error: Optional[Exception] = None

    try:
        while True:
            frame = await track.recv()
            resampled_frames = resampler.resample(frame)

            for r_frame in resampled_frames:
                pcm_bytes = r_frame.to_ndarray().tobytes()
                endpoint_triggered = detector.process_audio_chunk(pcm_bytes)

                if detector.in_speech:
                    frames.append(r_frame)

                if endpoint_triggered and frames:
                    enqueue(frames)
                    frames = []
    except Exception as exc:
        track_error = exc
        print(f"[WebRTC] Audio track stream ended for client '{client_id}': {exc}")
    finally:
        if frames:
            enqueue(frames)
        await utterances.join()
        utterances.put_nowait(None)
        await worker_task
        if track_error:
            await emit({"type": "track_closed", "detail": str(track_error)})


async def shutdown_peer_connections() -> None:
    coroutines = [cleanup("server shutdown") for cleanup in list(PEER_CLEANUPS.values())]
    if coroutines:
        await asyncio.gather(*coroutines)
    PEER_CONNECTIONS.clear()
    PEER_CLEANUPS.clear()
