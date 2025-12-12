"""Tests for the pipeline orchestration module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.pipeline import PipelineResult, run_pipeline
from src.config import Config
from src.chapter import Chapter
from src.transcript import Transcript, TranscriptSegment
from src.errors import FileSystemError, ProcessingError


class TestPipelineResult:
    """Tests for the PipelineResult data model."""
    
    def test_successful_result(self):
        """Test creating a successful pipeline result."""
        chapters = [
            Chapter(timestamp=0.0, title="Introduction"),
            Chapter(timestamp=60.0, title="Main Topic")
        ]
        
        result = PipelineResult(
            success=True,
            output_mkv="/path/to/output.mkv",
            audio_file="/path/to/audio.mp3",
            transcript_file="/path/to/transcript.json",
            chapters=chapters
        )
        
        assert result.success is True
        assert result.output_mkv == "/path/to/output.mkv"
        assert result.audio_file == "/path/to/audio.mp3"
        assert result.transcript_file == "/path/to/transcript.json"
        assert result.chapters == chapters
        assert result.error is None
        assert result.warnings == []
        assert result.step_failed is None
    
    def test_failed_result(self):
        """Test creating a failed pipeline result."""
        result = PipelineResult(
            success=False,
            error="Audio extraction failed",
            step_failed="audio extraction"
        )
        
        assert result.success is False
        assert result.error == "Audio extraction failed"
        assert result.step_failed == "audio extraction"
        assert result.output_mkv is None
    
    def test_result_with_warnings(self):
        """Test pipeline result with warnings."""
        result = PipelineResult(
            success=True,
            warnings=["Reusing existing audio file", "Reusing existing transcript"]
        )
        
        assert result.success is True
        assert len(result.warnings) == 2
        assert "Reusing existing audio file" in result.warnings


class TestRunPipeline:
    """Tests for the run_pipeline function."""
    
    @patch('src.pipeline.ChapterMerger')
    @patch('src.pipeline.ChapterAnalyzer')
    @patch('src.pipeline.TranscriptionService')
    @patch('src.pipeline.AudioExtractor')
    def test_successful_pipeline_execution(
        self, mock_extractor_class, mock_transcription_class,
        mock_analyzer_class, mock_merger_class, tmp_path
    ):
        """Test successful execution of the complete pipeline."""
        # Create a test MKV file
        mkv_file = tmp_path / "test.mkv"
        mkv_file.write_text("fake mkv content")
        
        # Setup mocks
        mock_extractor = Mock()
        mock_extractor.extract.return_value = str(tmp_path / "test.mp3")
        mock_extractor_class.return_value = mock_extractor
        
        mock_transcript = Transcript(
            segments=[TranscriptSegment(0.0, 10.0, "Test segment")],
            full_text="Test segment",
            duration=10.0
        )
        mock_transcription = Mock()
        mock_transcription.transcribe.return_value = mock_transcript
        mock_transcription_class.return_value = mock_transcription
        
        mock_chapters = [
            Chapter(timestamp=0.0, title="Introduction"),
            Chapter(timestamp=5.0, title="Conclusion")
        ]
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = mock_chapters
        mock_analyzer_class.return_value = mock_analyzer
        
        mock_merger = Mock()
        mock_merger.merge.return_value = str(tmp_path / "test_chaptered.mkv")
        mock_merger_class.return_value = mock_merger
        
        # Create config
        config = Config(
            gemini_api_key="test_key",
            whisper_model="test-whisper",
            gemini_model="test-gemini",
            output_dir=str(tmp_path)
        )
        
        # Run pipeline
        result = run_pipeline(str(mkv_file), config)
        
        # Verify result
        assert result.success is True
        assert result.audio_file == str(tmp_path / "test.mp3")
        assert result.transcript_file is not None
        assert result.chapters == mock_chapters
        assert result.output_mkv == str(tmp_path / "test_chaptered.mkv")
        assert result.error is None
        assert result.step_failed is None
        
        # Verify all steps were called
        mock_extractor.extract.assert_called_once()
        mock_transcription.transcribe.assert_called_once()
        mock_analyzer.analyze.assert_called_once()
        mock_merger.merge.assert_called_once()
    
    @patch('src.pipeline.AudioExtractor')
    def test_pipeline_fails_at_audio_extraction(self, mock_extractor_class, tmp_path):
        """Test pipeline halts when audio extraction fails."""
        mkv_file = tmp_path / "test.mkv"
        mkv_file.write_text("fake mkv content")
        
        # Setup mock to raise error
        mock_extractor = Mock()
        mock_extractor.extract.side_effect = FileSystemError(
            "MKV file does not exist",
            {"file_path": str(mkv_file)}
        )
        mock_extractor_class.return_value = mock_extractor
        
        config = Config(gemini_api_key="test_key")
        
        # Run pipeline
        result = run_pipeline(str(mkv_file), config)
        
        # Verify failure
        assert result.success is False
        assert result.error is not None
        assert result.step_failed == "audio extraction"
        assert result.output_mkv is None
    
    @patch('src.pipeline.TranscriptionService')
    @patch('src.pipeline.AudioExtractor')
    def test_pipeline_fails_at_transcription(
        self, mock_extractor_class, mock_transcription_class, tmp_path
    ):
        """Test pipeline halts when transcription fails."""
        mkv_file = tmp_path / "test.mkv"
        mkv_file.write_text("fake mkv content")
        
        # Setup audio extraction to succeed
        mock_extractor = Mock()
        mock_extractor.extract.return_value = str(tmp_path / "test.mp3")
        mock_extractor_class.return_value = mock_extractor
        
        # Setup transcription to fail
        mock_transcription = Mock()
        mock_transcription.transcribe.side_effect = ProcessingError(
            "No speech detected",
            {"file_path": str(tmp_path / "test.mp3")}
        )
        mock_transcription_class.return_value = mock_transcription
        
        config = Config(gemini_api_key="test_key")
        
        # Run pipeline
        result = run_pipeline(str(mkv_file), config)
        
        # Verify failure at transcription step
        assert result.success is False
        assert result.error is not None
        assert result.step_failed == "transcription"
        assert result.audio_file is not None  # Audio was extracted
        assert result.transcript_file is None  # Transcription failed
    
    @patch('src.pipeline.ChapterMerger')
    @patch('src.pipeline.ChapterAnalyzer')
    @patch('src.pipeline.TranscriptionService')
    @patch('src.pipeline.AudioExtractor')
    def test_skip_existing_audio_file(
        self, mock_extractor_class, mock_transcription_class,
        mock_analyzer_class, mock_merger_class, tmp_path
    ):
        """Test skip_existing option reuses existing audio file."""
        mkv_file = tmp_path / "test.mkv"
        mkv_file.write_text("fake mkv content")
        
        # Create existing audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_text("existing audio")
        
        # Setup mocks
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        
        mock_transcript = Transcript(
            segments=[TranscriptSegment(0.0, 10.0, "Test")],
            full_text="Test",
            duration=10.0
        )
        mock_transcription = Mock()
        mock_transcription.transcribe.return_value = mock_transcript
        mock_transcription_class.return_value = mock_transcription
        
        mock_chapters = [Chapter(timestamp=0.0, title="Test")]
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = mock_chapters
        mock_analyzer_class.return_value = mock_analyzer
        
        mock_merger = Mock()
        mock_merger.merge.return_value = str(tmp_path / "test_chaptered.mkv")
        mock_merger_class.return_value = mock_merger
        
        # Create config with skip_existing enabled
        config = Config(
            gemini_api_key="test_key",
            output_dir=str(tmp_path),
            skip_existing=True
        )
        
        # Run pipeline
        result = run_pipeline(str(mkv_file), config)
        
        # Verify audio extraction was skipped
        assert result.success is True
        assert result.audio_file == str(audio_file)
        mock_extractor.extract.assert_not_called()
        
        # Verify warning was added
        assert len(result.warnings) > 0
        assert any("Reusing existing audio" in w for w in result.warnings)
    
    @patch('src.pipeline.ChapterMerger')
    @patch('src.pipeline.ChapterAnalyzer')
    @patch('src.pipeline.TranscriptionService')
    @patch('src.pipeline.AudioExtractor')
    @patch('src.pipeline.Transcript')
    def test_skip_existing_transcript_file(
        self, mock_transcript_class, mock_extractor_class,
        mock_transcription_class, mock_analyzer_class, mock_merger_class, tmp_path
    ):
        """Test skip_existing option reuses existing transcript file."""
        mkv_file = tmp_path / "test.mkv"
        mkv_file.write_text("fake mkv content")
        
        # Create existing transcript file
        transcript_file = tmp_path / "test_transcript.json"
        transcript_file.write_text('{"segments": [], "full_text": "test", "duration": 10.0}')
        
        # Setup mocks
        mock_extractor = Mock()
        mock_extractor.extract.return_value = str(tmp_path / "test.mp3")
        mock_extractor_class.return_value = mock_extractor
        
        mock_transcript = Transcript(
            segments=[TranscriptSegment(0.0, 10.0, "Test")],
            full_text="Test",
            duration=10.0
        )
        mock_transcript_class.from_file.return_value = mock_transcript
        
        mock_transcription = Mock()
        mock_transcription_class.return_value = mock_transcription
        
        mock_chapters = [Chapter(timestamp=0.0, title="Test")]
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = mock_chapters
        mock_analyzer_class.return_value = mock_analyzer
        
        mock_merger = Mock()
        mock_merger.merge.return_value = str(tmp_path / "test_chaptered.mkv")
        mock_merger_class.return_value = mock_merger
        
        # Create config with skip_existing enabled
        config = Config(
            gemini_api_key="test_key",
            output_dir=str(tmp_path),
            skip_existing=True
        )
        
        # Run pipeline
        result = run_pipeline(str(mkv_file), config)
        
        # Verify transcription was skipped
        assert result.success is True
        assert result.transcript_file == str(transcript_file)
        mock_transcription.transcribe.assert_not_called()
        
        # Verify warning was added
        assert len(result.warnings) > 0
        assert any("Reusing existing transcript" in w for w in result.warnings)
    
    @patch('src.pipeline.ChapterMerger')
    @patch('src.pipeline.ChapterAnalyzer')
    @patch('src.pipeline.TranscriptionService')
    @patch('src.pipeline.AudioExtractor')
    def test_pipeline_reports_all_generated_files(
        self, mock_extractor_class, mock_transcription_class,
        mock_analyzer_class, mock_merger_class, tmp_path
    ):
        """Test that pipeline result includes all generated file paths."""
        mkv_file = tmp_path / "test.mkv"
        mkv_file.write_text("fake mkv content")
        
        # Setup mocks
        audio_path = str(tmp_path / "test.mp3")
        transcript_path = str(tmp_path / "test_transcript.json")
        output_path = str(tmp_path / "test_chaptered.mkv")
        
        mock_extractor = Mock()
        mock_extractor.extract.return_value = audio_path
        mock_extractor_class.return_value = mock_extractor
        
        mock_transcript = Transcript(
            segments=[TranscriptSegment(0.0, 10.0, "Test")],
            full_text="Test",
            duration=10.0
        )
        mock_transcription = Mock()
        mock_transcription.transcribe.return_value = mock_transcript
        mock_transcription_class.return_value = mock_transcription
        
        mock_chapters = [Chapter(timestamp=0.0, title="Test")]
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = mock_chapters
        mock_analyzer_class.return_value = mock_analyzer
        
        mock_merger = Mock()
        mock_merger.merge.return_value = output_path
        mock_merger_class.return_value = mock_merger
        
        config = Config(gemini_api_key="test_key", output_dir=str(tmp_path))
        
        # Run pipeline
        result = run_pipeline(str(mkv_file), config)
        
        # Verify all file paths are reported
        assert result.audio_file == audio_path
        assert result.transcript_file == transcript_path
        assert result.output_mkv == output_path
