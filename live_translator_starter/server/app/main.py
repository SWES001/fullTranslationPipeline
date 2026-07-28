from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.app.config import config
from server.app.schemas import OfferRequest, OfferResponse
from server.app.webrtc_gateway import create_answer, shutdown_peer_connections


app = FastAPI(title=config.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/offer", response_model=OfferResponse)
async def offer(request: OfferRequest) -> OfferResponse:
    """Accept a browser WebRTC offer and return the server SDP answer."""

    answer = await create_answer(request)
    return OfferResponse(**answer)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await shutdown_peer_connections()


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "online", "message": "Live Translator API Backend"}
