"""Tests for the Chapter data model."""

import pytest
from src.chapter import Chapter, validate_chapter_list


class TestChapter:
    """Test cases for the Chapter class."""
    
    def test_valid_chapter_creation(self):
        """Test creating a valid chapter."""
        chapter = Chapter(timestamp=60.5, title="Introduction")
        assert chapter.timestamp == 60.5
        assert chapter.title == "Introduction"
    
    def test_chapter_with_zero_timestamp(self):
        """Test that zero timestamp is valid."""
        chapter = Chapter(timestamp=0.0, title="Start")
        assert chapter.timestamp == 0.0
    
    def test_chapter_strips_whitespace_from_title(self):
        """Test that whitespace is stripped from titles."""
        chapter = Chapter(timestamp=10.0, title="  Spaced Title  ")
        assert chapter.title == "Spaced Title"
    
    def test_negative_timestamp_raises_error(self):
        """Test that negative timestamps are rejected."""
        with pytest.raises(ValueError, match="timestamp must be non-negative"):
            Chapter(timestamp=-1.0, title="Invalid")
    
    def test_empty_title_raises_error(self):
        """Test that empty titles are rejected."""
        with pytest.raises(ValueError, match="title must be a non-empty string"):
            Chapter(timestamp=10.0, title="")
    
    def test_whitespace_only_title_raises_error(self):
        """Test that whitespace-only titles are rejected."""
        with pytest.raises(ValueError, match="title must be a non-empty string"):
            Chapter(timestamp=10.0, title="   ")
    
    def test_validate_method_returns_true_for_valid_chapter(self):
        """Test that validate() returns True for valid chapters."""
        chapter = Chapter(timestamp=30.0, title="Valid Chapter")
        assert chapter.validate() is True
    
    def test_to_ffmpeg_format(self):
        """Test conversion to ffmpeg metadata format."""
        chapter = Chapter(timestamp=60.5, title="Introduction")
        result = chapter.to_ffmpeg_format()
        
        assert "[CHAPTER]" in result
        assert "TIMEBASE=1/1000" in result
        assert "START=60500" in result
        assert "END=60500" in result
        assert "title=Introduction" in result
    
    def test_to_ffmpeg_format_with_zero_timestamp(self):
        """Test ffmpeg format with zero timestamp."""
        chapter = Chapter(timestamp=0.0, title="Start")
        result = chapter.to_ffmpeg_format()
        
        assert "START=0" in result
        assert "END=0" in result


class TestValidateChapterList:
    """Test cases for the validate_chapter_list function."""
    
    def test_valid_chapter_list(self):
        """Test validation of a valid chapter list."""
        chapters = [
            Chapter(timestamp=0.0, title="Introduction"),
            Chapter(timestamp=60.0, title="Main Content"),
            Chapter(timestamp=120.0, title="Conclusion")
        ]
        assert validate_chapter_list(chapters) is True
    
    def test_empty_chapter_list_raises_error(self):
        """Test that empty chapter lists are rejected."""
        with pytest.raises(ValueError, match="Chapter list cannot be empty"):
            validate_chapter_list([])
    
    def test_duplicate_timestamps_raise_error(self):
        """Test that duplicate timestamps are rejected."""
        chapters = [
            Chapter(timestamp=0.0, title="First"),
            Chapter(timestamp=60.0, title="Second"),
            Chapter(timestamp=60.0, title="Duplicate")
        ]
        with pytest.raises(ValueError, match="timestamps must be unique"):
            validate_chapter_list(chapters)
    
    def test_unsorted_timestamps_raise_error(self):
        """Test that unsorted timestamps are rejected."""
        chapters = [
            Chapter(timestamp=60.0, title="Second"),
            Chapter(timestamp=0.0, title="First"),
            Chapter(timestamp=120.0, title="Third")
        ]
        with pytest.raises(ValueError, match="timestamps must be in ascending order"):
            validate_chapter_list(chapters)
    
    def test_single_chapter_is_valid(self):
        """Test that a single chapter is valid."""
        chapters = [Chapter(timestamp=0.0, title="Only Chapter")]
        assert validate_chapter_list(chapters) is True
