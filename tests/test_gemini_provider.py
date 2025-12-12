"""Unit tests for Gemini AI provider."""

import pytest
from unittest.mock import Mock, patch
from src.providers.gemini_provider import GeminiProvider
from src.chapter import Chapter
from src.transcript import Transcript, TranscriptSegment
from src.errors import ValidationError, DependencyError


class TestGeminiProvider:
    """Tests for GeminiProvider."""
    
    def create_test_transcript(self):
        """Create a test transcript."""
        segments = [
            TranscriptSegment(start_time=0.0, end_time=30.0, text="Hello everyone"),
            TranscriptSegment(start_time=30.0, end_time=60.0, text="Let's discuss the project")
        ]
        full_text = "Hello everyone Let's discuss the project"
        duration = 60.0
        return Transcript(segments=segments, full_text=full_text, duration=duration)
    
    def test_initialization_success(self):
        """Test successful GeminiProvider initialization."""
        with patch('src.providers.gemini_provider.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            provider = GeminiProvider("test_api_key", "test_model")
            
            assert provider.api_key == "test_api_key"
            assert provider.model_name == "test_model"
            assert provider.model is not None
            mock_genai.configure.assert_called_once_with(api_key="test_api_key")
            mock_genai.GenerativeModel.assert_called_once_with("test_model")
    
    def test_initialization_missing_api_key(self):
        """Test GeminiProvider initialization with missing API key."""
        with pytest.raises(ValidationError) as exc_info:
            GeminiProvider("", "test_model")
        
        assert "Gemini API key is required" in str(exc_info.value)
    
    def test_initialization_whitespace_api_key(self):
        """Test GeminiProvider initialization with whitespace API key."""
        with pytest.raises(ValidationError) as exc_info:
            GeminiProvider("   ", "test_model")
        
        assert "Gemini API key is required" in str(exc_info.value)
    
    def test_initialization_analyzer_failure(self):
        """Test GeminiProvider initialization when Gemini API fails."""
        with patch('src.providers.gemini_provider.genai') as mock_genai:
            mock_genai.configure.side_effect = Exception("API init failed")
            
            with pytest.raises(DependencyError) as exc_info:
                GeminiProvider("test_api_key", "test_model")
            
            assert "Failed to initialize Gemini provider" in str(exc_info.value)
    
    def test_is_available_success(self):
        """Test is_available returns True for valid provider."""
        with patch('src.providers.gemini_provider.genai') as mock_genai:
            mock_genai.GenerativeModel.return_value = Mock()
            
            provider = GeminiProvider("valid_api_key", "test_model")
            
            assert provider.is_available() is True
    
    def test_is_available_no_model(self):
        """Test is_available returns False when model is None."""
        provider = GeminiProvider.__new__(GeminiProvider)  # Create without __init__
        provider.api_key = "test_key"
        provider.model_name = "test_model"
        provider.model = None
        
        assert provider.is_available() is False
    
    def test_is_available_empty_api_key(self):
        """Test is_available returns False for empty API key."""
        provider = GeminiProvider.__new__(GeminiProvider)  # Create without __init__
        provider.api_key = ""
        provider.model_name = "test_model"
        provider.model = Mock()
        
        assert provider.is_available() == False
    
    def test_is_available_placeholder_api_key(self):
        """Test is_available returns False for placeholder API key."""
        provider = GeminiProvider.__new__(GeminiProvider)  # Create without __init__
        provider.api_key = "your_api_key_here"
        provider.model_name = "test_model"
        provider.model = Mock()
        
        assert provider.is_available() is False
    
    def test_analyze_transcript_success(self):
        """Test successful transcript analysis."""
        with patch('src.providers.gemini_provider.genai') as mock_genai:
            # Mock the Gemini API
            mock_model = Mock()
            mock_response = Mock()
            mock_response.text = '''{
                "chapters": [
                    {"timestamp_original": 0.0, "timestamp_in_minutes": 0.0, "title": "Introduction"},
                    {"timestamp_original": 60.0, "timestamp_in_minutes": 1.0, "title": "Discussion"}
                ],
                "notes": [{"details": "Test note"}]
            }'''
            mock_model.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model
            
            provider = GeminiProvider("test_api_key", "test_model")
            transcript = self.create_test_transcript()
            
            chapters, notes = provider.analyze_transcript(transcript)
            
            assert len(chapters) == 2
            assert chapters[0].title == "Introduction"
            assert chapters[1].title == "Discussion"
            assert len(notes) == 1
            assert notes[0]["details"] == "Test note"
            
            mock_model.generate_content.assert_called_once()
    
    def test_analyze_transcript_no_model(self):
        """Test transcript analysis when model is not initialized."""
        provider = GeminiProvider.__new__(GeminiProvider)  # Create without __init__
        provider.api_key = "test_key"
        provider.model_name = "test_model"
        provider.model = None
        
        transcript = self.create_test_transcript()
        
        with pytest.raises(DependencyError) as exc_info:
            provider.analyze_transcript(transcript)
        
        assert "Gemini provider not properly initialized" in str(exc_info.value)
    
    def test_analyze_transcript_api_failure(self):
        """Test transcript analysis when Gemini API fails."""
        with patch('src.providers.gemini_provider.genai') as mock_genai:
            # Mock the API to fail
            mock_model = Mock()
            mock_model.generate_content.side_effect = Exception("API call failed")
            mock_genai.GenerativeModel.return_value = mock_model
            
            provider = GeminiProvider("test_api_key", "test_model")
            transcript = self.create_test_transcript()
            
            with pytest.raises(DependencyError) as exc_info:
                provider.analyze_transcript(transcript)
            
            assert "Gemini API call failed" in str(exc_info.value)
    
    def test_get_provider_info(self):
        """Test get_provider_info returns correct information."""
        with patch('src.providers.gemini_provider.genai') as mock_genai:
            mock_genai.GenerativeModel.return_value = Mock()
            
            provider = GeminiProvider("test_api_key", "custom_model")
            info = provider.get_provider_info()
            
            assert info["name"] == "Gemini"
            assert info["type"] == "external_api"
            assert info["model"] == "custom_model"
            assert info["api_key_configured"] is True
            assert info["available"] is True
    
    def test_get_provider_info_no_api_key(self):
        """Test get_provider_info with no API key."""
        provider = GeminiProvider.__new__(GeminiProvider)  # Create without __init__
        provider.api_key = ""
        provider.model_name = "test_model"
        provider.model = None
        
        info = provider.get_provider_info()
        
        assert info["name"] == "Gemini"
        assert info["type"] == "external_api"
        assert info["model"] == "test_model"
        assert info["api_key_configured"] is False
        assert info["available"] is False