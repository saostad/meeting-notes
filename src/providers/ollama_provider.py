"""Ollama AI Provider implementation.

This module provides local AI analysis using Ollama for running
large language models locally.
"""

import json
import re
import time
import requests
from typing import List, Tuple, Dict, Any, Optional

from src.ai_provider import BaseAIProvider
from src.chapter import Chapter
from src.transcript import Transcript
from src.errors import ValidationError, DependencyError, ProcessingError


class OllamaProvider(BaseAIProvider):
    """AI Provider implementation using Ollama for local model execution.
    
    This provider connects to a local Ollama service to run language models
    for transcript analysis without sending data to external APIs.
    """
    
    def __init__(self, model_name: str = "phi4", base_url: str = "http://localhost:11434", 
                 timeout: int = 300, **kwargs):
        """Initialize the Ollama provider.
        
        Args:
            model_name: Name of the Ollama model to use (e.g., "phi4", "llama3.2")
            base_url: Base URL for the Ollama service
            timeout: Timeout for API requests in seconds
            **kwargs: Additional model parameters (temperature, max_tokens, etc.)
            
        Raises:
            ValidationError: If configuration is invalid
        """
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.model_parameters = kwargs
        
        # Validate configuration
        if not model_name or not model_name.strip():
            raise ValidationError(
                "Ollama model name is required",
                {"provider": "OllamaProvider"}
            )
        
        if not base_url or not base_url.strip():
            raise ValidationError(
                "Ollama base URL is required",
                {"provider": "OllamaProvider"}
            )
        
        # Set default parameters if not provided
        self.model_parameters.setdefault('temperature', 0.1)
        self.model_parameters.setdefault('num_predict', 4000)
    
    def is_available(self) -> bool:
        """Check if Ollama service is running and the model is available.
        
        Returns:
            True if the provider can be used, False otherwise
        """
        try:
            # Check if Ollama service is running
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            
            if response.status_code != 200:
                return False
            
            # Check if our specific model is available
            models_data = response.json()
            available_models = [model['name'] for model in models_data.get('models', [])]
            
            # Check for exact match or partial match (model might have tags)
            model_available = any(
                self.model_name in model_name or model_name.startswith(self.model_name)
                for model_name in available_models
            )
            
            return model_available
            
        except (requests.RequestException, json.JSONDecodeError, KeyError):
            return False
    
    def analyze_transcript(self, transcript: Transcript, save_raw_response: str = None, save_notes: str = None) -> Tuple[List[Chapter], List[Dict[str, Any]]]:
        """Analyze transcript using Ollama model.
        
        Args:
            transcript: The transcript to analyze
            save_raw_response: Optional path to save raw AI response
            save_notes: Optional path to save extracted notes
            
        Returns:
            Tuple of (chapters list, notes list)
            
        Raises:
            ValidationError: If transcript is invalid
            DependencyError: If Ollama service is unavailable
            ProcessingError: If analysis or parsing fails
        """
        if not transcript.segments:
            raise ValidationError(
                "Cannot analyze empty transcript",
                {"provider": "OllamaProvider"}
            )
        
        if not self.is_available():
            raise DependencyError(
                f"Ollama service unavailable or model '{self.model_name}' not found",
                {
                    "provider": "OllamaProvider",
                    "model": self.model_name,
                    "base_url": self.base_url,
                    "suggestion": f"Ensure Ollama is running and model '{self.model_name}' is installed"
                }
            )
        
        # Format the prompt
        prompt = self._format_prompt(transcript)
        
        # Call Ollama API
        try:
            response_text = self._call_ollama_api(prompt)
        except Exception as e:
            raise DependencyError(
                "Ollama API call failed",
                {
                    "provider": "OllamaProvider",
                    "model": self.model_name,
                    "cause": str(e)
                }
            )
        
        # Save raw response if requested
        if save_raw_response and response_text:
            try:
                with open(save_raw_response, 'w', encoding='utf-8') as f:
                    f.write(response_text)
            except Exception as e:
                # Don't fail the analysis if saving fails, just warn
                print(f"Warning: Failed to save raw response: {e}")
        
        # Parse the response
        try:
            chapters, notes = self._parse_response(response_text)
        except Exception as e:
            raise ProcessingError(
                "Failed to parse Ollama response",
                {
                    "provider": "OllamaProvider",
                    "model": self.model_name,
                    "cause": str(e),
                    "response_preview": response_text[:200] if response_text else "No response"
                }
            )
        
        # Save notes if requested
        if save_notes and notes:
            try:
                with open(save_notes, 'w', encoding='utf-8') as f:
                    json.dump(notes, f, indent=2, ensure_ascii=False)
            except Exception as e:
                # Don't fail the analysis if saving fails, just warn
                print(f"Warning: Failed to save notes: {e}")
        
        return chapters, notes
    
    def _call_ollama_api(self, prompt: str) -> str:
        """Make API call to Ollama service.
        
        Args:
            prompt: The formatted prompt to send
            
        Returns:
            Response text from the model
            
        Raises:
            requests.RequestException: If API call fails
        """
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",  # Force JSON format
            "options": self.model_parameters
        }
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout
        )
        
        response.raise_for_status()
        
        result = response.json()
        
        if 'response' not in result:
            raise ProcessingError(
                "Invalid response format from Ollama",
                {"expected_field": "response", "received": list(result.keys())}
            )
        
        return result['response']
    
    def _format_prompt(self, transcript: Transcript) -> str:
        """Format a transcript into a prompt for the Ollama model.
        
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
        
        json_format = """{
  "chapters": [
    {"timestamp_original": 0.0,"timestamp_in_minutes": 0.0, "title": "Introduction"},
    {"timestamp_original": 120.5,"timestamp_in_minutes": 2.0, "title": "Main Discussion"},
    {"timestamp_original": 300.0,"timestamp_in_minutes": 5.0, "title": "Conclusion"}
  ],
  "notes": [
    {"timestamp_original": 0.0,"timestamp_in_minutes": 0.0, "person_name": "Saeid", "details": "Switch the test workspace branch back to main after the PR merge."},
  ]
}"""
        
        prompt = f"""Analyze the following meeting transcript and identify logical chapter boundaries.
For each chapter, provide:
1. The timestamp (in seconds) where the chapter begins
2. A concise, descriptive title for the chapter

The chapters should represent major topic changes or sections in the meeting.
Aim for 3-80 chapters depending on the content length and structure.

Additionally, extract any actionable instructions or tasks mentioned in the meeting. 
"notes" should be a list of actionable instructions and tasks found in the meeting. If none found, leave this as an empty array.
Be specific for note details, if possible include order/index of the steps mentioned in meeting to guide the person.
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
{json_format}

CRITICAL: You MUST return ONLY valid JSON in the exact format specified above. Do not include any explanations, markdown formatting, or additional text. Start your response with {{ and end with }}.

Transcript:
{transcript_text}
"""
        return prompt
    
    def _parse_response(self, response: str) -> Tuple[List[Chapter], List[Dict[str, Any]]]:
        """Parse Ollama model response into Chapter objects and notes.
        
        Args:
            response: The response text from Ollama model
            
        Returns:
            Tuple of (List of Chapter objects, notes list)
            
        Raises:
            ProcessingError: If the response cannot be parsed
        """
        # Try to extract JSON from the response
        # Sometimes the model includes markdown code blocks or extra text
        json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find a JSON object directly using greedy match
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ProcessingError(
                    "Could not find JSON object in Ollama response",
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
                "Failed to parse JSON from Ollama response",
                {
                    "operation": "chapter parsing",
                    "cause": str(e),
                    "json_preview": json_str[:200]
                }
            )
        
        # Validate that we got an object with chapters
        if not isinstance(data, dict):
            raise ProcessingError(
                "Expected JSON object from Ollama, got different type",
                {
                    "operation": "chapter parsing",
                    "type": type(data).__name__
                }
            )
        
        if "chapters" not in data:
            raise ProcessingError(
                "Missing 'chapters' field in Ollama response",
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
                "No chapters found in Ollama response",
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
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Return provider information for logging and debugging.
        
        Returns:
            Dictionary containing provider metadata
        """
        return {
            "name": "Ollama",
            "type": "local_api",
            "model": self.model_name,
            "base_url": self.base_url,
            "parameters": self.model_parameters,
            "available": self.is_available()
        }