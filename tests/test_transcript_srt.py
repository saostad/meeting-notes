"""Tests for SRT subtitle generation from transcripts."""

import pytest
from pathlib import Path
from src.transcript import Transcript, TranscriptSegment


def test_srt_timestamp_formatting():
    """Test SRT timestamp formatting."""
    # Test various timestamps
    assert Transcript._format_srt_timestamp(0) == "00:00:00,000"
    assert Transcript._format_srt_timestamp(1.5) == "00:00:01,500"
    assert Transcript._format_srt_timestamp(65.123) == "00:01:05,123"
    assert Transcript._format_srt_timestamp(3661.456) == "01:01:01,456"
    assert Transcript._format_srt_timestamp(7200) == "02:00:00,000"


def test_to_srt_basic(tmp_path):
    """Test basic SRT file generation."""
    # Create a simple transcript
    segments = [
        TranscriptSegment(start_time=0.0, end_time=2.5, text="Hello world"),
        TranscriptSegment(start_time=2.5, end_time=5.0, text="This is a test"),
        TranscriptSegment(start_time=5.0, end_time=8.0, text="Of subtitle generation"),
    ]
    
    transcript = Transcript(
        segments=segments,
        full_text="Hello world This is a test Of subtitle generation",
        duration=8.0
    )
    
    # Generate SRT file
    srt_path = tmp_path / "test.srt"
    transcript.to_srt(str(srt_path))
    
    # Verify file was created
    assert srt_path.exists()
    
    # Read and verify content
    content = srt_path.read_text(encoding='utf-8')
    
    # Check for expected SRT format
    assert "1\n" in content
    assert "00:00:00,000 --> 00:00:02,500" in content
    assert "Hello world" in content
    
    assert "2\n" in content
    assert "00:00:02,500 --> 00:00:05,000" in content
    assert "This is a test" in content
    
    assert "3\n" in content
    assert "00:00:05,000 --> 00:00:08,000" in content
    assert "Of subtitle generation" in content


def test_to_srt_with_long_timestamps(tmp_path):
    """Test SRT generation with timestamps over an hour."""
    segments = [
        TranscriptSegment(start_time=3600.0, end_time=3605.5, text="One hour in"),
        TranscriptSegment(start_time=7200.0, end_time=7210.0, text="Two hours in"),
    ]
    
    transcript = Transcript(
        segments=segments,
        full_text="One hour in Two hours in",
        duration=7210.0
    )
    
    srt_path = tmp_path / "long.srt"
    transcript.to_srt(str(srt_path))
    
    content = srt_path.read_text(encoding='utf-8')
    
    # Verify hour formatting
    assert "01:00:00,000 --> 01:00:05,500" in content
    assert "02:00:00,000 --> 02:00:10,000" in content


def test_to_srt_creates_parent_directory(tmp_path):
    """Test that to_srt creates parent directories if needed."""
    nested_path = tmp_path / "nested" / "dir" / "test.srt"
    
    segments = [
        TranscriptSegment(start_time=0.0, end_time=1.0, text="Test"),
    ]
    
    transcript = Transcript(
        segments=segments,
        full_text="Test",
        duration=1.0
    )
    
    # Should create nested directories
    transcript.to_srt(str(nested_path))
    
    assert nested_path.exists()
    assert nested_path.parent.exists()


def test_to_srt_with_special_characters(tmp_path):
    """Test SRT generation with special characters in text."""
    segments = [
        TranscriptSegment(start_time=0.0, end_time=2.0, text="Hello, world! How are you?"),
        TranscriptSegment(start_time=2.0, end_time=4.0, text="I'm fine, thanks. 😊"),
        TranscriptSegment(start_time=4.0, end_time=6.0, text="Testing: quotes \"like this\""),
    ]
    
    transcript = Transcript(
        segments=segments,
        full_text="Hello, world! How are you? I'm fine, thanks. 😊 Testing: quotes \"like this\"",
        duration=6.0
    )
    
    srt_path = tmp_path / "special.srt"
    transcript.to_srt(str(srt_path))
    
    content = srt_path.read_text(encoding='utf-8')
    
    # Verify special characters are preserved
    assert "Hello, world! How are you?" in content
    assert "I'm fine, thanks. 😊" in content
    assert 'Testing: quotes "like this"' in content


def test_to_srt_empty_transcript(tmp_path):
    """Test SRT generation with empty transcript."""
    transcript = Transcript(
        segments=[],
        full_text="",
        duration=0.0
    )
    
    srt_path = tmp_path / "empty.srt"
    transcript.to_srt(str(srt_path))
    
    # File should be created but essentially empty
    assert srt_path.exists()
    content = srt_path.read_text(encoding='utf-8')
    assert content.strip() == ""
