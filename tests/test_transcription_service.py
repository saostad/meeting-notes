"""Unit tests for transcription service."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.transcription_service import TranscriptionService
from src.transcript import Transcript, TranscriptSegment
from src.errors import FileSystemError, DependencyError, ProcessingError


class TestTranscriptionServiceInit:
    """Tests for TranscriptionService initialization."""
    
    def test_init_with_default_model(self):
        """Test initialization with default model name."""
        service = TranscriptionService()
        
        assert service.model_name == "openai/whisper-large-v3-turbo"
        assert service.model is None
        assert service.processor is None
        assert service.pipe is None
    
    def test_init_with_custom_model(self):
        """Test initialization with custom model name."""
        service = TranscriptionService(model_name="openai/whisper-base")
        
        assert service.model_name == "openai/whisper-base"


class TestLoadModel:
    """Tests for load_model method."""
    
    def test_load_model_success(self):
        """Test successful model loading."""
        service = TranscriptionService()
        
        # Mock all the dependencies
        mock_model = MagicMock()
        mock_processor = MagicMock()
        mock_pipeline = MagicMock()
        
        with patch('torch.cuda.is_available', return_value=False):
            with patch('src.transcription_service.AutoModelForSpeechSeq2Seq.from_pretrained', return_value=mock_model):
                with patch('src.transcription_service.AutoProcessor.from_pretrained', return_value=mock_processor):
                    with patch('src.transcription_service.pipeline', return_value=mock_pipeline):
                        service.load_model()
        
        assert service.model is not None
        assert service.processor is not None
        assert service.pipe is not None
    
    def test_load_model_failure(self):
        """Test model loading failure raises DependencyError."""
        service = TranscriptionService()
        
        with patch('torch.cuda.is_available', return_value=False):
            with patch('src.transcription_service.AutoModelForSpeechSeq2Seq.from_pretrained', 
                      side_effect=Exception("Model download failed")):
                with pytest.raises(DependencyError) as exc_info:
                    service.load_model()
                
                assert "Failed to load Whisper model" in str(exc_info.value)
                assert "Whisper" in str(exc_info.value)


class TestTranscribe:
    """Tests for transcribe method."""
    
    def test_transcribe_nonexistent_file(self, tmp_path):
        """Test transcription fails for nonexistent file."""
        service = TranscriptionService()
        
        nonexistent = tmp_path / "nonexistent.mp3"
        
        with pytest.raises(FileSystemError) as exc_info:
            service.transcribe(str(nonexistent))
        
        assert "does not exist" in str(exc_info.value)
    
    def test_transcribe_directory_not_file(self, tmp_path):
        """Test transcription fails when path is a directory."""
        service = TranscriptionService()
        
        directory = tmp_path / "test_dir"
        directory.mkdir()
        
        with pytest.raises(FileSystemError) as exc_info:
            service.transcribe(str(directory))
        
        assert "not a file" in str(exc_info.value)
    
    def test_transcribe_empty_file(self, tmp_path):
        """Test transcription fails for empty file."""
        service = TranscriptionService()
        
        empty_file = tmp_path / "empty.mp3"
        empty_file.write_bytes(b"")
        
        with pytest.raises(ProcessingError) as exc_info:
            service.transcribe(str(empty_file))
        
        assert "empty" in str(exc_info.value).lower()
    
    def test_transcribe_success_with_chunks(self, tmp_path):
        """Test successful transcription with timestamped chunks."""
        service = TranscriptionService()
        
        # Create a dummy audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        # Mock the pipeline
        mock_pipe = MagicMock()
        mock_result = {
            "text": "Hello world, this is a test.",
            "chunks": [
                {"timestamp": (0.0, 5.0), "text": "Hello world,"},
                {"timestamp": (5.0, 10.0), "text": "this is a test."}
            ]
        }
        mock_pipe.return_value = mock_result
        service.pipe = mock_pipe
        
        # Transcribe
        transcript = service.transcribe(str(audio_file))
        
        assert transcript is not None
        assert transcript.full_text == "Hello world, this is a test."
        assert len(transcript.segments) == 2
        assert transcript.segments[0].start_time == 0.0
        assert transcript.segments[0].end_time == 5.0
        assert transcript.segments[0].text == "Hello world,"
        assert transcript.duration == 10.0
    
    def test_transcribe_success_without_chunks(self, tmp_path):
        """Test successful transcription without chunks (fallback)."""
        service = TranscriptionService()
        
        # Create a dummy audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        # Mock the pipeline
        mock_pipe = MagicMock()
        mock_result = {
            "text": "Hello world"
        }
        mock_pipe.return_value = mock_result
        service.pipe = mock_pipe
        
        # Transcribe
        transcript = service.transcribe(str(audio_file))
        
        assert transcript is not None
        assert transcript.full_text == "Hello world"
        assert len(transcript.segments) == 1
        assert transcript.segments[0].text == "Hello world"
    
    def test_transcribe_no_speech_detected(self, tmp_path):
        """Test transcription fails when no speech is detected."""
        service = TranscriptionService()
        
        # Create a dummy audio file
        audio_file = tmp_path / "silent.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        # Mock the pipeline to return empty text
        mock_pipe = MagicMock()
        mock_result = {
            "text": "   ",  # Only whitespace
            "chunks": []
        }
        mock_pipe.return_value = mock_result
        service.pipe = mock_pipe
        
        with pytest.raises(ProcessingError) as exc_info:
            service.transcribe(str(audio_file))
        
        assert "No speech detected" in str(exc_info.value)
    
    def test_transcribe_empty_result(self, tmp_path):
        """Test transcription fails when model returns empty result."""
        service = TranscriptionService()
        
        # Create a dummy audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        # Mock the pipeline to return empty result
        mock_pipe = MagicMock()
        mock_pipe.return_value = {}
        service.pipe = mock_pipe
        
        with pytest.raises(ProcessingError) as exc_info:
            service.transcribe(str(audio_file))
        
        assert "no output" in str(exc_info.value).lower()
    
    def test_transcribe_loads_model_if_not_loaded(self, tmp_path):
        """Test that transcribe loads model if not already loaded."""
        service = TranscriptionService()
        
        # Create a dummy audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        # Mock load_model
        with patch.object(service, 'load_model') as mock_load:
            # Mock the pipeline
            mock_pipe = MagicMock()
            mock_result = {
                "text": "Test",
                "chunks": [{"timestamp": (0.0, 1.0), "text": "Test"}]
            }
            mock_pipe.return_value = mock_result
            
            # Set pipe after load_model is called
            def set_pipe():
                service.pipe = mock_pipe
            
            mock_load.side_effect = set_pipe
            
            # Transcribe
            transcript = service.transcribe(str(audio_file))
            
            # Verify load_model was called
            mock_load.assert_called_once()
    
    def test_transcribe_saves_to_default_path(self, tmp_path):
        """Test that transcribe saves to default path."""
        service = TranscriptionService()
        
        # Create a dummy audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        # Mock the pipeline
        mock_pipe = MagicMock()
        mock_result = {
            "text": "Test",
            "chunks": [{"timestamp": (0.0, 1.0), "text": "Test"}]
        }
        mock_pipe.return_value = mock_result
        service.pipe = mock_pipe
        
        # Transcribe
        transcript = service.transcribe(str(audio_file))
        
        # Check that transcript file was created
        expected_path = tmp_path / "test_transcript.json"
        assert expected_path.exists()
    
    def test_transcribe_saves_to_custom_path(self, tmp_path):
        """Test that transcribe saves to custom path."""
        service = TranscriptionService()
        
        # Create a dummy audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        # Custom output path
        output_path = tmp_path / "custom_transcript.json"
        
        # Mock the pipeline
        mock_pipe = MagicMock()
        mock_result = {
            "text": "Test",
            "chunks": [{"timestamp": (0.0, 1.0), "text": "Test"}]
        }
        mock_pipe.return_value = mock_result
        service.pipe = mock_pipe
        
        # Transcribe
        transcript = service.transcribe(str(audio_file), str(output_path))
        
        # Check that transcript file was created at custom path
        assert output_path.exists()
    
    def test_transcribe_handles_none_timestamps(self, tmp_path):
        """Test transcription handles None values in timestamps."""
        service = TranscriptionService()
        
        # Create a dummy audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        # Mock the pipeline with None timestamps
        mock_pipe = MagicMock()
        mock_result = {
            "text": "Test",
            "chunks": [
                {"timestamp": (None, 5.0), "text": "Test 1"},
                {"timestamp": (5.0, None), "text": "Test 2"}
            ]
        }
        mock_pipe.return_value = mock_result
        service.pipe = mock_pipe
        
        # Transcribe
        transcript = service.transcribe(str(audio_file))
        
        assert transcript is not None
        assert len(transcript.segments) == 2
        assert transcript.segments[0].start_time == 0.0  # None converted to 0.0
        assert transcript.segments[1].end_time == 5.0  # None converted to start_time
    
    def test_transcribe_filters_empty_text_segments(self, tmp_path):
        """Test that segments with empty text are filtered out."""
        service = TranscriptionService()
        
        # Create a dummy audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        # Mock the pipeline with empty text segments
        mock_pipe = MagicMock()
        mock_result = {
            "text": "Hello world",
            "chunks": [
                {"timestamp": (0.0, 5.0), "text": "Hello"},
                {"timestamp": (5.0, 7.0), "text": "   "},  # Whitespace only
                {"timestamp": (7.0, 10.0), "text": "world"}
            ]
        }
        mock_pipe.return_value = mock_result
        service.pipe = mock_pipe
        
        # Transcribe
        transcript = service.transcribe(str(audio_file))
        
        # Only non-empty segments should be included
        assert len(transcript.segments) == 2
        assert transcript.segments[0].text == "Hello"
        assert transcript.segments[1].text == "world"
    
    def test_transcribe_exception_handling(self, tmp_path):
        """Test that unexpected exceptions are wrapped in ProcessingError."""
        service = TranscriptionService()
        
        # Create a dummy audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        # Mock the pipeline to raise an exception
        mock_pipe = MagicMock()
        mock_pipe.side_effect = RuntimeError("Unexpected error")
        service.pipe = mock_pipe
        
        with pytest.raises(ProcessingError) as exc_info:
            service.transcribe(str(audio_file))
        
        assert "Transcription failed" in str(exc_info.value)
        assert "Whisper" in str(exc_info.value)
