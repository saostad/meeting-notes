"""Unit tests for audio extraction component."""

import os
import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.audio_extractor import AudioExtractor
from src.errors import FileSystemError, DependencyError, ProcessingError


class TestAudioExtractorInit:
    """Tests for AudioExtractor initialization."""
    
    def test_init_with_ffmpeg_available(self):
        """Test initialization succeeds when ffmpeg is available."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            extractor = AudioExtractor()
            assert extractor is not None
    
    def test_init_without_ffmpeg(self):
        """Test initialization fails when ffmpeg is not available."""
        with patch('shutil.which', return_value=None):
            with pytest.raises(DependencyError) as exc_info:
                AudioExtractor()
            
            assert "ffmpeg not found" in str(exc_info.value)
            assert "ffmpeg" in str(exc_info.value)


class TestValidateMkv:
    """Tests for validate_mkv method."""
    
    def test_validate_nonexistent_file(self, tmp_path):
        """Test validation fails for nonexistent file."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            extractor = AudioExtractor()
            
            nonexistent = tmp_path / "nonexistent.mkv"
            
            with pytest.raises(FileSystemError) as exc_info:
                extractor.validate_mkv(str(nonexistent))
            
            assert "does not exist" in str(exc_info.value)
            assert str(nonexistent) in str(exc_info.value)
    
    def test_validate_directory_not_file(self, tmp_path):
        """Test validation fails when path is a directory."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            extractor = AudioExtractor()
            
            directory = tmp_path / "test_dir"
            directory.mkdir()
            
            with pytest.raises(FileSystemError) as exc_info:
                extractor.validate_mkv(str(directory))
            
            assert "not a file" in str(exc_info.value)
    
    def test_validate_file_without_audio(self, tmp_path):
        """Test validation fails for file without audio track."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            extractor = AudioExtractor()
            
            # Create a dummy file
            test_file = tmp_path / "test.mkv"
            test_file.write_text("dummy content")
            
            # Mock ffprobe to return no audio
            with patch.object(extractor, '_has_audio_track', return_value=False):
                with pytest.raises(ProcessingError) as exc_info:
                    extractor.validate_mkv(str(test_file))
                
                assert "no audio track" in str(exc_info.value)
    
    def test_validate_file_with_audio(self, tmp_path):
        """Test validation succeeds for file with audio track."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            extractor = AudioExtractor()
            
            # Create a dummy file
            test_file = tmp_path / "test.mkv"
            test_file.write_text("dummy content")
            
            # Mock ffprobe to return audio present
            with patch.object(extractor, '_has_audio_track', return_value=True):
                result = extractor.validate_mkv(str(test_file))
                assert result is True


class TestHasAudioTrack:
    """Tests for _has_audio_track method."""
    
    def test_has_audio_track_present(self, tmp_path):
        """Test detection of audio track when present."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            extractor = AudioExtractor()
            
            test_file = tmp_path / "test.mkv"
            test_file.write_text("dummy")
            
            # Mock subprocess to return audio
            mock_result = Mock()
            mock_result.stdout = "audio"
            mock_result.returncode = 0
            
            with patch('subprocess.run', return_value=mock_result):
                result = extractor._has_audio_track(str(test_file))
                assert result is True
    
    def test_has_audio_track_absent(self, tmp_path):
        """Test detection when audio track is absent."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            extractor = AudioExtractor()
            
            test_file = tmp_path / "test.mkv"
            test_file.write_text("dummy")
            
            # Mock subprocess to return no audio
            mock_result = Mock()
            mock_result.stdout = ""
            mock_result.returncode = 0
            
            with patch('subprocess.run', return_value=mock_result):
                result = extractor._has_audio_track(str(test_file))
                assert result is False
    
    def test_has_audio_track_ffprobe_fails(self, tmp_path):
        """Test handling of ffprobe failure."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            extractor = AudioExtractor()
            
            test_file = tmp_path / "test.mkv"
            test_file.write_text("dummy")
            
            # Mock subprocess to raise exception
            with patch('subprocess.run', side_effect=Exception("ffprobe error")):
                with pytest.raises(DependencyError) as exc_info:
                    extractor._has_audio_track(str(test_file))
                
                assert "ffprobe" in str(exc_info.value)


class TestExtract:
    """Tests for extract method."""
    
    def test_extract_with_default_output_path(self, tmp_path):
        """Test extraction with default output path."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            extractor = AudioExtractor()
            
            # Create input file
            input_file = tmp_path / "test.mkv"
            input_file.write_text("dummy mkv content")
            
            # Mock validation
            with patch.object(extractor, 'validate_mkv', return_value=True):
                # Mock ffmpeg execution
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stderr = ""
                
                with patch('subprocess.run', return_value=mock_result):
                    # Create the expected output file (simulating ffmpeg)
                    expected_output = tmp_path / "test.mp3"
                    
                    def create_output(*args, **kwargs):
                        # Extract the output path from ffmpeg args
                        output_path = args[0][-1]
                        Path(output_path).write_bytes(b"fake mp3 data")
                        return mock_result
                    
                    with patch('subprocess.run', side_effect=create_output):
                        result = extractor.extract(str(input_file))
                        
                        assert result == str(expected_output)
                        assert Path(result).exists()
    
    def test_extract_with_custom_output_path(self, tmp_path):
        """Test extraction with custom output path."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            extractor = AudioExtractor()
            
            # Create input file
            input_file = tmp_path / "test.mkv"
            input_file.write_text("dummy mkv content")
            
            # Custom output path
            output_dir = tmp_path / "output"
            output_file = output_dir / "custom.mp3"
            
            # Mock validation
            with patch.object(extractor, 'validate_mkv', return_value=True):
                # Mock ffmpeg execution
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stderr = ""
                
                def create_output(*args, **kwargs):
                    # Extract the output path from ffmpeg args
                    output_path = args[0][-1]
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_bytes(b"fake mp3 data")
                    return mock_result
                
                with patch('subprocess.run', side_effect=create_output):
                    result = extractor.extract(str(input_file), str(output_file))
                    
                    assert result == str(output_file)
                    assert Path(result).exists()
    
    def test_extract_ffmpeg_failure(self, tmp_path):
        """Test handling of ffmpeg failure."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            extractor = AudioExtractor()
            
            # Create input file
            input_file = tmp_path / "test.mkv"
            input_file.write_text("dummy mkv content")
            
            # Mock validation
            with patch.object(extractor, 'validate_mkv', return_value=True):
                # Mock ffmpeg failure
                mock_result = Mock()
                mock_result.returncode = 1
                mock_result.stderr = "ffmpeg error: invalid codec"
                
                with patch('subprocess.run', return_value=mock_result):
                    with pytest.raises(ProcessingError) as exc_info:
                        extractor.extract(str(input_file))
                    
                    assert "Audio extraction failed" in str(exc_info.value)
                    assert "ffmpeg" in str(exc_info.value)
    
    def test_extract_preserves_original_on_failure(self, tmp_path):
        """Test that original file is preserved when extraction fails."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            extractor = AudioExtractor()
            
            # Create input file with specific content
            input_file = tmp_path / "test.mkv"
            original_content = b"original mkv content"
            input_file.write_bytes(original_content)
            
            # Mock validation
            with patch.object(extractor, 'validate_mkv', return_value=True):
                # Mock ffmpeg failure
                mock_result = Mock()
                mock_result.returncode = 1
                mock_result.stderr = "ffmpeg error"
                
                with patch('subprocess.run', return_value=mock_result):
                    with pytest.raises(ProcessingError):
                        extractor.extract(str(input_file))
                    
                    # Verify original file is unchanged
                    assert input_file.exists()
                    assert input_file.read_bytes() == original_content
    
    def test_extract_cleans_up_temp_file_on_failure(self, tmp_path):
        """Test that temporary files are cleaned up on failure."""
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            extractor = AudioExtractor()
            
            # Create input file
            input_file = tmp_path / "test.mkv"
            input_file.write_text("dummy mkv content")
            
            # Mock validation
            with patch.object(extractor, 'validate_mkv', return_value=True):
                # Mock ffmpeg failure
                mock_result = Mock()
                mock_result.returncode = 1
                mock_result.stderr = "ffmpeg error"
                
                def create_temp_then_fail(*args, **kwargs):
                    # Create temp file
                    output_path = args[0][-1]
                    Path(output_path).write_bytes(b"temp data")
                    return mock_result
                
                with patch('subprocess.run', side_effect=create_temp_then_fail):
                    with pytest.raises(ProcessingError):
                        extractor.extract(str(input_file))
                    
                    # Verify no .tmp.mp3 files remain
                    temp_files = list(tmp_path.glob("*.tmp.mp3"))
                    assert len(temp_files) == 0
