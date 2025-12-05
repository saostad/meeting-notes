"""Chapter analysis component for the Meeting Video Chapter Tool.

This module provides functionality to analyze transcripts and identify
logical chapter boundaries using Google's Gemini API.
"""

import re
import json
from typing import List
import google.generativeai as genai

from src.chapter import Chapter, validate_chapter_list
from src.transcript import Transcript
from src.errors import DependencyError, ValidationError, ProcessingError


class ChapterAnalyzer:
    """Analyzes transcripts to identify chapter boundaries using Gemini API.
    
    Attributes:
        api_key: Google Gemini API key
        model_name: Name of the Gemini model to use
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-flash-latest"):
        """Initialize the ChapterAnalyzer.
        
        Args:
            api_key: Google Gemini API key
            model_name: Name of the Gemini model to use (default: gemini-flash-latest)
            
        Raises:
            ValidationError: If API key is missing or invalid
        """
        if not api_key or not api_key.strip():
            raise ValidationError(
                "Gemini API key is required",
                {"operation": "ChapterAnalyzer initialization"}
            )
        
        self.api_key = api_key
        self.model_name = model_name
        
        # Configure the Gemini API
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        except Exception as e:
            raise DependencyError(
                "Failed to initialize Gemini API",
                {
                    "dependency": "google-generativeai",
                    "model": self.model_name,
                    "cause": str(e)
                }
            )
    
    def analyze(self, transcript: Transcript, save_raw_response: str = None, save_notes: str = None) -> List[Chapter]:
        """Analyze a transcript and identify chapter boundaries.
        
        Args:
            transcript: The transcript to analyze
            save_raw_response: Optional path to save the raw AI response text
            save_notes: Optional path to save extracted actionable instructions/tasks
            
        Returns:
            List of Chapter objects with timestamps and titles
            
        Raises:
            ValidationError: If the transcript is empty or invalid
            DependencyError: If the Gemini API call fails
            ProcessingError: If chapter parsing or validation fails
        """
        # Validate transcript
        if not transcript.segments:
            raise ValidationError(
                "Cannot analyze empty transcript",
                {"operation": "chapter identification"}
            )
        
        # Format the prompt
        prompt = self.format_prompt(transcript)
        
        # Call Gemini API
        try:
            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                raise DependencyError(
                    "Gemini API returned empty response",
                    {
                        "dependency": "Gemini API",
                        "model": self.model_name
                    }
                )
            
            response_text = response.text
            
            # Save raw response if requested
            if save_raw_response:
                with open(save_raw_response, 'w', encoding='utf-8') as f:
                    f.write(response_text)
            
        except Exception as e:
            # Check for rate limit errors
            error_str = str(e).lower()
            if "rate limit" in error_str or "quota" in error_str:
                raise DependencyError(
                    "Gemini API rate limit exceeded",
                    {
                        "dependency": "Gemini API",
                        "model": self.model_name,
                        "cause": str(e),
                        "suggestion": "Please wait a few moments and try again"
                    }
                )
            else:
                raise DependencyError(
                    "Gemini API call failed",
                    {
                        "dependency": "Gemini API",
                        "model": self.model_name,
                        "cause": str(e)
                    }
                )
        
        # Parse the response
        chapters, notes = self.parse_response(response_text)
        
        # Save notes if requested (as JSON)
        if save_notes and notes:
            with open(save_notes, 'w', encoding='utf-8') as f:
                json.dump(notes, f, indent=2, ensure_ascii=False)
        
        # Validate chapter structure
        try:
            validate_chapter_list(chapters)
        except ValueError as e:
            raise ProcessingError(
                "Generated chapters have invalid structure",
                {
                    "operation": "chapter validation",
                    "cause": str(e)
                }
            )
        
        return chapters
    
    def format_prompt(self, transcript: Transcript) -> str:
        """Format a transcript into a prompt for Gemini.
        
        Args:
            transcript: The transcript to format
            
        Returns:
            Formatted prompt string
        """
        # Build the transcript text with timestamps
        transcript_text = ""
        for segment in transcript.segments:
            timestamp_str = self._format_timestamp(segment.start_time)
            transcript_text += f"[{timestamp_str}] {segment.text}\n"
        
        prompt = f"""Analyze the following meeting transcript and identify logical chapter boundaries.
For each chapter, provide:
1. The timestamp (in seconds) where the chapter begins
2. A concise, descriptive title for the chapter

The chapters should represent major topic changes or sections in the meeting.
Aim for 3-80 chapters depending on the content length and structure.

Additionally, extract any actionable instructions or tasks mentioned in the meeting. 
"notes" should be a list of actionable instructions and tasks found in the meeting. If none found, leave this as an empty string.
be specific for note details, if possible include order/index of the steps mentioned in meeting to guide the person.
Look for:
- Technical steps that need to be done (e.g., "first do this, then do that")
- Action items assigned to people
- Setup instructions or configuration steps
- Implementation tasks or procedures
- Any sequential instructions or workflows

CRITICAL RULES FOR TIMESTAMPS:
- Extract timestamps directly from the transcript without modification or rounding.
- Violation of these rules will invalidate the entire response.

Return your response in this exact JSON format:
{{
  "chapters": [
    {{"timestamp_original": 0.0,"timestamp_in_minutes": 0.0, "title": "Introduction"}},
    {{"timestamp_original": 120.5,"timestamp_in_minutes": 2.0, "title": "Main Discussion"}},
    {{"timestamp_original": 300.0,"timestamp_in_minutes": 5.0, "title": "Conclusion"}}
  ],
  "notes": [
    {{"timestamp_original": 0.0,"timestamp_in_minutes": 0.0, "person_name": "Saeid", "details": "Switch the test workspace branch back to main after the PR merge."}},
  ]
}}

IMPORTANT: Return ONLY the JSON object, no other text or explanation.

Transcript:
{transcript_text}
"""
        return prompt
    
    def parse_response(self, response: str) -> tuple[List[Chapter], list]:
        """Parse Gemini API response into Chapter objects and notes.
        
        Args:
            response: The response text from Gemini API
            
        Returns:
            Tuple of (List of Chapter objects, notes list)
            
        Raises:
            ProcessingError: If the response cannot be parsed
        """
        # Try to extract JSON from the response
        # Sometimes the model includes markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find a JSON object directly (greedy match to get full object)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ProcessingError(
                    "Could not find JSON object in Gemini response",
                    {
                        "operation": "chapter parsing",
                        "response_preview": response[:200]
                    }
                )
        
        # Parse the JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ProcessingError(
                "Failed to parse JSON from Gemini response",
                {
                    "operation": "chapter parsing",
                    "cause": str(e),
                    "json_preview": json_str[:200]
                }
            )
        
        # Validate that we got an object with chapters
        if not isinstance(data, dict):
            raise ProcessingError(
                "Expected JSON object from Gemini, got different type",
                {
                    "operation": "chapter parsing",
                    "type": type(data).__name__
                }
            )
        
        if "chapters" not in data:
            raise ProcessingError(
                "Missing 'chapters' field in Gemini response",
                {"operation": "chapter parsing"}
            )
        
        chapters_data = data["chapters"]
        notes = data.get("notes", [])
        
        # Ensure notes is a list (handle both array and string for backward compatibility)
        if isinstance(notes, str):
            notes = [] if not notes else [{"details": notes}]
        elif not isinstance(notes, list):
            notes = []
        
        # Validate that chapters is a list
        if not isinstance(chapters_data, list):
            raise ProcessingError(
                "Expected 'chapters' to be an array",
                {
                    "operation": "chapter parsing",
                    "type": type(chapters_data).__name__
                }
            )
        
        # Convert to Chapter objects
        chapters = []
        for i, item in enumerate(chapters_data):
            if not isinstance(item, dict):
                raise ProcessingError(
                    f"Chapter {i} is not a JSON object",
                    {
                        "operation": "chapter parsing",
                        "chapter_index": i
                    }
                )
            
            if "timestamp_original" not in item:
                raise ProcessingError(
                    f"Chapter {i} missing 'timestamp_original' field",
                    {
                        "operation": "chapter parsing",
                        "chapter_index": i
                    }
                )
            
            if "title" not in item:
                raise ProcessingError(
                    f"Chapter {i} missing 'title' field",
                    {
                        "operation": "chapter parsing",
                        "chapter_index": i
                    }
                )
            
            try:
                timestamp_original = float(item["timestamp_original"])
                title = str(item["title"])
                chapter = Chapter(timestamp=timestamp_original, title=title)
                chapters.append(chapter)
            except (ValueError, TypeError) as e:
                raise ProcessingError(
                    f"Invalid data in chapter {i}",
                    {
                        "operation": "chapter parsing",
                        "chapter_index": i,
                        "cause": str(e)
                    }
                )
        
        if not chapters:
            raise ProcessingError(
                "No chapters found in Gemini response",
                {"operation": "chapter parsing"}
            )
        
        return chapters, notes
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as MM:SS timestamp.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
