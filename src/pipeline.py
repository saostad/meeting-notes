"""Pipeline orchestration for the Meeting Video Chapter Tool.

This module provides the main pipeline that orchestrates all processing steps:
audio extraction, transcription, chapter identification, and chapter merging.
"""

import os
import time
import json
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
from src.file_detector import SimpleFileDetector as FileTypeDetector


def _load_existing_chapters(chapters_raw_path: str) -> List[Chapter]:
    """Load chapters from an existing chapters_raw.txt file.
    
    Args:
        chapters_raw_path: Path to the existing chapters_raw.txt file
        
    Returns:
        List of Chapter objects parsed from the file
        
    Raises:
        MeetingVideoChapterError: If the file cannot be parsed or contains invalid data
    """
    try:
        with open(chapters_raw_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both old and new formats
        if isinstance(data, dict) and 'chapters' in data:
            # New format with chapters and notes
            chapters_data = data['chapters']
        elif isinstance(data, list):
            # Old format - direct list of chapters
            chapters_data = data
        else:
            raise ValueError("Invalid chapters file format")
        
        # Parse chapters
        chapters = []
        for chapter_data in chapters_data:
            # Handle different timestamp field names for backward compatibility
            timestamp = chapter_data.get('timestamp_original', chapter_data.get('timestamp', 0))
            title = chapter_data.get('title', '')
            
            if not title:
                continue  # Skip chapters without titles
                
            chapters.append(Chapter(timestamp=timestamp, title=title))
        
        if not chapters:
            raise ValueError("No valid chapters found in file")
            
        return chapters
        
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        raise MeetingVideoChapterError(
            f"Failed to parse existing chapters file: {chapters_raw_path}",
            {"cause": str(e), "suggestion": "Delete the file to regenerate chapters"}
        )
    except Exception as e:
        raise MeetingVideoChapterError(
            f"Error reading chapters file: {chapters_raw_path}",
            {"cause": str(e)}
        )


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
        input_type: Type of input file ('audio' or 'video')
        audio_chapters_file: Path to audio-specific chapters file (for audio inputs)
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
    input_type: str = 'video'  # Default to video for backward compatibility
    audio_chapters_file: Optional[str] = None


def run_pipeline(input_path: str, config: Config, progress_callback=None) -> PipelineResult:
    """Execute the complete audio/video chapter processing pipeline.
    
    This function orchestrates all processing steps in sequence:
    1. File type detection and validation
    2. Audio extraction (for video) or direct audio use (for audio files)
    3. Transcription using Whisper
    4. Chapter identification using AI
    5. Output generation (video with chapters or audio-specific outputs)
    
    The pipeline halts on the first error and reports which step failed.
    If skip_existing is enabled, existing intermediate files are reused.
    
    Args:
        input_path: Path to the input audio or video file
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
        input_file = Path(input_path)
        
        # Step 0: File Type Detection and Validation
        file_type = FileTypeDetector.detect_file_type(input_path)
        
        # Determine output directory
        if config.output_dir:
            output_dir = Path(config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = input_file.parent
        
        # Define intermediate file paths
        audio_path = output_dir / f"{input_file.stem}.mp3"
        transcript_path = output_dir / f"{input_file.stem}_transcript.json"
        chapters_raw_path = output_dir / f"{input_file.stem}_chapters_raw.txt"
        notes_path = output_dir / f"{input_file.stem}_notes.json"
        subtitle_path = output_dir / f"{input_file.stem}_chaptered.srt"
        
        # Set input type in result
        result.input_type = file_type
        
        # Step 1: Audio Extraction (conditional based on input type)
        step_start_time = time.time()
        if progress_callback:
            if file_type == 'video':
                progress_callback(1, "Extracting audio", "start")
            else:
                progress_callback(1, "Validating audio file", "start")
        
        result.step_failed = "audio processing"
        
        if file_type == 'video':
            # Extract audio from video file
            if config.skip_existing and audio_path.exists():
                # Reuse existing audio file
                result.audio_file = str(audio_path)
                warnings.append(f"Reusing existing audio file: {audio_path}")
            else:
                extractor = AudioExtractor()
                result.audio_file = extractor.extract(input_path, str(audio_path))
        else:  # file_type == 'audio'
            # Use audio file directly, but validate it first
            FileTypeDetector.validate_audio_file(input_path)
            result.audio_file = input_path
            
        step_timings["audio_processing"] = time.time() - step_start_time
        if progress_callback:
            if file_type == 'video':
                progress_callback(1, "Extracting audio", "complete")
            else:
                progress_callback(1, "Validating audio file", "complete")
        print(f"⏱️  Step 1 completed in {step_timings['audio_processing']:.2f}s")
        
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
            chapters = _load_existing_chapters(str(chapters_raw_path))
            result.chapters = chapters
            result.chapters_file = str(chapters_raw_path)
            if notes_path.exists():
                result.notes_file = str(notes_path)
            warnings.append(f"Reusing existing chapters file: {chapters_raw_path}")
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
        
        # Step 4: Output Generation (conditional based on input type)
        step_start_time = time.time()
        if progress_callback:
            if file_type == 'video':
                progress_callback(4, "Merging chapters into video", "start")
            else:
                progress_callback(4, "Generating audio outputs", "start")
        
        result.step_failed = "output generation"
        
        if file_type == 'video':
            # Generate chaptered video file
            output_mkv_path = output_dir / f"{input_file.stem}_chaptered.mkv"
            merger = ChapterMerger()
            result.output_mkv = merger.merge(
                input_path, 
                chapters, 
                str(output_mkv_path),
                overlay_titles=config.overlay_chapter_titles
            )
        else:  # file_type == 'audio'
            # Generate audio-specific outputs (chapters file with metadata)
            audio_chapters_path = output_dir / f"{input_file.stem}_audio_chapters.json"
            
            # Create audio-specific chapters file with additional metadata
            audio_chapters_data = {
                "input_file": input_path,
                "input_type": "audio",
                "duration": getattr(chapters[-1], 'timestamp', 0) if chapters else 0,
                "chapters": [
                    {
                        "timestamp": chapter.timestamp,
                        "timestamp_formatted": f"{int(chapter.timestamp // 60):02d}:{int(chapter.timestamp % 60):02d}",
                        "title": chapter.title
                    }
                    for chapter in chapters
                ],
                "total_chapters": len(chapters)
            }
            
            with open(audio_chapters_path, 'w', encoding='utf-8') as f:
                json.dump(audio_chapters_data, f, indent=2, ensure_ascii=False)
            
            result.audio_chapters_file = str(audio_chapters_path)
        
        step_timings["output_generation"] = time.time() - step_start_time
        if progress_callback:
            if file_type == 'video':
                progress_callback(4, "Merging chapters into video", "complete")
            else:
                progress_callback(4, "Generating audio outputs", "complete")
        print(f"⏱️  Step 4 completed in {step_timings['output_generation']:.2f}s")
        
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
