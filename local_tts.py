import logging
import asyncio
import io

import edge_tts
from livekit import rtc
from livekit.agents import tts
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions

logger = logging.getLogger(__name__)


class LocalEdgeTTS(tts.TTS):
    """
    Local Edge TTS implementation using edge-tts library for Bangla.
    
    Available Bangla voices:
    - bn-IN-BashkarNeural (Male voice, India)
    - bn-IN-TanishaaNeural (Female voice, India)
    - bn-BD-NabanitaNeural (Female voice, Bangladesh)
    - bn-BD-PradeepNeural (Male voice, Bangladesh)
    """
    
    def __init__(
        self,
        voice: str = "bn-IN-BashkarNeural",  # Default Bangla voice
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ):
        """
        Initialize Edge TTS with Bangla voice.
        
        Args:
            voice: Voice ID (see class docstring for available voices)
            rate: Speech rate adjustment (e.g., "+10%" for faster, "-10%" for slower)
            volume: Volume adjustment
            pitch: Pitch adjustment
        """
        super().__init__(
            capabilities=tts.TTSCapabilities(
                streaming=False,  # Edge TTS generates complete audio
            ),
            sample_rate=24000,  # Edge TTS uses 24kHz
            num_channels=1,
        )
        self._voice = voice
        self._rate = rate
        self._volume = volume
        self._pitch = pitch
        
        logger.info(f"Initialized Edge TTS with voice: {voice}")

    def _ensure_sample_rate(self, sample_rate: int) -> int:
        """Edge TTS uses 24kHz sample rate."""
        return 24000

    def synthesize(self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS) -> "ChunkedStream":
        """Synthesize text to speech."""
        return ChunkedStream(
            text=text,
            voice=self._voice,
            rate=self._rate,
            volume=self._volume,
            pitch=self._pitch,
            tts=self,
            conn_options=conn_options,
        )


class ChunkedStream(tts.ChunkedStream):
    """Stream for Edge TTS synthesis."""

    def __init__(
        self,
        text: str,
        voice: str,
        rate: str,
        volume: str,
        pitch: str,
        tts: LocalEdgeTTS,
        conn_options: APIConnectOptions,
    ):
        super().__init__(tts=tts, input_text=text, conn_options=conn_options)
        self._text = text
        self._voice = voice
        self._rate = rate
        self._volume = volume
        self._pitch = pitch

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        """Run the TTS synthesis."""
        try:
            logger.debug(f"Synthesizing text: {self._text[:50]}...")
            
            # Create Edge TTS communicate instance
            communicate = edge_tts.Communicate(
                text=self._text,
                voice=self._voice,
                rate=self._rate,
                volume=self._volume,
                pitch=self._pitch,
            )
            
            # Collect all audio chunks
            audio_data = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.write(chunk["data"])
            
            # Get the complete audio
            audio_bytes = audio_data.getvalue()
            
            if not audio_bytes:
                logger.warning("No audio data generated")
                return
            
            logger.debug(f"Generated audio: {len(audio_bytes)} bytes")
            
            # Initialize the output emitter
            from livekit.agents import utils
            output_emitter.initialize(
                request_id=utils.shortuuid(),
                sample_rate=24000,
                num_channels=1,
                mime_type="audio/mp3",  # Edge TTS outputs MP3 format
            )
            
            # Push the audio data
            output_emitter.push(audio_bytes)
            
        except Exception as e:
            logger.error(f"Error during TTS synthesis: {e}", exc_info=True)
            raise
