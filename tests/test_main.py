"""
Unit tests for the CLI interface.

Tests the main() function and command-line argument parsing.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

from src.main import main, format_result
from src.pipeline import PipelineResult
from src.chapter import Chapter


class TestFormatResult:
    """Test the format_result function."""
    
    def test_format_successful_result(self):
        """Test formatting a successful pipeline result."""
        chapters = [
            Chapter(timestamp=0.0, title="Introduction"),
            Chapter(timestamp=300.0, title="Main Discussion"),
            Chapter(timestamp=600.0, title="Conclusion")
        ]
        
        result = PipelineResult(
            success=True,
            output_mkv="/path/to/output.mkv",
            audio_file="/path/to/audio.mp3",
            transcript_file="/path/to/transcript.json",
            chapters=chapters
        )
        
        formatted = format_result(result)
        
        assert "✓ Processing completed successfully!" in formatted
        assert "Generated files:" in formatted
        assert "/path/to/audio.mp3" in formatted
        assert "/path/to/transcript.json" in formatted
        assert "/path/to/output.mkv" in formatted
        assert "Chapters identified: 3" in formatted
        assert "Introduction" in formatted
        assert "Main Discussion" in formatted
        assert "Conclusion" in formatted
    
    def test_format_successful_result_with_warnings(self):
        """Test formatting a successful result with warnings."""
        result = PipelineResult(
            success=True,
            output_mkv="/path/to/output.mkv",
            warnings=["Reusing existing audio file", "Reusing existing transcript"]
        )
        
        formatted = format_result(result)
        
        assert "✓ Processing completed successfully!" in formatted
        assert "Warnings:" in formatted
        assert "Reusing existing audio file" in formatted
        assert "Reusing existing transcript" in formatted
    
    def test_format_failed_result(self):
        """Test formatting a failed pipeline result."""
        result = PipelineResult(
            success=False,
            step_failed="transcription",
            error="Error: Transcription failed\n  File: /path/to/audio.mp3\n  Cause: Model loading failed",
            audio_file="/path/to/audio.mp3"
        )
        
        formatted = format_result(result)
        
        assert "✗ Processing failed" in formatted
        assert "Failed at step: transcription" in formatted
        assert "Transcription failed" in formatted
        assert "Intermediate files generated before failure:" in formatted
        assert "/path/to/audio.mp3" in formatted
    
    def test_format_failed_result_with_warnings(self):
        """Test formatting a failed result with warnings."""
        result = PipelineResult(
            success=False,
            step_failed="chapter merging",
            error="Error: Chapter merging failed",
            warnings=["Reusing existing audio file"]
        )
        
        formatted = format_result(result)
        
        assert "✗ Processing failed" in formatted
        assert "Warnings:" in formatted
        assert "Reusing existing audio file" in formatted


class TestMain:
    """Test the main() CLI function."""
    
    def test_main_missing_input_file(self, capsys):
        """Test main() with a non-existent input file."""
        with patch.object(sys, 'argv', ['main.py', 'nonexistent.mkv']):
            exit_code = main()
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Input file not found" in captured.err
    
    def test_main_invalid_file_extension(self, capsys, tmp_path):
        """Test main() with a non-MKV file."""
        # Create a temporary non-MKV file
        test_file = tmp_path / "test.mp4"
        test_file.write_text("dummy")
        
        with patch.object(sys, 'argv', ['main.py', str(test_file)]):
            exit_code = main()
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "must be an MKV file" in captured.err
    
    def test_main_missing_api_key(self, capsys, tmp_path, monkeypatch):
        """Test main() with missing API key configuration."""
        # Clear the API key from environment
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        
        # Create a temporary MKV file
        test_file = tmp_path / "test.mkv"
        test_file.write_text("dummy")
        
        # Create a temporary .env file without API key
        env_file = tmp_path / ".env"
        env_file.write_text("WHISPER_MODEL=openai/whisper-large-v3-turbo\n")
        
        with patch.object(sys, 'argv', ['main.py', str(test_file), '--env-file', str(env_file)]):
            exit_code = main()
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "GEMINI_API_KEY" in captured.err
    
    @patch('src.main.run_pipeline')
    def test_main_successful_execution(self, mock_run_pipeline, capsys, tmp_path):
        """Test main() with successful pipeline execution."""
        # Create a temporary MKV file
        test_file = tmp_path / "test.mkv"
        test_file.write_text("dummy")
        
        # Create a temporary .env file with API key
        env_file = tmp_path / ".env"
        env_file.write_text("GEMINI_API_KEY=test_key_123\n")
        
        # Mock successful pipeline result
        mock_result = PipelineResult(
            success=True,
            output_mkv=str(tmp_path / "test_chaptered.mkv"),
            audio_file=str(tmp_path / "test.mp3"),
            transcript_file=str(tmp_path / "test_transcript.json"),
            chapters=[Chapter(timestamp=0.0, title="Test Chapter")]
        )
        mock_run_pipeline.return_value = mock_result
        
        with patch.object(sys, 'argv', ['main.py', str(test_file), '--env-file', str(env_file)]):
            exit_code = main()
        
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "✓ Processing completed successfully!" in captured.out
        assert "Step 1/5: Extracting audio..." in captured.out
        assert "Step 2/5: Transcribing audio" in captured.out
        assert "Step 3/5: Identifying chapters..." in captured.out
        assert "Step 4/5: Merging chapters into video..." in captured.out
        assert "Step 5/5: Generating subtitles..." in captured.out
    
    @patch('src.main.run_pipeline')
    def test_main_with_output_dir_option(self, mock_run_pipeline, tmp_path):
        """Test main() with --output-dir option."""
        # Create a temporary MKV file
        test_file = tmp_path / "test.mkv"
        test_file.write_text("dummy")
        
        # Create output directory
        output_dir = tmp_path / "output"
        
        # Create a temporary .env file with API key
        env_file = tmp_path / ".env"
        env_file.write_text("GEMINI_API_KEY=test_key_123\n")
        
        # Mock successful pipeline result
        mock_result = PipelineResult(success=True)
        mock_run_pipeline.return_value = mock_result
        
        with patch.object(sys, 'argv', ['main.py', str(test_file), '--output-dir', str(output_dir), '--env-file', str(env_file)]):
            exit_code = main()
        
        assert exit_code == 0
        # Verify that run_pipeline was called with correct config
        call_args = mock_run_pipeline.call_args
        config = call_args[0][1]
        assert config.output_dir == str(output_dir)
    
    @patch('src.main.run_pipeline')
    def test_main_with_skip_existing_option(self, mock_run_pipeline, tmp_path):
        """Test main() with --skip-existing option."""
        # Create a temporary MKV file
        test_file = tmp_path / "test.mkv"
        test_file.write_text("dummy")
        
        # Create a temporary .env file with API key
        env_file = tmp_path / ".env"
        env_file.write_text("GEMINI_API_KEY=test_key_123\n")
        
        # Mock successful pipeline result
        mock_result = PipelineResult(success=True)
        mock_run_pipeline.return_value = mock_result
        
        with patch.object(sys, 'argv', ['main.py', str(test_file), '--skip-existing', '--env-file', str(env_file)]):
            exit_code = main()
        
        assert exit_code == 0
        # Verify that run_pipeline was called with correct config
        call_args = mock_run_pipeline.call_args
        config = call_args[0][1]
        assert config.skip_existing is True
    
    @patch('src.main.run_pipeline')
    def test_main_failed_pipeline(self, mock_run_pipeline, capsys, tmp_path):
        """Test main() with failed pipeline execution."""
        # Create a temporary MKV file
        test_file = tmp_path / "test.mkv"
        test_file.write_text("dummy")
        
        # Create a temporary .env file with API key
        env_file = tmp_path / ".env"
        env_file.write_text("GEMINI_API_KEY=test_key_123\n")
        
        # Mock failed pipeline result
        mock_result = PipelineResult(
            success=False,
            step_failed="transcription",
            error="Error: Transcription failed"
        )
        mock_run_pipeline.return_value = mock_result
        
        with patch.object(sys, 'argv', ['main.py', str(test_file), '--env-file', str(env_file)]):
            exit_code = main()
        
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "✗ Processing failed" in captured.out
        assert "Failed at step: transcription" in captured.out
