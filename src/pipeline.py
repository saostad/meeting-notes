"""Pipeline orchestration for the Meeting Video Chapter Tool.

This module provides the main pipeline that orchestrates all processing steps:
audio extraction, transcription, chapter identification, and chapter merging.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from src.audio_extractor import AudioExtractor
from src.transcription_service import TranscriptionService
from src.chapter_analyzer import ChapterAnalyzer
from src.chapter_merger import ChapterMerger
from src.chapter import Chapter
from src.transcript import Transcript
from src.config import Config
from src.errors import MeetingVideoChapterError


@dataclass
class PipelineResult:
    """Result of a pipeline execution.
    
    Attributes:
        success: Whether the pipeline completed successfully
        output_mkv: Path to the final MKV file with chapters (if successful)
        audio_file: Path to the extracted audio file (if generated)
        transcript_file: Path to the transcript file (if generated)
        subtitle_file: Path to the SRT subtitle file (if generated)
        chapters_file: Path to the chapters JSON file (if generated)
        notes_file: Path to the notes file with actionable instructions (if generated)
        chapters: List of identified chapters (if generated)
        error: Error message if pipeline failed
        warnings: List of warning messages from processing
        step_failed: Name of the step that failed (if any)
    """
    success: bool
    output_mkv: Optional[str] = None
    audio_file: Optional[str] = None
    transcript_file: Optional[str] = None
    subtitle_file: Optional[str] = None
    chapters_file: Optional[str] = None
    notes_file: Optional[str] = None
    chapters: Optional[List[Chapter]] = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    step_failed: Optional[str] = None


def run_pipeline(mkv_path: str, config: Config) -> PipelineResult:
    """Execute the complete video chapter processing pipeline.
    
    This function orchestrates all processing steps in sequence:
    1. Audio extraction from MKV
    2. Transcription using Whisper
    3. Chapter identification using Gemini
    4. Chapter merging back into MKV
    
    The pipeline halts on the first error and reports which step failed.
    If skip_existing is enabled, existing intermediate files are reused.
    
    Args:
        mkv_path: Path to the input MKV file
        config: Configuration object with API keys and settings
        
    Returns:
        PipelineResult: Result object with success status, file paths, and any errors
    """
    result = PipelineResult(success=False)
    warnings = []
    
    try:
        mkv_file = Path(mkv_path)
        
        # Determine output directory
        if config.output_dir:
            output_dir = Path(config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = mkv_file.parent
        
        # Define intermediate file paths
        audio_path = output_dir / f"{mkv_file.stem}.mp3"
        transcript_path = output_dir / f"{mkv_file.stem}_transcript.json"
        chapters_raw_path = output_dir / f"{mkv_file.stem}_chapters_raw.txt"
        notes_path = output_dir / f"{mkv_file.stem}_notes.json"
        subtitle_path = output_dir / f"{mkv_file.stem}_chaptered.srt"
        output_mkv_path = output_dir / f"{mkv_file.stem}_chaptered.mkv"
        
        # Step 1: Audio Extraction
        result.step_failed = "audio extraction"
        if config.skip_existing and audio_path.exists():
            # Reuse existing audio file
            result.audio_file = str(audio_path)
            warnings.append(f"Reusing existing audio file: {audio_path}")
        else:
            extractor = AudioExtractor()
            result.audio_file = extractor.extract(str(mkv_path), str(audio_path))
        
        # Step 2: Transcription
        result.step_failed = "transcription"
        if config.skip_existing and transcript_path.exists():
            # Reuse existing transcript
            transcript = Transcript.from_file(str(transcript_path))
            result.transcript_file = str(transcript_path)
            warnings.append(f"Reusing existing transcript file: {transcript_path}")
        else:
            transcription_service = TranscriptionService(model_name=config.whisper_model)
            transcript = transcription_service.transcribe(result.audio_file, str(transcript_path))
            result.transcript_file = str(transcript_path)
        
        # Step 3: Chapter Identification
        result.step_failed = "chapter identification"
        if config.skip_existing and chapters_raw_path.exists():
            # Reuse existing chapters file
            analyzer = ChapterAnalyzer(
                api_key=config.gemini_api_key,
                model_name=config.gemini_model
            )
            with open(chapters_raw_path, 'r', encoding='utf-8') as f:
                raw_response = f.read()
            chapters, _ = analyzer.parse_response(raw_response)
            result.chapters = chapters
            result.chapters_file = str(chapters_raw_path)
            if notes_path.exists():
                result.notes_file = str(notes_path)
            warnings.append(f"Reusing existing chapters file: {chapters_raw_path}")
        else:
            analyzer = ChapterAnalyzer(
                api_key=config.gemini_api_key,
                model_name=config.gemini_model
            )
            chapters = analyzer.analyze(
                transcript, 
                save_raw_response=str(chapters_raw_path),
                save_notes=str(notes_path)
            )
            result.chapters = chapters
            result.chapters_file = str(chapters_raw_path)
            if notes_path.exists():
                result.notes_file = str(notes_path)
        
        # Step 4: Chapter Merging
        result.step_failed = "chapter merging"
        merger = ChapterMerger()
        result.output_mkv = merger.merge(
            str(mkv_path), 
            chapters, 
            str(output_mkv_path),
            overlay_titles=config.overlay_chapter_titles
        )
        
        # Step 5: Generate Subtitle File
        # Generate SRT subtitle file from transcript for VLC and other players
        result.step_failed = "subtitle generation"
        if config.skip_existing and subtitle_path.exists():
            # Reuse existing subtitle file
            result.subtitle_file = str(subtitle_path)
            warnings.append(f"Reusing existing subtitle file: {subtitle_path}")
        else:
            transcript.to_srt(str(subtitle_path))
            result.subtitle_file = str(subtitle_path)
        
        # Pipeline completed successfully
        result.success = True
        result.step_failed = None
        result.warnings = warnings
        
        return result
    
    except MeetingVideoChapterError as e:
        # Capture error from our custom exceptions
        result.error = str(e)
        result.warnings = warnings
        return result
    
    except Exception as e:
        # Capture unexpected errors
        result.error = f"Unexpected error during {result.step_failed}: {str(e)}"
        result.warnings = warnings
        return result
