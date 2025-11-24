"""
Simplified Remote Bangla Speech-to-Text using gradio_client library
This version is more reliable and handles Gradio API complexity automatically
"""

import asyncio
import logging
import io
import wave
import numpy as np
from typing import Optional
from gradio_client import Client
from livekit.agents import stt, utils
from livekit import rtc

logger = logging.getLogger(__name__)


class LocalBanglaSpeechSTT(stt.STT):
    """
    Speech-to-Text implementation using gradio_client library.
    Much simpler and more reliable than manual HTTP requests.
    """
    
    def __init__(
        self,
        api_url: str = "https://88a06ccbe8e9fdd60e.gradio.live",
        username: str = "deepthinkers",
        password: str = "bangla2025",
        language: str = "bn",
        timeout: int = 30,
        max_retries: int = 3,
        apply_correction: bool = True,
    ):
        """
        Initialize the Remote STT client
        
        Args:
            api_url: Base URL of your Gradio server from Colab
            username: Authentication username
            password: Authentication password
            language: Language code (default: "bn" for Bangla)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retry attempts
            apply_correction: Apply grammar correction to transcriptions (default: True)
        """
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=False,
                interim_results=False
            )
        )
        
        self._api_url = api_url
        self._username = username
        self._password = password
        self._language = language
        self._timeout = timeout
        self._max_retries = max_retries
        self._apply_correction = apply_correction
        self._client: Optional[Client] = None
        
        logger.info(f"Initialized RemoteBanglaSpeechSTT with API: {self._api_url}")
    
    def _ensure_client(self):
        """Ensure Gradio client exists"""
        if self._client is None:
            logger.debug("Creating Gradio client")
            self._client = Client(
                self._api_url,
                auth=(self._username, self._password)
            )
    
    def _combine_audio_frames(self, frames: list) -> rtc.AudioFrame:
        """Combine multiple audio frames into a single frame"""
        if not frames:
            raise ValueError("No audio frames to combine")
        
        if len(frames) == 1:
            return frames[0]
        
        first_frame = frames[0]
        sample_rate = first_frame.sample_rate
        num_channels = first_frame.num_channels
        
        combined_data = b''.join(frame.data for frame in frames)
        bytes_per_sample = 2 * num_channels
        total_samples = len(combined_data) // bytes_per_sample
        
        return rtc.AudioFrame(
            data=combined_data,
            sample_rate=sample_rate,
            num_channels=num_channels,
            samples_per_channel=total_samples
        )
    
    def _audio_frame_to_wav_file(self, frame: rtc.AudioFrame) -> str:
        """
        Convert AudioFrame to WAV file and return path
        
        Args:
            frame: AudioFrame from LiveKit
            
        Returns:
            str: Path to temporary WAV file
        """
        import tempfile
        
        # Convert frame data to numpy array
        audio_data = np.frombuffer(frame.data, dtype=np.int16)
        
        # Create temporary WAV file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
            
            with wave.open(temp_path, 'wb') as wav_file:
                wav_file.setnchannels(frame.num_channels)
                wav_file.setsampwidth(2)  # 16-bit audio
                wav_file.setframerate(frame.sample_rate)
                wav_file.writeframes(audio_data.tobytes())
        
        logger.debug(
            f"Created WAV file: {temp_path}, "
            f"{frame.sample_rate}Hz, {frame.num_channels} channel(s)"
        )
        
        return temp_path
    
    async def _send_audio_to_api(self, wav_path: str) -> str:
        """
        Send audio to the Gradio API using gradio_client
        
        Args:
            wav_path: Path to WAV file
            
        Returns:
            str: Transcribed text
        """
        from gradio_client import handle_file
        
        self._ensure_client()
        
        last_error = None
        
        for attempt in range(self._max_retries):
            try:
                logger.debug(f"Sending audio (attempt {attempt + 1}/{self._max_retries})")
                
                # Use handle_file to properly format the file for Gradio
                file_input = handle_file(wav_path)
                
                # Use gradio_client - it handles all the API complexity!
                result = await asyncio.to_thread(
                    self._client.predict,
                    file_input,
                    self._apply_correction,  # Pass grammar correction flag
                    api_name="/transcribe"
                )
                
                logger.info(f"Transcription received: '{result}'")
                return result if result else ""
                
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(1)
        
        error_msg = f"Failed after {self._max_retries} attempts"
        if last_error:
            error_msg += f": {str(last_error)}"
        raise Exception(error_msg)
    
    async def _recognize_impl(
        self,
        buffer: utils.AudioBuffer,
        *,
        language: Optional[str] = None,
        conn_options=None,
        **kwargs,
    ) -> stt.SpeechEvent:
        """Internal implementation of speech recognition"""
        import os
        
        temp_file = None
        
        try:
            # Handle audio buffer
            if isinstance(buffer, rtc.AudioFrame):
                frames = [buffer]
            elif hasattr(buffer, '__iter__'):
                try:
                    frames = list(buffer)
                except TypeError:
                    frames = [buffer]
            else:
                frames = [buffer]
            
            if not frames:
                logger.warning("Empty audio buffer")
                return self._empty_event(language)
            
            # Combine frames and convert to WAV
            combined_frame = self._combine_audio_frames(frames)
            temp_file = self._audio_frame_to_wav_file(combined_frame)
            
            # Send to API
            text = await self._send_audio_to_api(temp_file)
            
            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[
                    stt.SpeechData(
                        language=language or self._language,
                        text=text,
                        confidence=1.0
                    )
                ]
            )
        
        except Exception as e:
            logger.error(f"Error during recognition: {str(e)}")
            return self._empty_event(language)
        
        finally:
            # Clean up temp file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass
    
    def _empty_event(self, language: Optional[str]) -> stt.SpeechEvent:
        """Create an empty speech event"""
        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[
                stt.SpeechData(
                    language=language or self._language,
                    text=""
                )
            ]
        )
    
    async def stream(self) -> stt.SpeechStream:
        """Streaming not supported"""
        raise NotImplementedError(
            "Streaming is not supported. "
            "The Gradio API processes complete audio files."
        )
    
    async def aclose(self):
        """Clean up resources"""
        logger.debug("Closing RemoteBanglaSpeechSTT")
        await super().aclose()

