"""Tests for the centralized prompts module."""

import pytest
from src.prompts import format_transcript_analysis_prompt, _format_timestamp, get_prompt_templates
from src.transcript import Transcript, TranscriptSegment


class TestPrompts:
    """Test cases for the prompts module."""
    
    def test_format_timestamp(self):
        """Test _format_timestamp function."""
        assert _format_timestamp(0) == "00:00"
        assert _format_timestamp(65) == "01:05"
        assert _format_timestamp(3661) == "61:01"
        assert _format_timestamp(125.5) == "02:05"  # Should handle floats
    
    def test_format_transcript_analysis_prompt_basic(self):
        """Test basic prompt formatting."""
        # Create a simple transcript
        segments = [
            TranscriptSegment(start_time=0.0, end_time=10.0, text="Hello everyone"),
            TranscriptSegment(start_time=10.0, end_time=20.0, text="Let's start the meeting")
        ]
        full_text = "Hello everyone Let's start the meeting"
        transcript = Transcript(segments=segments, full_text=full_text, duration=20.0)
        
        # Generate the prompt
        prompt = format_transcript_analysis_prompt(transcript)
        
        # Verify the prompt contains expected elements
        assert "Analyze the following meeting transcript" in prompt
        assert "[00:00] Hello everyone" in prompt
        assert "[00:10] Let's start the meeting" in prompt
        assert "chapters" in prompt
        assert "notes" in prompt
        assert "timestamp_original" in prompt
        assert "JSON" in prompt
    
    def test_format_transcript_analysis_prompt_empty_transcript(self):
        """Test prompt formatting with empty transcript."""
        transcript = Transcript(segments=[], full_text="", duration=0.0)
        
        # Should still generate a valid prompt
        prompt = format_transcript_analysis_prompt(transcript)
        
        assert "Analyze the following meeting transcript" in prompt
        assert "Transcript:" in prompt
    
    def test_format_transcript_analysis_prompt_structure(self):
        """Test that the prompt has the expected structure."""
        segments = [
            TranscriptSegment(start_time=120.5, end_time=130.0, text="This is a test")
        ]
        transcript = Transcript(segments=segments, full_text="This is a test", duration=130.0)
        
        prompt = format_transcript_analysis_prompt(transcript)
        
        # Check for key sections
        assert "CRITICAL RULES FOR TIMESTAMPS:" in prompt
        assert "Return your response in this exact JSON format:" in prompt
        assert "timestamp_original" in prompt
        assert "timestamp_in_minutes" in prompt
        assert "person_name" in prompt
        assert "details" in prompt
        
        # Check that timestamp is formatted correctly
        assert "[02:00] This is a test" in prompt
    
    def test_get_prompt_templates(self):
        """Test get_prompt_templates function."""
        templates = get_prompt_templates()
        
        assert isinstance(templates, dict)
        assert "transcript_analysis" in templates
        
        transcript_template = templates["transcript_analysis"]
        assert "function" in transcript_template
        assert "description" in transcript_template
        assert "supported_providers" in transcript_template
        assert transcript_template["function"] == "format_transcript_analysis_prompt"
        assert "ollama" in transcript_template["supported_providers"]
        assert "gemini" in transcript_template["supported_providers"]