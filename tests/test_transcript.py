"""Unit tests for transcript data models."""

import json
import pytest
from pathlib import Path
from src.transcript import Transcript, TranscriptSegment


class TestTranscriptSegment:
    """Tests for TranscriptSegment dataclass."""
    
    def test_create_valid_segment(self):
        """Test creating a valid transcript segment."""
        segment = TranscriptSegment(
            start_time=0.0,
            end_time=5.5,
            text="Hello world"
        )
        
        assert segment.start_time == 0.0
        assert segment.end_time == 5.5
        assert segment.text == "Hello world"
    
    def test_segment_with_negative_start_time(self):
        """Test that negative start_time raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            TranscriptSegment(
                start_time=-1.0,
                end_time=5.0,
                text="Test"
            )
        
        assert "start_time must be non-negative" in str(exc_info.value)
    
    def test_segment_with_negative_end_time(self):
        """Test that negative end_time raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            TranscriptSegment(
                start_time=0.0,
                end_time=-1.0,
                text="Test"
            )
        
        assert "end_time must be non-negative" in str(exc_info.value)
    
    def test_segment_with_end_before_start(self):
        """Test that end_time < start_time raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            TranscriptSegment(
                start_time=10.0,
                end_time=5.0,
                text="Test"
            )
        
        assert "end_time" in str(exc_info.value)
        assert "start_time" in str(exc_info.value)
    
    def test_segment_with_equal_times(self):
        """Test segment with start_time == end_time is valid."""
        segment = TranscriptSegment(
            start_time=5.0,
            end_time=5.0,
            text="Test"
        )
        
        assert segment.start_time == segment.end_time


class TestTranscript:
    """Tests for Transcript dataclass."""
    
    def test_create_valid_transcript(self):
        """Test creating a valid transcript."""
        segments = [
            TranscriptSegment(0.0, 5.0, "First segment"),
            TranscriptSegment(5.0, 10.0, "Second segment")
        ]
        
        transcript = Transcript(
            segments=segments,
            full_text="First segment Second segment",
            duration=10.0
        )
        
        assert len(transcript.segments) == 2
        assert transcript.full_text == "First segment Second segment"
        assert transcript.duration == 10.0
    
    def test_transcript_with_negative_duration(self):
        """Test that negative duration raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Transcript(
                segments=[],
                full_text="",
                duration=-1.0
            )
        
        assert "duration must be non-negative" in str(exc_info.value)
    
    def test_transcript_with_empty_segments(self):
        """Test transcript with no segments is valid."""
        transcript = Transcript(
            segments=[],
            full_text="",
            duration=0.0
        )
        
        assert len(transcript.segments) == 0
        assert transcript.full_text == ""
        assert transcript.duration == 0.0


class TestTranscriptSerialization:
    """Tests for Transcript serialization (to_file and from_file)."""
    
    def test_to_file_creates_json(self, tmp_path):
        """Test that to_file creates a valid JSON file."""
        segments = [
            TranscriptSegment(0.0, 5.0, "First segment"),
            TranscriptSegment(5.0, 10.0, "Second segment")
        ]
        
        transcript = Transcript(
            segments=segments,
            full_text="First segment Second segment",
            duration=10.0
        )
        
        output_file = tmp_path / "transcript.json"
        transcript.to_file(str(output_file))
        
        assert output_file.exists()
        
        # Verify JSON content
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        assert "segments" in data
        assert "full_text" in data
        assert "duration" in data
        assert len(data["segments"]) == 2
        assert data["duration"] == 10.0
    
    def test_to_file_creates_parent_directory(self, tmp_path):
        """Test that to_file creates parent directories if needed."""
        segments = [TranscriptSegment(0.0, 5.0, "Test")]
        transcript = Transcript(
            segments=segments,
            full_text="Test",
            duration=5.0
        )
        
        nested_path = tmp_path / "nested" / "dir" / "transcript.json"
        transcript.to_file(str(nested_path))
        
        assert nested_path.exists()
    
    def test_from_file_loads_transcript(self, tmp_path):
        """Test that from_file correctly loads a transcript."""
        # Create a transcript file
        data = {
            "segments": [
                {"start_time": 0.0, "end_time": 5.0, "text": "First"},
                {"start_time": 5.0, "end_time": 10.0, "text": "Second"}
            ],
            "full_text": "First Second",
            "duration": 10.0
        }
        
        file_path = tmp_path / "transcript.json"
        with open(file_path, 'w') as f:
            json.dump(data, f)
        
        # Load transcript
        transcript = Transcript.from_file(str(file_path))
        
        assert len(transcript.segments) == 2
        assert transcript.segments[0].text == "First"
        assert transcript.segments[1].text == "Second"
        assert transcript.full_text == "First Second"
        assert transcript.duration == 10.0
    
    def test_from_file_nonexistent_file(self, tmp_path):
        """Test that from_file raises FileNotFoundError for missing file."""
        nonexistent = tmp_path / "nonexistent.json"
        
        with pytest.raises(FileNotFoundError) as exc_info:
            Transcript.from_file(str(nonexistent))
        
        assert "not found" in str(exc_info.value)
    
    def test_from_file_directory_not_file(self, tmp_path):
        """Test that from_file raises ValueError for directory."""
        directory = tmp_path / "test_dir"
        directory.mkdir()
        
        with pytest.raises(ValueError) as exc_info:
            Transcript.from_file(str(directory))
        
        assert "not a file" in str(exc_info.value)
    
    def test_from_file_missing_segments_field(self, tmp_path):
        """Test that from_file raises ValueError for missing segments."""
        data = {
            "full_text": "Test",
            "duration": 5.0
        }
        
        file_path = tmp_path / "invalid.json"
        with open(file_path, 'w') as f:
            json.dump(data, f)
        
        with pytest.raises(ValueError) as exc_info:
            Transcript.from_file(str(file_path))
        
        assert "missing 'segments'" in str(exc_info.value)
    
    def test_from_file_missing_full_text_field(self, tmp_path):
        """Test that from_file raises ValueError for missing full_text."""
        data = {
            "segments": [],
            "duration": 5.0
        }
        
        file_path = tmp_path / "invalid.json"
        with open(file_path, 'w') as f:
            json.dump(data, f)
        
        with pytest.raises(ValueError) as exc_info:
            Transcript.from_file(str(file_path))
        
        assert "missing 'full_text'" in str(exc_info.value)
    
    def test_from_file_missing_duration_field(self, tmp_path):
        """Test that from_file raises ValueError for missing duration."""
        data = {
            "segments": [],
            "full_text": "Test"
        }
        
        file_path = tmp_path / "invalid.json"
        with open(file_path, 'w') as f:
            json.dump(data, f)
        
        with pytest.raises(ValueError) as exc_info:
            Transcript.from_file(str(file_path))
        
        assert "missing 'duration'" in str(exc_info.value)
    
    def test_round_trip_serialization(self, tmp_path):
        """Test that saving and loading preserves transcript data."""
        segments = [
            TranscriptSegment(0.0, 5.5, "First segment"),
            TranscriptSegment(5.5, 12.3, "Second segment"),
            TranscriptSegment(12.3, 20.0, "Third segment")
        ]
        
        original = Transcript(
            segments=segments,
            full_text="First segment Second segment Third segment",
            duration=20.0
        )
        
        file_path = tmp_path / "transcript.json"
        original.to_file(str(file_path))
        loaded = Transcript.from_file(str(file_path))
        
        assert len(loaded.segments) == len(original.segments)
        assert loaded.full_text == original.full_text
        assert loaded.duration == original.duration
        
        for orig_seg, loaded_seg in zip(original.segments, loaded.segments):
            assert loaded_seg.start_time == orig_seg.start_time
            assert loaded_seg.end_time == orig_seg.end_time
            assert loaded_seg.text == orig_seg.text
