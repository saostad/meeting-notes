#!/usr/bin/env python3
"""
Command-line interface for the Meeting Video Chapter Tool.

This module provides the CLI entry point for processing MKV video files
to add chapter markers based on automatic transcription and analysis.
"""

import argparse
import sys
from pathlib import Path
from typing import NoReturn

# Add parent directory to path for imports when running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config, ConfigurationError
from src.pipeline import run_pipeline, PipelineResult
from src.errors import MeetingVideoChapterError


def format_result(result: PipelineResult) -> str:
    """Format pipeline result for display to user.
    
    Args:
        result: The pipeline result to format
        
    Returns:
        Formatted string for display
    """
    lines = []
    
    if result.success:
        lines.append("✓ Processing completed successfully!")
        lines.append("")
        lines.append("Generated files:")
        
        if result.audio_file:
            lines.append(f"  Audio: {result.audio_file}")
        if result.transcript_file:
            lines.append(f"  Transcript: {result.transcript_file}")
        if result.subtitle_file:
            lines.append(f"  Subtitles: {result.subtitle_file}")
        if result.output_mkv:
            lines.append(f"  Chaptered video: {result.output_mkv}")
        
        if result.chapters:
            lines.append("")
            lines.append(f"Chapters identified: {len(result.chapters)}")
            for i, chapter in enumerate(result.chapters, 1):
                timestamp_min = int(chapter.timestamp // 60)
                timestamp_sec = int(chapter.timestamp % 60)
                lines.append(f"  {i}. [{timestamp_min:02d}:{timestamp_sec:02d}] {chapter.title}")
        
        # Display warnings if any
        if result.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in result.warnings:
                lines.append(f"  ⚠ {warning}")
    else:
        lines.append("✗ Processing failed")
        lines.append("")
        
        if result.step_failed:
            lines.append(f"Failed at step: {result.step_failed}")
        
        if result.error:
            lines.append("")
            lines.append(result.error)
        
        # Show what was generated before failure
        if result.audio_file or result.transcript_file:
            lines.append("")
            lines.append("Intermediate files generated before failure:")
            if result.audio_file:
                lines.append(f"  Audio: {result.audio_file}")
            if result.transcript_file:
                lines.append(f"  Transcript: {result.transcript_file}")
        
        # Display warnings if any
        if result.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in result.warnings:
                lines.append(f"  ⚠ {warning}")
    
    return "\n".join(lines)


def main() -> int:
    """Main entry point for the CLI.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Add chapter markers to meeting video files using automatic transcription and analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s meeting.mkv
  %(prog)s meeting.mkv --output-dir ./processed
  %(prog)s meeting.mkv --skip-existing
  %(prog)s meeting.mkv -o ./output -s

Configuration:
  Set GEMINI_API_KEY in environment or .env file.
  See .env.example for all configuration options.
        """
    )
    
    parser.add_argument(
        "input_file",
        help="Path to the input MKV video file"
    )
    
    parser.add_argument(
        "-o", "--output-dir",
        dest="output_dir",
        help="Directory where generated files will be saved (default: same as input file)"
    )
    
    parser.add_argument(
        "-s", "--skip-existing",
        dest="skip_existing",
        action="store_true",
        help="Skip regenerating intermediate files if they already exist"
    )
    
    parser.add_argument(
        "--env-file",
        dest="env_file",
        default=".env",
        help="Path to .env file (default: .env)"
    )
    
    args = parser.parse_args()
    
    try:
        # Validate input file exists
        input_path = Path(args.input_file)
        if not input_path.exists():
            print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
            return 1
        
        if not input_path.suffix.lower() == ".mkv":
            print(f"Error: Input file must be an MKV file: {args.input_file}", file=sys.stderr)
            return 1
        
        # Load configuration
        print("Loading configuration...")
        try:
            config = Config.load(env_file=args.env_file)
        except ConfigurationError as e:
            print(str(e), file=sys.stderr)
            return 1
        
        # Override config with command-line arguments
        if args.output_dir:
            config.output_dir = args.output_dir
        if args.skip_existing:
            config.skip_existing = True
        
        # Display processing start
        print(f"Processing: {input_path.name}")
        print("")
        
        # Execute pipeline with progress messages
        print("Step 1/5: Extracting audio...")
        print("Step 2/5: Transcribing audio (this may take a while)...")
        print("Step 3/5: Identifying chapters...")
        print("Step 4/5: Merging chapters into video...")
        print("Step 5/5: Generating subtitles...")
        print("")
        
        # Run the pipeline
        result = run_pipeline(str(input_path), config)
        
        # Display results
        print(format_result(result))
        
        # Return appropriate exit code
        return 0 if result.success else 1
    
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user", file=sys.stderr)
        return 1
    
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
