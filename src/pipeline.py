"""Pipeline orchestration for the Meeting Video Chapter Tool.

This module provides the main pipeline that orchestrates all processing steps:
audio extraction, transcription, chapter identification, and chapter merging.
"""

import os
import time
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
        step_timings: Dictionary of step names to execution times in seconds
        total_time: Total pipeline execution time in seconds
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
    step_timings: dict = field(default_factory=dict)
    total_time: float = 0.0


def run_pipeline(mkv_path: str, config: Config, progress_callback=None) -> PipelineResult:
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
        progress_callback: Optional callback function to report progress (step_num, step_name, status)
        
    Returns:
        PipelineResult: Result object with success status, file paths, and any errors
    """
    # Start total timing
    pipeline_start_time = time.time()
    
    result = PipelineResult(success=False)
    warnings = []
    step_timings = {}
    
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
        step_start_time = time.time()
        if progress_callback:
            progress_callback(1, "Extracting audio", "start")
        result.step_failed = "audio extraction"
        if config.skip_existing and audio_path.exists():
            # Reuse existing audio file
            result.audio_file = str(audio_path)
            warnings.append(f"Reusing existing audio file: {audio_path}")
        else:
            extractor = AudioExtractor()
            result.audio_file = extractor.extract(str(mkv_path), str(audio_path))
        step_timings["audio_extraction"] = time.time() - step_start_time
        if progress_callback:
            progress_callback(1, "Extracting audio", "complete")
        print(f"⏱️  Step 1 completed in {step_timings['audio_extraction']:.2f}s")
        
        # Step 2: Transcription
        step_start_time = time.time()
        if progress_callback:
            progress_callback(2, "Transcribing audio (this may take a while)", "start")
        result.step_failed = "transcription"
        if config.skip_existing and transcript_path.exists():
            # Reuse existing transcript (Requirement 7.3)
            transcript = Transcript.from_file(str(transcript_path))
            result.transcript_file = str(transcript_path)
            warnings.append(f"Reusing existing transcript file: {transcript_path}")
        else:
            # Initialize transcription service with model caching support (Requirement 7.5)
            transcription_service = TranscriptionService(model_name=config.whisper_model)
            transcript = transcription_service.transcribe(result.audio_file, str(transcript_path))
            result.transcript_file = str(transcript_path)
        step_timings["transcription"] = time.time() - step_start_time
        if progress_callback:
            progress_callback(2, "Transcribing audio (this may take a while)", "complete")
        print(f"⏱️  Step 2 completed in {step_timings['transcription']:.2f}s")
        
        # Step 3: Chapter Identification
        step_start_time = time.time()
        if progress_callback:
            progress_callback(3, "Identifying chapters", "start")
        result.step_failed = "chapter identification"
        if config.skip_existing and chapters_raw_path.exists():
            # Reuse existing chapters file (Requirement 7.3)
            # For backward compatibility, we need to parse the existing response
            # Since we can't easily recreate the provider that generated it,
            # we'll create a new analyzer and let it handle the analysis
            analyzer = ChapterAnalyzer(config)
            chapters = analyzer.analyze(
                transcript, 
                save_raw_response=str(chapters_raw_path),
                save_notes=str(notes_path)
            )
            result.chapters = chapters
            result.chapters_file = str(chapters_raw_path)
            if notes_path.exists():
                result.notes_file = str(notes_path)
            warnings.append(f"Reusing existing transcript but re-analyzing with current AI provider configuration")
        else:
            analyzer = ChapterAnalyzer(config)
            chapters = analyzer.analyze(
                transcript, 
                save_raw_response=str(chapters_raw_path),
                save_notes=str(notes_path)
            )
            result.chapters = chapters
            result.chapters_file = str(chapters_raw_path)
            if notes_path.exists():
                result.notes_file = str(notes_path)
        step_timings["chapter_identification"] = time.time() - step_start_time
        if progress_callback:
            progress_callback(3, "Identifying chapters", "complete")
        print(f"⏱️  Step 3 completed in {step_timings['chapter_identification']:.2f}s")
        
        # Step 4: Chapter Merging
        step_start_time = time.time()
        if progress_callback:
            progress_callback(4, "Merging chapters into video", "start")
        result.step_failed = "chapter merging"
        merger = ChapterMerger()
        result.output_mkv = merger.merge(
            str(mkv_path), 
            chapters, 
            str(output_mkv_path),
            overlay_titles=config.overlay_chapter_titles
        )
        step_timings["chapter_merging"] = time.time() - step_start_time
        if progress_callback:
            progress_callback(4, "Merging chapters into video", "complete")
        print(f"⏱️  Step 4 completed in {step_timings['chapter_merging']:.2f}s")
        
        # Step 5: Generate Subtitle File
        # Generate SRT subtitle file from transcript for VLC and other players
        step_start_time = time.time()
        if progress_callback:
            progress_callback(5, "Generating subtitles", "start")
        result.step_failed = "subtitle generation"
        if config.skip_existing and subtitle_path.exists():
            # Reuse existing subtitle file (Requirement 7.3)
            result.subtitle_file = str(subtitle_path)
            warnings.append(f"Reusing existing subtitle file: {subtitle_path}")
        else:
            transcript.to_srt(str(subtitle_path))
            result.subtitle_file = str(subtitle_path)
        step_timings["subtitle_generation"] = time.time() - step_start_time
        if progress_callback:
            progress_callback(5, "Generating subtitles", "complete")
        print(f"⏱️  Step 5 completed in {step_timings['subtitle_generation']:.2f}s")
        
        # Pipeline completed successfully
        total_time = time.time() - pipeline_start_time
        
        # Print timing summary
        print("\n" + "="*50)
        print("⏱️  PIPELINE TIMING SUMMARY")
        print("="*50)
        for step_name, step_time in step_timings.items():
            step_display = step_name.replace("_", " ").title()
            print(f"{step_display:.<30} {step_time:>8.2f}s")
        print("-"*50)
        print(f"{'Total Processing Time':.<30} {total_time:>8.2f}s")
        print("="*50)
        
        result.success = True
        result.step_failed = None
        result.warnings = warnings
        result.step_timings = step_timings
        result.total_time = total_time
        
        return result
    
    except MeetingVideoChapterError as e:
        # Capture error from our custom exceptions
        total_time = time.time() - pipeline_start_time
        result.error = str(e)
        result.warnings = warnings
        result.step_timings = step_timings
        result.total_time = total_time
        
        # Print partial timing summary on failure
        if step_timings:
            print(f"\n⏱️  Pipeline failed after {total_time:.2f}s")
            print("Completed steps:")
            for step_name, step_time in step_timings.items():
                step_display = step_name.replace("_", " ").title()
                print(f"  {step_display}: {step_time:.2f}s")
        
        return result
    
    except Exception as e:
        # Capture unexpected errors
        total_time = time.time() - pipeline_start_time
        result.error = f"Unexpected error during {result.step_failed}: {str(e)}"
        result.warnings = warnings
        result.step_timings = step_timings
        result.total_time = total_time
        
        # Print partial timing summary on failure
        if step_timings:
            print(f"\n⏱️  Pipeline failed after {total_time:.2f}s")
            print("Completed steps:")
            for step_name, step_time in step_timings.items():
                step_display = step_name.replace("_", " ").title()
                print(f"  {step_display}: {step_time:.2f}s")
        
        return result
