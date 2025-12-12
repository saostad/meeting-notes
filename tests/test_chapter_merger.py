"""Unit tests for the ChapterMerger class."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.chapter_merger import ChapterMerger
from src.chapter import Chapter
from src.errors import FileSystemError, DependencyError, ValidationError, ProcessingError


class TestChapterMerger:
    """Test suite for ChapterMerger class."""
    
    def test_init_verifies_ffmpeg(self):
        """Test that initialization verifies ffmpeg is available."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            merger = ChapterMerger()
            assert merger is not None
    
    def test_init_raises_error_when_ffmpeg_missing(self):
        """Test that initialization raises error when ffmpeg is not found."""
        with patch('shutil.which', return_value=None):
            with pytest.raises(DependencyError) as exc_info:
                ChapterMerger()
            assert "ffmpeg not found" in str(exc_info.value)
            assert exc_info.value.context["dependency"] == "ffmpeg"
    
    def test_validate_chapters_with_valid_list(self):
        """Test that validate_chapters accepts valid chapter lists."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            merger = ChapterMerger()
            chapters = [
                Chapter(timestamp=0.0, title="Introduction"),
                Chapter(timestamp=60.0, title="Main Content"),
                Chapter(timestamp=120.0, title="Conclusion")
            ]
            assert merger.validate_chapters(chapters) is True
    
    def test_validate_chapters_with_empty_list(self):
        """Test that validate_chapters rejects empty lists."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            merger = ChapterMerger()
            with pytest.raises(ValidationError) as exc_info:
                merger.validate_chapters([])
            assert "validation failed" in str(exc_info.value).lower()
    
    def test_validate_chapters_with_duplicate_timestamps(self):
        """Test that validate_chapters rejects duplicate timestamps."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            merger = ChapterMerger()
            chapters = [
                Chapter(timestamp=0.0, title="Introduction"),
                Chapter(timestamp=0.0, title="Duplicate")
            ]
            with pytest.raises(ValidationError) as exc_info:
                merger.validate_chapters(chapters)
            assert "unique" in str(exc_info.value).lower()
    
    def test_validate_chapters_with_unordered_timestamps(self):
        """Test that validate_chapters rejects unordered timestamps."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            merger = ChapterMerger()
            chapters = [
                Chapter(timestamp=60.0, title="Second"),
                Chapter(timestamp=0.0, title="First")
            ]
            with pytest.raises(ValidationError) as exc_info:
                merger.validate_chapters(chapters)
            assert "ascending" in str(exc_info.value).lower()
    
    def test_create_metadata_file_generates_valid_format(self):
        """Test that create_metadata_file generates proper ffmpeg format."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            merger = ChapterMerger()
            chapters = [
                Chapter(timestamp=0.0, title="Introduction"),
                Chapter(timestamp=60.5, title="Main Content"),
                Chapter(timestamp=120.0, title="Conclusion")
            ]
            
            metadata_path = merger.create_metadata_file(chapters)
            
            try:
                assert os.path.exists(metadata_path)
                
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for required elements
                assert ";FFMETADATA1" in content
                assert "[CHAPTER]" in content
                assert "TIMEBASE=1/1000" in content
                assert "START=0" in content
                assert "START=60500" in content
                assert "START=120000" in content
                assert "title=Introduction" in content
                assert "title=Main Content" in content
                assert "title=Conclusion" in content
            finally:
                if os.path.exists(metadata_path):
                    os.unlink(metadata_path)
    
    def test_create_metadata_file_with_invalid_chapters(self):
        """Test that create_metadata_file rejects invalid chapters."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            merger = ChapterMerger()
            chapters = []
            
            with pytest.raises(ValidationError):
                merger.create_metadata_file(chapters)
    
    def test_merge_validates_input_file_exists(self):
        """Test that merge validates input file existence."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            merger = ChapterMerger()
            chapters = [Chapter(timestamp=0.0, title="Test")]
            
            with pytest.raises(FileSystemError) as exc_info:
                merger.merge("/nonexistent/file.mkv", chapters)
            assert "does not exist" in str(exc_info.value).lower()
    
    def test_merge_validates_chapters(self):
        """Test that merge validates chapter list."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            merger = ChapterMerger()
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix='.mkv', delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                with pytest.raises(ValidationError):
                    merger.merge(tmp_path, [])  # Empty chapter list
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
    
    @patch('subprocess.run')
    def test_merge_calls_ffmpeg_correctly(self, mock_run):
        """Test that merge calls ffmpeg with correct arguments."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            merger = ChapterMerger()
            chapters = [
                Chapter(timestamp=0.0, title="Introduction"),
                Chapter(timestamp=60.0, title="Main Content")
            ]
            
            # Create temporary input file
            with tempfile.NamedTemporaryFile(suffix='.mkv', delete=False) as tmp:
                tmp_path = tmp.name
                tmp.write(b'fake mkv content')
            
            # Mock successful ffmpeg execution
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = ""
            
            output_path = None
            try:
                # Calculate expected output path
                expected_output = str(Path(tmp_path).parent / f"{Path(tmp_path).stem}_chaptered.mkv")
                temp_output = Path(expected_output).parent / f"{Path(expected_output).stem}.tmp.mkv"
                
                def create_output(*args, **kwargs):
                    # Create the temp output file when ffmpeg is called
                    with open(temp_output, 'wb') as f:
                        f.write(b'fake output')
                    return mock_result
                
                mock_run.side_effect = create_output
                
                output_path = merger.merge(tmp_path, chapters)
                
                # Verify ffmpeg was called
                assert mock_run.called
                call_args = mock_run.call_args[0][0]
                assert call_args[0] == "ffmpeg"
                assert "-i" in call_args
                assert "-map_metadata" in call_args
                assert "-codec" in call_args
                assert "copy" in call_args
                
                # Verify output file was created
                assert os.path.exists(output_path)
                assert output_path.endswith('_chaptered.mkv')
                
            finally:
                # Cleanup
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                if output_path and os.path.exists(output_path):
                    os.unlink(output_path)
    
    @patch('subprocess.run')
    def test_merge_preserves_original_on_failure(self, mock_run):
        """Test that merge preserves original file when ffmpeg fails."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            merger = ChapterMerger()
            chapters = [Chapter(timestamp=0.0, title="Test")]
            
            # Create temporary input file with content
            with tempfile.NamedTemporaryFile(suffix='.mkv', delete=False) as tmp:
                tmp_path = tmp.name
                original_content = b'original mkv content'
                tmp.write(original_content)
            
            # Mock failed ffmpeg execution
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "ffmpeg error"
            mock_run.return_value = mock_result
            
            try:
                with pytest.raises(ProcessingError):
                    merger.merge(tmp_path, chapters)
                
                # Verify original file is unchanged
                assert os.path.exists(tmp_path)
                with open(tmp_path, 'rb') as f:
                    assert f.read() == original_content
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
    
    @patch('subprocess.run')
    def test_merge_with_custom_output_path(self, mock_run):
        """Test that merge respects custom output path."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            merger = ChapterMerger()
            chapters = [Chapter(timestamp=0.0, title="Test")]
            
            # Create temporary input file
            with tempfile.NamedTemporaryFile(suffix='.mkv', delete=False) as tmp:
                tmp_path = tmp.name
                tmp.write(b'fake mkv content')
            
            custom_output = tmp_path.replace('.mkv', '_custom.mkv')
            
            # Mock successful ffmpeg execution
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            try:
                # Create a fake output file for the test
                temp_output = Path(custom_output).parent / f"{Path(custom_output).stem}.tmp.mkv"
                
                def create_output(*args, **kwargs):
                    with open(temp_output, 'wb') as f:
                        f.write(b'fake output')
                    return mock_result
                
                mock_run.side_effect = create_output
                
                output_path = merger.merge(tmp_path, chapters, output_path=custom_output)
                
                assert output_path == custom_output
                assert os.path.exists(output_path)
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                if os.path.exists(custom_output):
                    os.unlink(custom_output)
