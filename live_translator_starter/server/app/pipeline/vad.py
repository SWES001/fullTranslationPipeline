import webrtcvad

class WebRTCEndpointDetector:
    def __init__(self, sample_rate: int = 16000, aggressiveness: int = 3, silence_limit_ms: int = 600):
        # Aggressiveness: 0 (least filtering) to 3 (most aggressive filtering of noise)
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate
        
        # webrtcvad strictly requires 10, 20, or 30ms chunks. We use 30ms.
        self.frame_duration_ms = 30
        
        # At 16000Hz mono 16-bit PCM, 30ms of audio is:
        # 16000 * 0.030 * 2 bytes = 960 bytes
        self.bytes_per_frame = int(self.sample_rate * (self.frame_duration_ms / 1000.0) * 2)
        
        self.buffer = b""
        self.in_speech = False
        self.silence_accumulator_ms = 0
        self.silence_limit_ms = silence_limit_ms

    def process_audio_chunk(self, pcm_bytes: bytes) -> bool:
        """Accumulates PCM bytes. Returns True if a sentence has ended (endpointed)."""
        self.buffer += pcm_bytes
        endpoint_triggered = False
        
        # Process buffer in chunks of exactly 30ms
        while len(self.buffer) >= self.bytes_per_frame:
            chunk = self.buffer[:self.bytes_per_frame]
            self.buffer = self.buffer[self.bytes_per_frame:]
            
            # Check if this 30ms chunk contains speech
            is_speech = self.vad.is_speech(chunk, self.sample_rate)
            
            if is_speech:
                self.in_speech = True
                self.silence_accumulator_ms = 0
            else:
                if self.in_speech:
                    self.silence_accumulator_ms += self.frame_duration_ms
                    if self.silence_accumulator_ms >= self.silence_limit_ms:
                        # User has paused long enough! 
                        # Sentence is finished. Trigger endpoint.
                        self.in_speech = False
                        self.silence_accumulator_ms = 0
                        endpoint_triggered = True
                        
        return endpoint_triggered