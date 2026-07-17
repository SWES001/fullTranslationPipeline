import base64
import httpx
import asyncio

async def test():
    with open("reference.wav", "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")
        
    # Standard base64 format without data URI prefix
    payload = {
        "model": "/models/Qwen3-TTS-12Hz-1.7B-Base",
        "input": "Miami.",
        "task_type": "Base",
        "ref_audio": "data:audio/wav;base64," + audio_b64,
        "x_vector_only_mode": True,
        "response_format": "wav"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            print("Pinging Qwen3 TTS with ref_audio...")
            r = await client.post("http://74.2.96.26:31411/v1/audio/speech", json=payload, timeout=120.0)
            print(f"Status: {r.status_code}")
            if r.status_code == 200:
                print(f"Success! {len(r.content)} bytes generated.")
            else:
                print("Error Response:")
                print(r.text)
        except Exception as e:
            print("Error:", repr(e))

asyncio.run(test())
