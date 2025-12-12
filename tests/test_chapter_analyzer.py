"""Tests for the ChapterAnalyzer component."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.chapter_analyzer import ChapterAnalyzer
from src.chapter import Chapter
from src.transcript import Transcript, TranscriptSegment
from src.errors import ValidationError, DependencyError, ProcessingError


class TestChapterAnalyzerInit:
    """Test cases for ChapterAnalyzer initialization."""
    
    @patch('src.chapter_analyzer.genai')
    def test_init_with_valid_api_key(self, mock_genai):
        """Test initialization with valid API key."""
        analyzer = ChapterAnalyzer(api_key="test_key", model_name="gemini-flash-latest")
        assert analyzer.api_key == "test_key"
        assert analyzer.model_name == "gemini-flash-latest"
        mock_genai.configure.assert_called_once_with(api_key="test_key")
    
    def test_init_with_empty_api_key_raises_error(self):
        """Test that empty API key raises ValidationError."""
        with pytest.raises(ValidationError, match="Gemini API key is required"):
            ChapterAnalyzer(api_key="")
    
    def test_init_with_whitespace_api_key_raises_error(self):
        """Test that whitespace-only API key raises ValidationError."""
        with pytest.raises(ValidationError, match="Gemini API key is required"):
            ChapterAnalyzer(api_key="   ")
    
    @patch('src.chapter_analyzer.genai')
    def test_init_with_api_failure_raises_dependency_error(self, mock_genai):
        """Test that API initialization failure raises DependencyError."""
        mock_genai.configure.side_effect = Exception("API error")
        
        with pytest.raises(DependencyError, match="Failed to initialize Gemini API"):
            ChapterAnalyzer(api_key="test_key")


class TestFormatPrompt:
    """Test cases for format_prompt method."""
    
    @patch('src.chapter_analyzer.genai')
    def test_format_prompt_includes_transcript_text(self, mock_genai):
        """Test that prompt includes transcript text."""
        analyzer = ChapterAnalyzer(api_key="test_key")
        
        transcript = Transcript(
            segments=[
                TranscriptSegment(start_time=0.0, end_time=10.0, text="Hello world"),
                TranscriptSegment(start_time=10.0, end_time=20.0, text="This is a test")
            ],
            full_text="Hello world This is a test",
            duration=20.0
        )
        
        prompt = analyzer.format_prompt(transcript)
        
        assert "Hello world" in prompt
        assert "This is a test" in prompt
        assert "[00:00]" in prompt
        assert "[00:10]" in prompt
        assert "JSON" in prompt


class TestParseResponse:
    """Test cases for parse_response method."""
    
    @patch('src.chapter_analyzer.genai')
    def test_parse_valid_json_response(self, mock_genai):
        """Test parsing a valid JSON response."""
        analyzer = ChapterAnalyzer(api_key="test_key")
        
        response = '''{
            "chapters": [
                {"timestamp": 0.0, "title": "Introduction"},
                {"timestamp": 60.0, "title": "Main Content"},
                {"timestamp": 120.0, "title": "Conclusion"}
            ],
            "notes": [
                {"timestamp": 60.0, "person_name": "John", "details": "Review the code"}
            ]
        }'''
        
        chapters, notes = analyzer.parse_response(response)
        
        assert len(chapters) == 3
        assert chapters[0].timestamp == 0.0
        assert chapters[0].title == "Introduction"
        assert chapters[1].timestamp == 60.0
        assert chapters[1].title == "Main Content"
        assert isinstance(notes, list)
        assert len(notes) == 1
        assert notes[0]["person_name"] == "John"
    
    @patch('src.chapter_analyzer.genai')
    def test_parse_json_with_markdown_code_block(self, mock_genai):
        """Test parsing JSON wrapped in markdown code block."""
        analyzer = ChapterAnalyzer(api_key="test_key")
        
        response = '''Here are the chapters:
```json
{
    "chapters": [
        {"timestamp": 0.0, "title": "Start"},
        {"timestamp": 30.0, "title": "End"}
    ],
    "notes": []
}
```
'''
        
        chapters, notes = analyzer.parse_response(response)
        
        assert len(chapters) == 2
        assert chapters[0].title == "Start"
        assert isinstance(notes, list)
        assert len(notes) == 0
    
    @patch('src.chapter_analyzer.genai')
    def test_parse_response_without_json_raises_error(self, mock_genai):
        """Test that response without JSON raises ProcessingError."""
        analyzer = ChapterAnalyzer(api_key="test_key")
        
        response = "This is just plain text without any JSON"
        
        with pytest.raises(ProcessingError, match="Could not find JSON object"):
            analyzer.parse_response(response)
    
    @patch('src.chapter_analyzer.genai')
    def test_parse_invalid_json_raises_error(self, mock_genai):
        """Test that invalid JSON raises ProcessingError."""
        analyzer = ChapterAnalyzer(api_key="test_key")
        
        response = '[{"timestamp": 0.0, "title": "Test"}]'  # Valid array but invalid JSON inside
        response = '[{"timestamp": 0.0, "title": "Test",}]'  # Trailing comma - invalid JSON
        
        with pytest.raises(ProcessingError, match="Failed to parse JSON"):
            analyzer.parse_response(response)
    
    @patch('src.chapter_analyzer.genai')
    def test_parse_non_object_json_raises_error(self, mock_genai):
        """Test that non-object JSON raises ProcessingError."""
        analyzer = ChapterAnalyzer(api_key="test_key")
        
        response = '[{"timestamp": 0.0, "title": "Test"}]'
        
        with pytest.raises(ProcessingError, match="Missing 'chapters' field"):
            analyzer.parse_response(response)
    
    @patch('src.chapter_analyzer.genai')
    def test_parse_chapter_missing_timestamp_raises_error(self, mock_genai):
        """Test that chapter missing timestamp raises ProcessingError."""
        analyzer = ChapterAnalyzer(api_key="test_key")
        
        response = '{"chapters": [{"title": "Test"}], "notes": []}'
        
        with pytest.raises(ProcessingError, match="missing 'timestamp' field"):
            analyzer.parse_response(response)
    
    @patch('src.chapter_analyzer.genai')
    def test_parse_chapter_missing_title_raises_error(self, mock_genai):
        """Test that chapter missing title raises ProcessingError."""
        analyzer = ChapterAnalyzer(api_key="test_key")
        
        response = '{"chapters": [{"timestamp": 0.0}], "notes": []}'
        
        with pytest.raises(ProcessingError, match="missing 'title' field"):
            analyzer.parse_response(response)
    
    @patch('src.chapter_analyzer.genai')
    def test_parse_empty_array_raises_error(self, mock_genai):
        """Test that empty chapter array raises ProcessingError."""
        analyzer = ChapterAnalyzer(api_key="test_key")
        
        response = '{"chapters": [], "notes": []}'
        
        with pytest.raises(ProcessingError, match="No chapters found"):
            analyzer.parse_response(response)
    
    @patch('src.chapter_analyzer.genai')
    def test_parse_missing_chapters_field_raises_error(self, mock_genai):
        """Test that missing chapters field raises ProcessingError."""
        analyzer = ChapterAnalyzer(api_key="test_key")
        
        response = '{"notes": "Some notes"}'
        
        with pytest.raises(ProcessingError, match="Missing 'chapters' field"):
            analyzer.parse_response(response)
    
    @patch('src.chapter_analyzer.genai')
    def test_parse_backward_compatible_string_notes(self, mock_genai):
        """Test backward compatibility with string notes format."""
        analyzer = ChapterAnalyzer(api_key="test_key")
        
        response = '''{
            "chapters": [
                {"timestamp": 0.0, "title": "Test"}
            ],
            "notes": "Some old format notes"
        }'''
        
        chapters, notes = analyzer.parse_response(response)
        
        assert len(chapters) == 1
        assert isinstance(notes, list)
        assert len(notes) == 1
        assert notes[0]["details"] == "Some old format notes"


class TestAnalyze:
    """Test cases for analyze method."""
    
    @patch('src.chapter_analyzer.genai')
    def test_analyze_with_empty_transcript_raises_error(self, mock_genai):
        """Test that empty transcript raises ValidationError."""
        analyzer = ChapterAnalyzer(api_key="test_key")
        
        transcript = Transcript(segments=[], full_text="", duration=0.0)
        
        with pytest.raises(ValidationError, match="Cannot analyze empty transcript"):
            analyzer.analyze(transcript)
    
    @patch('src.chapter_analyzer.genai')
    def test_analyze_with_valid_transcript(self, mock_genai):
        """Test successful analysis of a valid transcript."""
        # Mock the model and response
        mock_response = Mock()
        mock_response.text = '''{
            "chapters": [
                {"timestamp": 0.0, "title": "Introduction"},
                {"timestamp": 60.0, "title": "Conclusion"}
            ],
            "notes": [
                {"timestamp": 30.0, "person_name": "Test", "details": "Test task"}
            ]
        }'''
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        analyzer = ChapterAnalyzer(api_key="test_key")
        
        transcript = Transcript(
            segments=[
                TranscriptSegment(start_time=0.0, end_time=30.0, text="Hello"),
                TranscriptSegment(start_time=30.0, end_time=60.0, text="World")
            ],
            full_text="Hello World",
            duration=60.0
        )
        
        chapters = analyzer.analyze(transcript)
        
        assert len(chapters) == 2
        assert chapters[0].timestamp == 0.0
        assert chapters[0].title == "Introduction"
    
    @patch('src.chapter_analyzer.genai')
    def test_analyze_with_empty_api_response_raises_error(self, mock_genai):
        """Test that empty API response raises DependencyError."""
        mock_response = Mock()
        mock_response.text = None
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        analyzer = ChapterAnalyzer(api_key="test_key")
        
        transcript = Transcript(
            segments=[TranscriptSegment(start_time=0.0, end_time=10.0, text="Test")],
            full_text="Test",
            duration=10.0
        )
        
        with pytest.raises(DependencyError, match="Gemini API returned empty response"):
            analyzer.analyze(transcript)
    
    @patch('src.chapter_analyzer.genai')
    def test_analyze_with_rate_limit_error(self, mock_genai):
        """Test that rate limit errors are properly reported."""
        mock_model = Mock()
        mock_model.generate_content.side_effect = Exception("Rate limit exceeded")
        mock_genai.GenerativeModel.return_value = mock_model
        
        analyzer = ChapterAnalyzer(api_key="test_key")
        
        transcript = Transcript(
            segments=[TranscriptSegment(start_time=0.0, end_time=10.0, text="Test")],
            full_text="Test",
            duration=10.0
        )
        
        with pytest.raises(DependencyError, match="rate limit exceeded"):
            analyzer.analyze(transcript)
    
    @patch('src.chapter_analyzer.genai')
    def test_analyze_with_invalid_chapter_structure_raises_error(self, mock_genai):
        """Test that invalid chapter structure raises ProcessingError."""
        # Return chapters with duplicate timestamps (invalid)
        mock_response = Mock()
        mock_response.text = '''{
            "chapters": [
                {"timestamp": 0.0, "title": "First"},
                {"timestamp": 0.0, "title": "Duplicate"}
            ],
            "notes": []
        }'''
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        analyzer = ChapterAnalyzer(api_key="test_key")
        
        transcript = Transcript(
            segments=[TranscriptSegment(start_time=0.0, end_time=10.0, text="Test")],
            full_text="Test",
            duration=10.0
        )
        
        with pytest.raises(ProcessingError, match="invalid structure"):
            analyzer.analyze(transcript)
