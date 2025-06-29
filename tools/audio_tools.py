"""
Audio processing tools for Agent Zero Gemini
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import tempfile

from core.tools import BaseTool

logger = logging.getLogger(__name__)

class TextToSpeechTool(BaseTool):
    """Text-to-speech tool"""
    
    def __init__(self):
        super().__init__(
            name="text_to_speech",
            description="Convert text to speech audio"
        )
        self._setup_tts()
    
    def _setup_tts(self):
        """Setup TTS engine"""
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            
            # Configure voice settings
            voices = self.tts_engine.getProperty('voices')
            if voices:
                self.tts_engine.setProperty('voice', voices[0].id)
            
            self.tts_engine.setProperty('rate', 150)  # Speed
            self.tts_engine.setProperty('volume', 0.9)  # Volume
            
        except ImportError:
            logger.warning("pyttsx3 not installed. TTS will not be available.")
            self.tts_engine = None
        except Exception as e:
            logger.error(f"Error initializing TTS engine: {e}")
            self.tts_engine = None
    
    async def execute(self, text: str, output_file: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Convert text to speech"""
        if not self.tts_engine:
            return {
                "success": False,
                "error": "TTS engine not available. Install with: pip install pyttsx3"
            }
        
        try:
            # Configure voice settings if provided
            rate = kwargs.get("rate", 150)
            volume = kwargs.get("volume", 0.9)
            voice_index = kwargs.get("voice_index", 0)
            
            self.tts_engine.setProperty('rate', rate)
            self.tts_engine.setProperty('volume', volume)
            
            # Set voice if specified
            voices = self.tts_engine.getProperty('voices')
            if voices and 0 <= voice_index < len(voices):
                self.tts_engine.setProperty('voice', voices[voice_index].id)
            
            if output_file:
                # Save to file
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                self.tts_engine.save_to_file(text, str(output_path))
                await asyncio.to_thread(self.tts_engine.runAndWait)
                
                return {
                    "success": True,
                    "output_file": str(output_path),
                    "message": f"Speech saved to {output_path}"
                }
            else:
                # Play directly
                await asyncio.to_thread(self.tts_engine.say, text)
                await asyncio.to_thread(self.tts_engine.runAndWait)
                
                return {
                    "success": True,
                    "message": "Speech played successfully"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "text": {
                "type": "string",
                "description": "Text to convert to speech"
            },
            "output_file": {
                "type": "string",
                "description": "Output audio file path (optional)",
                "optional": True
            },
            "rate": {
                "type": "integer",
                "description": "Speech rate (words per minute)",
                "default": 150,
                "optional": True
            },
            "volume": {
                "type": "number",
                "description": "Volume level (0.0 to 1.0)",
                "default": 0.9,
                "optional": True
            },
            "voice_index": {
                "type": "integer",
                "description": "Voice index to use",
                "default": 0,
                "optional": True
            }
        }

class SpeechToTextTool(BaseTool):
    """Speech-to-text tool"""
    
    def __init__(self):
        super().__init__(
            name="speech_to_text",
            description="Convert speech audio to text"
        )
        self._setup_stt()
    
    def _setup_stt(self):
        """Setup STT recognizer"""
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            
            # Adjust for ambient noise
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
                
        except ImportError:
            logger.warning("speech_recognition not installed. STT will not be available.")
            self.recognizer = None
        except Exception as e:
            logger.error(f"Error initializing STT: {e}")
            self.recognizer = None
    
    async def execute(self, source: str = "microphone", **kwargs) -> Dict[str, Any]:
        """Convert speech to text"""
        if not self.recognizer:
            return {
                "success": False,
                "error": "Speech recognition not available. Install with: pip install SpeechRecognition pyaudio"
            }
        
        try:
            if source == "microphone":
                return await self._recognize_from_microphone(**kwargs)
            elif source == "file":
                return await self._recognize_from_file(kwargs.get("audio_file"), **kwargs)
            else:
                return {
                    "success": False,
                    "error": f"Unknown source: {source}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _recognize_from_microphone(self, **kwargs) -> Dict[str, Any]:
        """Recognize speech from microphone"""
        timeout = kwargs.get("timeout", 5)
        phrase_timeout = kwargs.get("phrase_timeout", 1)
        language = kwargs.get("language", "en-US")
        
        try:
            with self.microphone as source:
                logger.info("Listening for speech...")
                audio = await asyncio.to_thread(
                    self.recognizer.listen,
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_timeout
                )
            
            # Recognize speech
            text = await asyncio.to_thread(
                self.recognizer.recognize_google,
                audio,
                language=language
            )
            
            return {
                "success": True,
                "text": text,
                "source": "microphone"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Speech recognition failed: {str(e)}"
            }
    
    async def _recognize_from_file(self, audio_file: str, **kwargs) -> Dict[str, Any]:
        """Recognize speech from audio file"""
        if not audio_file:
            return {
                "success": False,
                "error": "Audio file path required"
            }
        
        audio_path = Path(audio_file)
        if not audio_path.exists():
            return {
                "success": False,
                "error": f"Audio file not found: {audio_file}"
            }
        
        language = kwargs.get("language", "en-US")
        
        try:
            import speech_recognition as sr
            
            with sr.AudioFile(str(audio_path)) as source:
                audio = await asyncio.to_thread(self.recognizer.record, source)
            
            # Recognize speech
            text = await asyncio.to_thread(
                self.recognizer.recognize_google,
                audio,
                language=language
            )
            
            return {
                "success": True,
                "text": text,
                "source": "file",
                "file": str(audio_path)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Speech recognition failed: {str(e)}"
            }
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "source": {
                "type": "string",
                "description": "Audio source (microphone or file)",
                "enum": ["microphone", "file"],
                "default": "microphone"
            },
            "audio_file": {
                "type": "string",
                "description": "Path to audio file (required if source is file)",
                "optional": True
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout for listening (seconds)",
                "default": 5,
                "optional": True
            },
            "phrase_timeout": {
                "type": "integer",
                "description": "Timeout for phrase completion (seconds)",
                "default": 1,
                "optional": True
            },
            "language": {
                "type": "string",
                "description": "Language code for recognition",
                "default": "en-US",
                "optional": True
            }
        }

class AudioProcessingTool(BaseTool):
    """Audio file processing tool"""
    
    def __init__(self):
        super().__init__(
            name="audio_processing",
            description="Process audio files - convert formats, adjust volume, trim, etc."
        )
    
    async def execute(self, action: str, input_file: str, **kwargs) -> Dict[str, Any]:
        """Process audio file"""
        try:
            from pydub import AudioSegment
            
            input_path = Path(input_file)
            if not input_path.exists():
                return {
                    "success": False,
                    "error": f"Input file not found: {input_file}"
                }
            
            # Load audio
            audio = AudioSegment.from_file(str(input_path))
            
            if action == "convert":
                return await self._convert_audio(audio, input_path, **kwargs)
            elif action == "trim":
                return await self._trim_audio(audio, input_path, **kwargs)
            elif action == "adjust_volume":
                return await self._adjust_volume(audio, input_path, **kwargs)
            elif action == "get_info":
                return await self._get_audio_info(audio, input_path)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
                
        except ImportError:
            return {
                "success": False,
                "error": "pydub not installed. Install with: pip install pydub"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _convert_audio(self, audio, input_path: Path, **kwargs) -> Dict[str, Any]:
        """Convert audio format"""
        output_format = kwargs.get("format", "mp3")
        output_file = kwargs.get("output_file")
        
        if not output_file:
            output_file = input_path.with_suffix(f".{output_format}")
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        await asyncio.to_thread(audio.export, str(output_path), format=output_format)
        
        return {
            "success": True,
            "output_file": str(output_path),
            "format": output_format
        }
    
    async def _trim_audio(self, audio, input_path: Path, **kwargs) -> Dict[str, Any]:
        """Trim audio"""
        start_time = kwargs.get("start_time", 0) * 1000  # Convert to milliseconds
        end_time = kwargs.get("end_time")
        
        if end_time:
            end_time = end_time * 1000
            trimmed_audio = audio[start_time:end_time]
        else:
            trimmed_audio = audio[start_time:]
        
        output_file = kwargs.get("output_file", input_path.with_suffix("_trimmed" + input_path.suffix))
        output_path = Path(output_file)
        
        await asyncio.to_thread(trimmed_audio.export, str(output_path), format=input_path.suffix[1:])
        
        return {
            "success": True,
            "output_file": str(output_path),
            "duration": len(trimmed_audio) / 1000
        }
    
    async def _adjust_volume(self, audio, input_path: Path, **kwargs) -> Dict[str, Any]:
        """Adjust audio volume"""
        volume_change = kwargs.get("volume_change", 0)  # dB change
        
        adjusted_audio = audio + volume_change
        
        output_file = kwargs.get("output_file", input_path.with_suffix("_adjusted" + input_path.suffix))
        output_path = Path(output_file)
        
        await asyncio.to_thread(adjusted_audio.export, str(output_path), format=input_path.suffix[1:])
        
        return {
            "success": True,
            "output_file": str(output_path),
            "volume_change": volume_change
        }
    
    async def _get_audio_info(self, audio, input_path: Path) -> Dict[str, Any]:
        """Get audio file information"""
        return {
            "success": True,
            "file": str(input_path),
            "duration": len(audio) / 1000,  # seconds
            "channels": audio.channels,
            "sample_rate": audio.frame_rate,
            "frame_width": audio.frame_width,
            "max_possible_amplitude": audio.max_possible_amplitude
        }
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "action": {
                "type": "string",
                "description": "Audio processing action",
                "enum": ["convert", "trim", "adjust_volume", "get_info"]
            },
            "input_file": {
                "type": "string",
                "description": "Input audio file path"
            },
            "output_file": {
                "type": "string",
                "description": "Output file path (optional)",
                "optional": True
            },
            "format": {
                "type": "string",
                "description": "Output format for conversion",
                "optional": True
            },
            "start_time": {
                "type": "number",
                "description": "Start time for trimming (seconds)",
                "optional": True
            },
            "end_time": {
                "type": "number",
                "description": "End time for trimming (seconds)",
                "optional": True
            },
            "volume_change": {
                "type": "number",
                "description": "Volume change in dB",
                "optional": True
            }
        }
