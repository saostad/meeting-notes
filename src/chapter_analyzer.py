"""Chapter analysis component for the Meeting Video Chapter Tool.

This module provides functionality to analyze transcripts and identify
logical chapter boundaries using configurable AI providers.
"""

import re
import json
from typing import List, Tuple, Dict, Any

from src.chapter import Chapter, validate_chapter_list
from src.transcript import Transcript
from src.errors import DependencyError, ValidationError, ProcessingError
from src.ai_provider import AIProviderManager
from src.config import Config


class ChapterAnalyzer:
    """Analyzes transcripts to identify chapter boundaries using AI providers.
    
    This class now uses the AIProviderManager to support multiple AI providers
    including local models (Ollama, Transformers) and external APIs (Gemini).
    
    Attributes:
        config: Configuration object with AI provider settings
        ai_provider_manager: Manager for AI provider selection and fallback
    """
    
    def __init__(self, config: Config):
        """Initialize the ChapterAnalyzer with AI provider configuration.
        
        Args:
            config: Configuration object containing AI provider settings
            
        Raises:
            ValidationError: If configuration is invalid
            DependencyError: If no AI providers are available
        """
        self.config = config
        
        # Initialize AI provider manager
        try:
            self.ai_provider_manager = AIProviderManager(config)
        except Exception as e:
            raise DependencyError(
                "Failed to initialize AI provider system",
                {
                    "cause": str(e),
                    "suggestion": "Check your AI provider configuration and dependencies"
                }
            )
        
        # Validate that at least one provider is available
        validation_issues = self.ai_provider_manager.validate_configuration()
        if validation_issues:
            # Check if any provider is actually available
            available_providers = self.ai_provider_manager.get_available_providers()
            if not available_providers:
                raise DependencyError(
                    "No AI providers are available for transcript analysis",
                    {
                        "issues": validation_issues,
                        "suggestion": "Install required dependencies or configure API keys"
                    }
                )
    
    @classmethod
    def create_legacy(cls, api_key: str, model_name: str = "gemini-flash-latest") -> "ChapterAnalyzer":
        """Create ChapterAnalyzer with legacy Gemini-only configuration.
        
        This method provides backward compatibility for existing code that
        directly passes Gemini API credentials.
        
        Args:
            api_key: Google Gemini API key
            model_name: Name of the Gemini model to use
            
        Returns:
            ChapterAnalyzer configured for Gemini-only usage
            
        Raises:
            ValidationError: If API key is missing or invalid
        """
        if not api_key or not api_key.strip():
            raise ValidationError(
                "Gemini API key is required",
                {"operation": "ChapterAnalyzer initialization"}
            )
        
        # Create a minimal config for Gemini-only usage
        config = Config(
            gemini_api_key=api_key,
            gemini_model=model_name,
            ai_provider="gemini",
            enable_fallback=False
        )
        
        return cls(config)
    
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
            DependencyError: If AI provider calls fail
            ProcessingError: If chapter parsing or validation fails
        """
        chapters, notes = self.analyze_with_notes(transcript, save_raw_response, save_notes)
        return chapters
    
    def analyze_with_notes(self, transcript: Transcript, save_raw_response: str = None, save_notes: str = None) -> Tuple[List[Chapter], List[Dict[str, Any]]]:
        """Analyze a transcript and return both chapters and notes.
        
        Args:
            transcript: The transcript to analyze
            save_raw_response: Optional path to save the raw AI response text
            save_notes: Optional path to save extracted actionable instructions/tasks
            
        Returns:
            Tuple of (List of Chapter objects, List of note dictionaries)
            
        Raises:
            ValidationError: If the transcript is empty or invalid
            DependencyError: If AI provider calls fail
            ProcessingError: If chapter parsing or validation fails
        """
        # Validate transcript
        if not transcript.segments:
            raise ValidationError(
                "Cannot analyze empty transcript",
                {"operation": "chapter identification"}
            )
        
        # Use AI provider manager to analyze transcript
        try:
            chapters, notes = self.ai_provider_manager.analyze_transcript(
                transcript, 
                save_raw_response, 
                save_notes
            )
        except Exception as e:
            # Re-raise with enhanced context if needed
            if isinstance(e, (ValidationError, DependencyError, ProcessingError)):
                raise
            else:
                raise ProcessingError(
                    "Unexpected error during transcript analysis",
                    {
                        "operation": "chapter identification",
                        "cause": str(e)
                    }
                )
        
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
        
        return chapters, notes
    
    def get_available_providers(self) -> List[str]:
        """Get list of currently available AI providers.
        
        Returns:
            List of provider names that are available
        """
        return self.ai_provider_manager.get_available_providers()
    
    def validate_configuration(self) -> List[str]:
        """Validate the current AI provider configuration.
        
        Returns:
            List of configuration issues/warnings
        """
        return self.ai_provider_manager.validate_configuration()
