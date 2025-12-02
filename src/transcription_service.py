"""Transcription service for the Meeting Video Chapter Tool.

This module provides functionality to transcribe audio files using the Whisper
speech recognition model, generating timestamped transcripts.
"""

import os
from pathlib import Path
from typing import Optional
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

from src.transcript import Transcript, TranscriptSegment
from src.errors import FileSystemError, DependencyError, ProcessingError


class TranscriptionService:
    """Service for transcribing audio files using Whisper model.
    
    This class handles loading the Whisper model, processing audio files,
    and generating timestamped transcripts with proper error handling.
    """
    
    def __init__(self, model_name: str = "openai/whisper-large-v3-turbo"):
        """Initialize the transcription service.
        
        Args:
            model_name: Name of the Whisper model to use from HuggingFace
        """
        self.model_name = model_name
        self.model = None
        self.processor = None
        self.pipe = None
        self._device = None
        self._torch_dtype = None
    
    def load_model(self) -> None:
        """Load and initialize the Whisper model.
        
        This method loads the model weights and sets up the transcription pipeline.
        The model is downloaded on first use and cached for subsequent runs.
        
        Raises:
            DependencyError: If model loading fails
        """
        try:
            # Determine device and dtype
            self._device = "cuda:0" if torch.cuda.is_available() else "cpu"
            self._torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            
            # Load model
            self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                self.model_name,
                torch_dtype=self._torch_dtype,
                low_cpu_mem_usage=True,
                use_safetensors=True
            )
            self.model.to(self._device)
            
            # Load processor
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            
            # Create pipeline
            self.pipe = pipeline(
                "automatic-speech-recognition",
                model=self.model,
                tokenizer=self.processor.tokenizer,
                feature_extractor=self.processor.feature_extractor,
                torch_dtype=self._torch_dtype,
                device=self._device,
                return_timestamps=True
            )
            
        except Exception as e:
            raise DependencyError(
                "Failed to load Whisper model",
                context={
                    "dependency": "transformers/Whisper",
                    "operation": "model loading",
                    "model_name": self.model_name,
                    "cause": str(e)
                }
            )
    
    def transcribe(self, audio_path: str, output_path: Optional[str] = None) -> Transcript:
        """Transcribe an audio file and generate a timestamped transcript.
        
        Args:
            audio_path: Path to the audio file (MP3 or other supported format)
            output_path: Optional path to save the transcript JSON file.
                        If not provided, saves to same directory as audio with .json extension
        
        Returns:
            Transcript: The generated transcript with segments and timing
            
        Raises:
            FileSystemError: If audio file doesn't exist or is not accessible
            ProcessingError: If transcription fails
            DependencyError: If model is not loaded or fails during transcription
        """
        # Validate audio file exists
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileSystemError(
                "Audio file does not exist",
                context={
                    "file_path": str(audio_path),
                    "operation": "transcription"
                }
            )
        
        if not audio_file.is_file():
            raise FileSystemError(
                "Path is not a file",
                context={
                    "file_path": str(audio_path),
                    "operation": "transcription"
                }
            )
        
        # Check if file is empty
        if audio_file.stat().st_size == 0:
            raise ProcessingError(
                "Audio file is empty",
                context={
                    "file_path": str(audio_path),
                    "operation": "transcription"
                }
            )
        
        # Load model if not already loaded
        if self.pipe is None:
            self.load_model()
        
        try:
            # Run transcription
            result = self.pipe(
                str(audio_path),
                generate_kwargs={"language": "english"},
                return_timestamps=True
            )
            
            # Handle empty transcription result
            if not result or "text" not in result:
                raise ProcessingError(
                    "Transcription produced no output",
                    context={
                        "file_path": str(audio_path),
                        "operation": "transcription",
                        "cause": "Model returned empty result"
                    }
                )
            
            # Extract full text
            full_text = result["text"].strip()
            
            # Handle case where no speech was detected
            if not full_text:
                raise ProcessingError(
                    "No speech detected in audio file",
                    context={
                        "file_path": str(audio_path),
                        "operation": "transcription",
                        "cause": "Audio file contains no speech or is silent"
                    }
                )
            
            # Extract segments with timestamps
            segments = []
            duration = 0.0
            
            if "chunks" in result and result["chunks"]:
                for chunk in result["chunks"]:
                    timestamp = chunk.get("timestamp", (0.0, 0.0))
                    text = chunk.get("text", "").strip()
                    
                    # Handle timestamp format
                    if isinstance(timestamp, tuple) and len(timestamp) == 2:
                        start_time = float(timestamp[0]) if timestamp[0] is not None else 0.0
                        end_time = float(timestamp[1]) if timestamp[1] is not None else start_time
                    else:
                        # Fallback if timestamp format is unexpected
                        start_time = 0.0
                        end_time = 0.0
                    
                    if text:  # Only add non-empty segments
                        segments.append(TranscriptSegment(
                            start_time=start_time,
                            end_time=end_time,
                            text=text
                        ))
                        
                        # Update duration
                        if end_time > duration:
                            duration = end_time
            else:
                # If no chunks, create a single segment with the full text
                # Estimate duration from file (this is a fallback)
                segments.append(TranscriptSegment(
                    start_time=0.0,
                    end_time=0.0,  # Unknown duration
                    text=full_text
                ))
            
            # Create transcript object
            transcript = Transcript(
                segments=segments,
                full_text=full_text,
                duration=duration
            )
            
            # Save to file if output path is provided or default
            if output_path is None:
                output_path = str(audio_file.parent / f"{audio_file.stem}_transcript.json")
            
            transcript.to_file(output_path)
            
            return transcript
            
        except (FileSystemError, ProcessingError, DependencyError):
            # Re-raise our custom exceptions
            raise
            
        except Exception as e:
            raise ProcessingError(
                "Transcription failed",
                context={
                    "file_path": str(audio_path),
                    "dependency": "Whisper",
                    "operation": "transcription",
                    "cause": str(e)
                }
            )
