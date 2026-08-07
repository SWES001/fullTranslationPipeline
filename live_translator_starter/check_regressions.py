import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import HTTPException

from server.app.pipeline.asr import ASRResult
from server.app.pipeline.session import TranslationSession
from server.app.pipeline.stable_buffer import StableTextBuffer
from server.app.schemas import OfferRequest
import server.app.webrtc_gateway as gateway


async def emit(_message: dict) -> None:
    return None


async def check_gateway_cleanup() -> None:
    gateway.finish_session = lambda *_args: None
    gateway.config.connection_timeout_seconds = 0.01
    await gateway.create_answer(
        OfferRequest(
            sdp="invalid",
            type="offer",
            session_mode="room",
            room_id="Channel 1",
            client_id="Alice",
            asr_model="fake",
            model="fake",
            tts_model="fake",
        )
    )
    await asyncio.sleep(0.05)
    assert not gateway.PEER_CONNECTIONS
    assert not gateway.ROOM_MANAGER.rooms


def check_duplicate_usernames() -> None:
    manager = gateway.RoomManager()
    session = TranslationSession("en", "ja", "fake", asr_model="fake", tts_model="fake")
    manager.register_client("room", "Alice", session, emit)
    try:
        manager.register_client("room", "alice", session, emit)
    except ValueError:
        pass
    else:
        raise AssertionError("Case-insensitive duplicate username was accepted")


async def check_duplicate_offer_rejected() -> None:
    session = TranslationSession("en", "ja", "fake", asr_model="fake", tts_model="fake")
    gateway.ROOM_MANAGER.register_client("room", "Alice", session, emit)
    try:
        await gateway.create_answer(
            OfferRequest(
                sdp="invalid",
                type="offer",
                session_mode="room",
                room_id="room",
                client_id="alice",
                asr_model="fake",
                model="fake",
                tts_model="fake",
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Duplicate username offer was accepted")
    finally:
        gateway.ROOM_MANAGER.unregister_client("room", "Alice", session)


async def check_audio_receive_is_decoupled() -> None:
    class Array:
        def tobytes(self) -> bytes:
            return b"audio"

    class Frame:
        def to_ndarray(self) -> Array:
            return Array()

    class Track:
        def __init__(self) -> None:
            self.received = 0

        async def recv(self) -> Frame:
            self.received += 1
            if self.received <= 3:
                return Frame()
            raise RuntimeError("track ended")

    class Resampler:
        def resample(self, frame: Frame) -> list[Frame]:
            return [frame]

    class Detector:
        in_speech = True

        def process_audio_chunk(self, _pcm: bytes) -> bool:
            return True

    class Session:
        def __init__(self, track: Track) -> None:
            self.track = track
            self.received_counts = []

        async def process_audio_window(self, _frames: list[Frame]) -> None:
            self.received_counts.append(self.track.received)
            await asyncio.sleep(0.01)
            return None

    track = Track()
    session = Session(track)
    original_resampler = gateway.av.AudioResampler
    original_detector = gateway.WebRTCEndpointDetector
    gateway.av.AudioResampler = lambda **_kwargs: Resampler()
    gateway.WebRTCEndpointDetector = Detector
    try:
        await gateway.consume_audio_track(track, session, emit, client_id="queue-check")
    finally:
        gateway.av.AudioResampler = original_resampler
        gateway.WebRTCEndpointDetector = original_detector

    assert session.received_counts == [4, 4, 4]


def check_bracket_filter() -> None:
    buffer = StableTextBuffer()
    assert buffer.commit(ASRResult("[ASR timeout]", True, 0.0, "en")) is None
    assert buffer.commit(ASRResult("[not closed", True, 0.0, "en")) == "[not closed"


def check_client_contract() -> None:
    root = Path(__file__).parent
    html = (root / "client/index.html").read_text(encoding="utf-8")
    javascript = (root / "client/src/main.js").read_text(encoding="utf-8")
    assert "cyberagent/CAT-Translate-3.3b" not in html
    assert "Qwen/Qwen3-8B" not in html
    assert "Qwen3-TTS-1.7B" not in html
    assert "fetch('/offer'" in javascript
    assert "74.2.96.26:30001" not in javascript


async def check_metrics_contract() -> None:
    session = TranslationSession("en", "ja", "fake", asr_model="fake", tts_model="fake")
    event = await session.process_audio_window([])
    assert event is not None
    assert "text_ready_ms" in event and "audio_ready_ms" in event
    assert "ttft_ms" not in event and "ttfa_ms" not in event

    with TemporaryDirectory() as directory:
        path = session.save_metrics(Path(directory))
        assert path is not None
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert set(payload["averages_ms"]) == {
            "asr",
            "trans",
            "text_ready",
            "tts",
            "audio_ready",
        }
        assert payload["utterance_count"] == 1


async def main() -> None:
    await check_gateway_cleanup()
    check_duplicate_usernames()
    await check_duplicate_offer_rejected()
    await check_audio_receive_is_decoupled()
    check_bracket_filter()
    check_client_contract()
    await check_metrics_contract()
    print("Regression checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
