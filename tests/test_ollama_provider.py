"""Tests for the Ollama AI Provider.

This module tests the OllamaProvider implementation including
model availability checking, transcript analysis, and response parsing.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from src.providers.ollama_provider import OllamaProvider
from src.transcript import Transcript, TranscriptSegment
from src.chapter import Chapter
from src.errors import ValidationError, DependencyError, ProcessingError


class TestOllamaProvider:
    """Test cases for OllamaProvider class."""
    
    def test_init_with_defaults(self):
        """Test OllamaProvider initialization with default parameters."""
        provider = OllamaProvider()
        
        assert provider.model_name == "phi4"
        assert provider.base_url == "http://localhost:11434"
        assert provider.timeout == 600
        assert provider.model_parameters["temperature"] == 0.1
        assert provider.model_parameters["num_predict"] == 4000
    
    def test_init_with_custom_parameters(self):
        """Test OllamaProvider initialization with custom parameters."""
        provider = OllamaProvider(
            model_name="llama3.2",
            base_url="http://custom:8080",
            timeout=600,
            temperature=0.5,
            max_tokens=2000
        )
        
        assert provider.model_name == "llama3.2"
        assert provider.base_url == "http://custom:8080"
        assert provider.timeout == 600
        assert provider.model_parameters["temperature"] == 0.5
        assert provider.model_parameters["max_tokens"] == 2000
        assert provider.model_parameters["num_predict"] == 4000  # Default preserved
    
    def test_init_validation_empty_model_name(self):
        """Test that empty model name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            OllamaProvider(model_name="")
        
        assert "Ollama model name is required" in str(exc_info.value)
    
    def test_init_validation_empty_base_url(self):
        """Test that empty base URL raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            OllamaProvider(base_url="")
        
        assert "Ollama base URL is required" in str(exc_info.value)
    
    @patch('requests.get')
    def test_is_available_service_running_model_available(self, mock_get):
        """Test is_available when service is running and model is available."""
        # Mock successful response with model available
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "phi4:latest"},
                {"name": "llama3.2:7b"}
            ]
        }
        mock_get.return_value = mock_response
        
        provider = OllamaProvider(model_name="phi4")
        assert provider.is_available() is True
        
        mock_get.assert_called_once_with(
            "http://localhost:11434/api/tags",
            timeout=5
        )
    
    @patch('requests.get')
    def test_is_available_service_running_model_not_available(self, mock_get):
        """Test is_available when service is running but model is not available."""
        # Mock successful response but model not in list
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.2:7b"},
                {"name": "mistral:latest"}
            ]
        }
        mock_get.return_value = mock_response
        
        provider = OllamaProvider(model_name="phi4")
        assert provider.is_available() is False
    
    @patch('requests.get')
    def test_is_available_service_not_running(self, mock_get):
        """Test is_available when Ollama service is not running."""
        # Mock connection error
        mock_get.side_effect = requests.ConnectionError("Connection refused")
        
        provider = OllamaProvider()
        assert provider.is_available() is False
    
    @patch('requests.get')
    def test_is_available_service_error_response(self, mock_get):
        """Test is_available when service returns error response."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        provider = OllamaProvider()
        assert provider.is_available() is False
    
    def test_analyze_transcript_empty_transcript(self):
        """Test analyze_transcript with empty transcript raises ValidationError."""
        provider = OllamaProvider()
        empty_transcript = Transcript(segments=[], full_text="", duration=0.0)
        
        with pytest.raises(ValidationError) as exc_info:
            provider.analyze_transcript(empty_transcript)
        
        assert "Cannot analyze empty transcript" in str(exc_info.value)
    
    @patch.object(OllamaProvider, 'is_available')
    def test_analyze_transcript_service_unavailable(self, mock_is_available):
        """Test analyze_transcript when Ollama service is unavailable."""
        mock_is_available.return_value = False
        
        provider = OllamaProvider()
        transcript = Transcript(
            segments=[TranscriptSegment(0.0, 5.0, "Hello world")],
            full_text="Hello world",
            duration=5.0
        )
        
        with pytest.raises(DependencyError) as exc_info:
            provider.analyze_transcript(transcript)
        
        assert "Ollama service unavailable" in str(exc_info.value)
    
    @patch.object(OllamaProvider, 'is_available')
    @patch('requests.post')
    def test_analyze_transcript_success(self, mock_post, mock_is_available):
        """Test successful transcript analysis."""
        mock_is_available.return_value = True
        
        # Mock successful Ollama API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": json.dumps({
                "chapters": [
                    {"timestamp_original": 0.0, "timestamp_in_minutes": 0.0, "title": "Introduction"},
                    {"timestamp_original": 60.0, "timestamp_in_minutes": 1.0, "title": "Main Discussion"}
                ],
                "notes": [
                    {"timestamp_original": 30.0, "timestamp_in_minutes": 0.5, "person_name": "John", "details": "Follow up on action items"}
                ]
            })
        }
        mock_post.return_value = mock_response
        
        provider = OllamaProvider()
        transcript = Transcript(
            segments=[
                TranscriptSegment(0.0, 30.0, "Welcome to the meeting"),
                TranscriptSegment(30.0, 90.0, "Let's discuss the main topics")
            ],
            full_text="Welcome to the meeting. Let's discuss the main topics.",
            duration=90.0
        )
        
        chapters, notes = provider.analyze_transcript(transcript)
        
        # Verify results
        assert len(chapters) == 2
        assert chapters[0].timestamp == 0.0
        assert chapters[0].title == "Introduction"
        assert chapters[1].timestamp == 60.0
        assert chapters[1].title == "Main Discussion"
        
        assert len(notes) == 1
        assert notes[0]["person_name"] == "John"
        assert notes[0]["details"] == "Follow up on action items"
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["model"] == "phi4"
        assert "Welcome to the meeting" in call_args[1]["json"]["prompt"]
    
    @patch.object(OllamaProvider, 'is_available')
    @patch('requests.post')
    def test_analyze_transcript_api_error(self, mock_post, mock_is_available):
        """Test analyze_transcript when Ollama API call fails."""
        mock_is_available.return_value = True
        mock_post.side_effect = requests.RequestException("API Error")
        
        provider = OllamaProvider()
        transcript = Transcript(
            segments=[TranscriptSegment(0.0, 5.0, "Hello world")],
            full_text="Hello world",
            duration=5.0
        )
        
        with pytest.raises(DependencyError) as exc_info:
            provider.analyze_transcript(transcript)
        
        assert "Ollama API call failed" in str(exc_info.value)
    
    @patch.object(OllamaProvider, 'is_available')
    @patch('requests.post')
    def test_analyze_transcript_invalid_response_format(self, mock_post, mock_is_available):
        """Test analyze_transcript with invalid response format."""
        mock_is_available.return_value = True
        
        # Mock response without 'response' field
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "Invalid request"}
        mock_post.return_value = mock_response
        
        provider = OllamaProvider()
        transcript = Transcript(
            segments=[TranscriptSegment(0.0, 5.0, "Hello world")],
            full_text="Hello world",
            duration=5.0
        )
        
        with pytest.raises(DependencyError) as exc_info:
            provider.analyze_transcript(transcript)
        
        assert "Ollama API call failed" in str(exc_info.value)
    
    def test_parse_response_valid_json(self):
        """Test _parse_response with valid JSON response."""
        provider = OllamaProvider()
        
        response = json.dumps({
            "chapters": [
                {"timestamp_original": 0.0, "timestamp_in_minutes": 0.0, "title": "Start"},
                {"timestamp_original": 120.0, "timestamp_in_minutes": 2.0, "title": "Middle"}
            ],
            "notes": [
                {"details": "Important note"}
            ]
        })
        
        chapters, notes = provider._parse_response(response)
        
        assert len(chapters) == 2
        assert chapters[0].timestamp == 0.0
        assert chapters[0].title == "Start"
        assert len(notes) == 1
        assert notes[0]["details"] == "Important note"
    
    def test_parse_response_json_in_code_block(self):
        """Test _parse_response with JSON wrapped in markdown code block."""
        provider = OllamaProvider()
        
        response = '''Here is the analysis:
        
```json
{
  "chapters": [
    {"timestamp_original": 0.0, "timestamp_in_minutes": 0.0, "title": "Introduction"}
  ],
  "notes": []
}
```

That's the result.'''
        
        chapters, notes = provider._parse_response(response)
        
        assert len(chapters) == 1
        assert chapters[0].title == "Introduction"
        assert len(notes) == 0
    
    def test_parse_response_no_json(self):
        """Test _parse_response with response containing no JSON."""
        provider = OllamaProvider()
        
        response = "This is just plain text with no JSON structure."
        
        with pytest.raises(ProcessingError) as exc_info:
            provider._parse_response(response)
        
        assert "Could not find JSON object in Ollama response" in str(exc_info.value)
    
    def test_parse_response_invalid_json(self):
        """Test _parse_response with malformed JSON."""
        provider = OllamaProvider()
        
        response = '{"chapters": [{"timestamp_original": 0.0, "title": "Test"}]}'  # Valid JSON but missing closing brace for test
        # Let's use actually malformed JSON
        response = '{"chapters": [{"timestamp_original": 0.0, "title": "Test"'  # Missing closing braces
        
        with pytest.raises(ProcessingError) as exc_info:
            provider._parse_response(response)
        
        # The regex will find the partial JSON but it will fail to parse
        error_msg = str(exc_info.value)
        assert ("Could not find JSON object in Ollama response" in error_msg or 
                "Failed to parse JSON from Ollama response" in error_msg)
    
    def test_parse_response_missing_chapters(self):
        """Test _parse_response with JSON missing chapters field."""
        provider = OllamaProvider()
        
        response = json.dumps({"notes": []})
        
        with pytest.raises(ProcessingError) as exc_info:
            provider._parse_response(response)
        
        assert "Missing 'chapters' field in Ollama response" in str(exc_info.value)
    
    def test_parse_response_invalid_chapter_data(self):
        """Test _parse_response with invalid chapter data."""
        provider = OllamaProvider()
        
        response = json.dumps({
            "chapters": [
                {"timestamp_original": "invalid", "title": "Test"}  # Invalid timestamp
            ],
            "notes": []
        })
        
        with pytest.raises(ProcessingError) as exc_info:
            provider._parse_response(response)
        
        assert "Invalid data in chapter 0" in str(exc_info.value)
    
    def test_get_provider_info(self):
        """Test get_provider_info returns correct metadata."""
        provider = OllamaProvider(
            model_name="test-model",
            base_url="http://test:1234",
            temperature=0.7
        )
        
        info = provider.get_provider_info()
        
        assert info["name"] == "Ollama"
        assert info["type"] == "local_api"
        assert info["model"] == "test-model"
        assert info["base_url"] == "http://test:1234"
        assert info["parameters"]["temperature"] == 0.7
        assert "available" in info
    
    def test_format_timestamp(self):
        """Test _format_timestamp method."""
        provider = OllamaProvider()
        
        assert provider._format_timestamp(0) == "00:00"
        assert provider._format_timestamp(65) == "01:05"
        assert provider._format_timestamp(3661) == "61:01"