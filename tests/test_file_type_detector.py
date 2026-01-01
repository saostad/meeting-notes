"""
Unit tests for file type detection and validation.
"""

import pytest
import json
import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.file_type_detector import FileTypeDetector
from src.errors import ValidationError, FileSystemError


class TestFileTypeDetection:
    """Test file type detection based on extensions."""
    
    def test_detect_audio_file_mp3(self, tmp_path):
        """Test detection of MP3 audio files."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()
        
        result = FileTypeDetector.detect_file_type(str(audio_file))
        assert result == 'audio'
    
    def test_detect_audio_file_wav(self, tmp_path):
        """Test detection of WAV audio files."""
        audio_file = tmp_path / "test.wav"
        audio_file.touch()
        
        result = FileTypeDetector.detect_file_type(str(audio_file))
        assert result == 'audio'
    
    def test_detect_audio_file_flac(self, tmp_path):
        """Test detection of FLAC audio files."""
        audio_file = tmp_path / "test.flac"
        audio_file.touch()
        
        result = FileTypeDetector.detect_file_type(str(audio_file))
        assert result == 'audio'
    
    def test_detect_audio_file_m4a(self, tmp_path):
        """Test detection of M4A audio files."""
        audio_file = tmp_path / "test.m4a"
        audio_file.touch()
        
        result = FileTypeDetector.detect_file_type(str(audio_file))
        assert result == 'audio'
    
    def test_detect_video_file_mkv(self, tmp_path):
        """Test detection of MKV video files."""
        video_file = tmp_path / "test.mkv"
        video_file.touch()
        
        result = FileTypeDetector.detect_file_type(str(video_file))
        assert result == 'video'
    
    def test_detect_video_file_mp4(self, tmp_path):
        """Test detection of MP4 video files."""
        video_file = tmp_path / "test.mp4"
        video_file.touch()
        
        result = FileTypeDetector.detect_file_type(str(video_file))
        assert result == 'video'
    
    def test_detect_case_insensitive(self, tmp_path):
        """Test that file extension detection is case insensitive."""
        audio_file = tmp_path / "test.MP3"
        audio_file.touch()
        
        result = FileTypeDetector.detect_file_type(str(audio_file))
        assert result == 'audio'
    
    def test_detect_unsupported_format(self, tmp_path):
        """Test error handling for unsupported file formats."""
        unsupported_file = tmp_path / "test.txt"
        unsupported_file.touch()
        
        with pytest.raises(ValidationError) as exc_info:
            FileTypeDetector.detect_file_type(str(unsupported_file))
        
        error = exc_info.value
        assert "Unsupported file format" in str(error)
        assert ".txt" in str(error)
        assert "supported_formats" in error.context
    
    def test_detect_nonexistent_file(self):
        """Test error handling for nonexistent files."""
        with pytest.raises(FileSystemError) as exc_info:
            FileTypeDetector.detect_file_type("/nonexistent/file.mp3")
        
        error = exc_info.value
        assert "Input file not found" in str(error)
        assert "/nonexistent/file.mp3" in error.context["file_path"]
    
    def test_detect_directory_path(self, tmp_path):
        """Test error handling when path is a directory."""
        directory = tmp_path / "test_dir"
        directory.mkdir()
        
        with pytest.raises(FileSystemError) as exc_info:
            FileTypeDetector.detect_file_type(str(directory))
        
        error = exc_info.value
        assert "Path is not a file" in str(error)


class TestAudioFileValidation:
    """Test audio file validation using ffprobe."""
    
    @patch('subprocess.run')
    def test_validate_audio_file_success(self, mock_run, tmp_path):
        """Test successful audio file validation."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()
        
        # Mock ffprobe output
        mock_metadata = {
            'format': {
                'format_name': 'mp3',
                'duration': '120.5',
                'size': '1024000',
                'bit_rate': '128000'
            },
            'streams': [
                {
                    'codec_type': 'audio',
                    'codec_name': 'mp3',
                    'sample_rate': '44100',
                    'channels': '2'
                }
            ]
        }
        
        mock_run.return_value = MagicMock(
            stdout=json.dumps(mock_metadata),
            stderr='',
            returncode=0
        )
        
        result = FileTypeDetector.validate_audio_file(str(audio_file))
        
        assert result['file_path'] == str(audio_file)
        assert result['format_name'] == 'mp3'
        assert result['duration'] == 120.5
        assert result['audio_codec'] == 'mp3'
        assert result['sample_rate'] == 44100
        assert result['channels'] == 2
        assert result['audio_streams_count'] == 1
    
    @patch('subprocess.run')
    def test_validate_audio_file_no_audio_streams(self, mock_run, tmp_path):
        """Test validation failure when file has no audio streams."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()
        
        # Mock ffprobe output with no audio streams
        mock_metadata = {
            'format': {'format_name': 'mp3'},
            'streams': [
                {
                    'codec_type': 'video',
                    'codec_name': 'h264'
                }
            ]
        }
        
        mock_run.return_value = MagicMock(
            stdout=json.dumps(mock_metadata),
            stderr='',
            returncode=0
        )
        
        with pytest.raises(ValidationError) as exc_info:
            FileTypeDetector.validate_audio_file(str(audio_file))
        
        error = exc_info.value
        assert "No audio streams found" in str(error)
    
    @patch('subprocess.run')
    def test_validate_audio_file_invalid_duration(self, mock_run, tmp_path):
        """Test validation failure for files with invalid duration."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()
        
        # Mock ffprobe output with zero duration
        mock_metadata = {
            'format': {
                'format_name': 'mp3',
                'duration': '0',
                'size': '1024',
                'bit_rate': '128000'
            },
            'streams': [
                {
                    'codec_type': 'audio',
                    'codec_name': 'mp3',
                    'sample_rate': '44100',
                    'channels': '2'
                }
            ]
        }
        
        mock_run.return_value = MagicMock(
            stdout=json.dumps(mock_metadata),
            stderr='',
            returncode=0
        )
        
        with pytest.raises(ValidationError) as exc_info:
            FileTypeDetector.validate_audio_file(str(audio_file))
        
        error = exc_info.value
        assert "invalid duration" in str(error)
    
    @patch('subprocess.run')
    def test_validate_audio_file_ffprobe_error(self, mock_run, tmp_path):
        """Test handling of ffprobe execution errors."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()
        
        # Mock ffprobe failure
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'ffprobe', stderr='Invalid file format'
        )
        
        with pytest.raises(ValidationError) as exc_info:
            FileTypeDetector.validate_audio_file(str(audio_file))
        
        error = exc_info.value
        assert "Failed to analyze audio file" in str(error)
        assert "ffprobe" in error.context["dependency"]
    
    @patch('subprocess.run')
    def test_validate_audio_file_ffprobe_not_found(self, mock_run, tmp_path):
        """Test handling when ffprobe is not installed."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()
        
        # Mock ffprobe not found
        mock_run.side_effect = FileNotFoundError()
        
        with pytest.raises(FileSystemError) as exc_info:
            FileTypeDetector.validate_audio_file(str(audio_file))
        
        error = exc_info.value
        assert "ffprobe not found" in str(error)
    
    def test_validate_non_audio_file(self, tmp_path):
        """Test validation error when file is not audio type."""
        video_file = tmp_path / "test.mkv"
        video_file.touch()
        
        with pytest.raises(ValidationError) as exc_info:
            FileTypeDetector.validate_audio_file(str(video_file))
        
        error = exc_info.value
        assert "File is not an audio file" in str(error)


class TestVideoFileValidation:
    """Test video file validation using ffprobe."""
    
    @patch('subprocess.run')
    def test_validate_video_file_success(self, mock_run, tmp_path):
        """Test successful video file validation."""
        video_file = tmp_path / "test.mkv"
        video_file.touch()
        
        # Mock ffprobe output
        mock_metadata = {
            'format': {
                'format_name': 'matroska,webm',
                'duration': '300.0',
                'size': '50000000',
                'bit_rate': '1000000'
            },
            'streams': [
                {
                    'codec_type': 'video',
                    'codec_name': 'h264',
                    'width': '1920',
                    'height': '1080'
                },
                {
                    'codec_type': 'audio',
                    'codec_name': 'aac',
                    'sample_rate': '48000',
                    'channels': '2'
                }
            ]
        }
        
        mock_run.return_value = MagicMock(
            stdout=json.dumps(mock_metadata),
            stderr='',
            returncode=0
        )
        
        result = FileTypeDetector.validate_video_file(str(video_file))
        
        assert result['file_path'] == str(video_file)
        assert result['format_name'] == 'matroska,webm'
        assert result['duration'] == 300.0
        assert result['audio_codec'] == 'aac'
        assert result['video_codec'] == 'h264'
        assert result['width'] == 1920
        assert result['height'] == 1080
        assert result['audio_streams_count'] == 1
        assert result['video_streams_count'] == 1
    
    @patch('subprocess.run')
    def test_validate_video_file_no_audio_streams(self, mock_run, tmp_path):
        """Test validation failure when video file has no audio streams."""
        video_file = tmp_path / "test.mkv"
        video_file.touch()
        
        # Mock ffprobe output with no audio streams
        mock_metadata = {
            'format': {'format_name': 'matroska'},
            'streams': [
                {
                    'codec_type': 'video',
                    'codec_name': 'h264',
                    'width': '1920',
                    'height': '1080'
                }
            ]
        }
        
        mock_run.return_value = MagicMock(
            stdout=json.dumps(mock_metadata),
            stderr='',
            returncode=0
        )
        
        with pytest.raises(ValidationError) as exc_info:
            FileTypeDetector.validate_video_file(str(video_file))
        
        error = exc_info.value
        assert "No audio streams found in video file" in str(error)
    
    def test_validate_non_video_file(self, tmp_path):
        """Test validation error when file is not video type."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()
        
        with pytest.raises(ValidationError) as exc_info:
            FileTypeDetector.validate_video_file(str(audio_file))
        
        error = exc_info.value
        assert "File is not a video file" in str(error)


class TestSupportedFormats:
    """Test supported formats functionality."""
    
    def test_get_supported_formats(self):
        """Test getting list of supported formats."""
        formats = FileTypeDetector.get_supported_formats()
        
        assert 'audio' in formats
        assert 'video' in formats
        
        # Check that expected formats are present
        assert '.mp3' in formats['audio']
        assert '.wav' in formats['audio']
        assert '.flac' in formats['audio']
        assert '.m4a' in formats['audio']
        
        assert '.mkv' in formats['video']
        assert '.mp4' in formats['video']
        assert '.avi' in formats['video']
        assert '.mov' in formats['video']
        
        # Check that lists are sorted
        assert formats['audio'] == sorted(formats['audio'])
        assert formats['video'] == sorted(formats['video'])


class TestFileTypeDetectorConstants:
    """Test FileTypeDetector class constants."""
    
    def test_audio_extensions_constant(self):
        """Test that AUDIO_EXTENSIONS contains expected formats."""
        expected_audio = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg'}
        assert FileTypeDetector.AUDIO_EXTENSIONS == expected_audio
    
    def test_video_extensions_constant(self):
        """Test that VIDEO_EXTENSIONS contains expected formats."""
        expected_video = {'.mkv', '.mp4', '.avi', '.mov', '.webm'}
        assert FileTypeDetector.VIDEO_EXTENSIONS == expected_video
    
    def test_no_extension_overlap(self):
        """Test that audio and video extensions don't overlap."""
        audio_exts = FileTypeDetector.AUDIO_EXTENSIONS
        video_exts = FileTypeDetector.VIDEO_EXTENSIONS
        
        overlap = audio_exts.intersection(video_exts)
        assert len(overlap) == 0, f"Found overlapping extensions: {overlap}"