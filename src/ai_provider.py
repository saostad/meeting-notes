"""AI Provider system for the Meeting Video Chapter Tool.

This module provides the foundation for supporting multiple AI providers
including local models (Ollama) and external APIs (Gemini).
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field

from src.chapter import Chapter
from src.transcript import Transcript


@dataclass
class ProviderConfig:
    """Configuration structure for AI providers.
    
    Attributes:
        provider_type: Type of provider ("ollama", "gemini")
        model_name: Name of the model to use
        parameters: Provider-specific parameters
        timeout: Timeout in seconds for operations
        max_retries: Maximum number of retry attempts
    """
    provider_type: str
    model_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 600
    max_retries: int = 2


@dataclass
class AnalysisResult:
    """Standardized result format from AI providers.
    
    Attributes:
        chapters: List of identified chapters
        notes: List of extracted actionable notes
        provider_used: Name of the provider that generated the result
        processing_time: Time taken for analysis in seconds
        confidence_score: Optional confidence score for the analysis
        warnings: List of warnings encountered during processing
    """
    chapters: List[Chapter]
    notes: List[Dict[str, Any]]
    provider_used: str
    processing_time: float
    confidence_score: Optional[float] = None
    warnings: List[str] = field(default_factory=list)


class BaseAIProvider(ABC):
    """Abstract base class for AI providers.
    
    All AI providers must implement this interface to ensure consistent
    behavior across different AI backends.
    """
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and functional.
        
        Returns:
            True if the provider can be used, False otherwise
        """
        pass
    
    @abstractmethod
    def analyze_transcript(self, transcript: Transcript, save_raw_response: str = None, save_notes: str = None) -> Tuple[List[Chapter], List[Dict[str, Any]]]:
        """Analyze transcript and return chapters and notes.
        
        Args:
            transcript: The transcript to analyze
            save_raw_response: Optional path to save raw AI response
            save_notes: Optional path to save extracted notes
            
        Returns:
            Tuple of (chapters list, notes list)
            
        Raises:
            Various exceptions depending on the provider implementation
        """
        pass
    
    @abstractmethod
    def review_analysis(self, original_result: Dict[str, Any], transcript: Transcript, save_raw_response: str = None) -> Tuple[List[Chapter], List[Dict[str, Any]]]:
        """Review and improve an existing analysis result.
        
        Args:
            original_result: The original analysis result with chapters and notes
            transcript: The original transcript for reference
            save_raw_response: Optional path to save raw AI response
            
        Returns:
            Tuple of (improved chapters list, improved notes list)
            
        Raises:
            Various exceptions depending on the provider implementation
        """
        pass
    
    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """Return provider information for logging and debugging.
        
        Returns:
            Dictionary containing provider metadata
        """
        pass


class AIProviderManager:
    """Manages AI provider selection and execution with optional fallback.
    
    This class orchestrates the selection of AI providers based on configuration
    and handles fallback logic when the primary provider fails.
    """
    
    def __init__(self, config):
        """Initialize the AIProviderManager.
        
        Args:
            config: Configuration object containing AI provider settings
        """
        from src.config import Config
        
        self.config: Config = config
        self.primary_provider: Optional[BaseAIProvider] = None
        self.fallback_provider: Optional[BaseAIProvider] = None
        
        # Initialize providers based on configuration
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """Initialize primary and fallback providers based on configuration."""
        # Create primary provider
        if self.config.ai_provider == "local":
            self.primary_provider = self._create_local_provider()
        elif self.config.ai_provider == "gemini":
            self.primary_provider = self._create_gemini_provider()
        else:
            # Default to local if invalid provider specified
            self.primary_provider = self._create_local_provider()
        
        # Create fallback provider if enabled
        if self.config.enable_fallback:
            if self.config.ai_provider != "gemini":
                # Use Gemini as fallback if primary is not Gemini
                self.fallback_provider = self._create_gemini_provider()
    
    def _create_local_provider(self) -> Optional[BaseAIProvider]:
        """Create a local AI provider based on available frameworks.
        
        Returns:
            Local provider instance or None if not available
        """
        framework = self.config.local_model_framework
        
        # Try frameworks in order based on configuration
        if framework == "ollama" or framework == "auto":
            ollama_provider = self._try_create_ollama_provider()
            if ollama_provider:
                return ollama_provider
        
        # No local providers available
        return None
    
    def _try_create_ollama_provider(self) -> Optional[BaseAIProvider]:
        """Try to create an Ollama provider.
        
        Returns:
            Ollama provider instance or None if not available
        """
        try:
            from src.providers.ollama_provider import OllamaProvider
            
            # Get model parameters from config
            model_params = self.config.model_parameters or {}
            
            print(f"🔧 Attempting to create Ollama provider:")
            print(f"   Model: {self.config.local_model_name}")
            print(f"   Base URL: {self.config.ollama_base_url}")
            print(f"   Timeout: {self.config.analysis_timeout}s")
            
            provider = OllamaProvider(
                model_name=self.config.local_model_name,
                base_url=self.config.ollama_base_url,
                timeout=self.config.analysis_timeout,
                **model_params
            )
            
            # Test if provider is available
            print(f"🔍 Testing Ollama provider availability...")
            if provider.is_available():
                print(f"✅ Ollama provider is available")
                return provider
            else:
                print(f"❌ Ollama provider is not available")
                return None
                
        except Exception as e:
            # Provider creation failed
            print(f"❌ Failed to create Ollama provider: {type(e).__name__}: {e}")
            return None
    

    
    def _create_gemini_provider(self) -> Optional[BaseAIProvider]:
        """Create a Gemini provider instance.
        
        Returns:
            Gemini provider instance or None if not available
        """
        # Import here to avoid circular imports
        from src.providers.gemini_provider import GeminiProvider
        
        try:
            return GeminiProvider(
                api_key=self.config.gemini_api_key,
                model_name=self.config.gemini_model
            )
        except Exception:
            # Provider creation failed
            return None
    
    def analyze_transcript(self, transcript: Transcript, save_raw_response: str = None, save_notes: str = None) -> Tuple[List[Chapter], List[Dict[str, Any]]]:
        """Analyze transcript using available providers with fallback logic.
        
        Args:
            transcript: The transcript to analyze
            save_raw_response: Optional path to save raw AI response
            save_notes: Optional path to save extracted notes
            
        Returns:
            Tuple of (chapters list, notes list)
            
        Raises:
            RuntimeError: If no providers are available or all providers fail
        """
        import time
        import json
        from src.errors import ProcessingError, DependencyError, ValidationError
        
        # Track which provider was used for logging
        provider_used = None
        processing_start = time.time()
        primary_error = None
        fallback_error = None
        
        # Validate transcript before processing
        if not transcript or not transcript.segments:
            raise ValidationError(
                "Cannot analyze empty or invalid transcript",
                {"operation": "transcript analysis"}
            )
        
        # Report provider status at start
        self._report_provider_status()
        
        # Perform initial analysis
        chapters, notes = self._perform_analysis(transcript, save_raw_response, save_notes)
        
        # Perform review passes if enabled
        if self.config.enable_review and self.config.review_passes > 1:
            chapters, notes = self._perform_review_passes(
                chapters, notes, transcript, save_raw_response, save_notes
            )
        
        return chapters, notes
    
    def _perform_analysis(self, transcript: Transcript, save_raw_response: str = None, save_notes: str = None) -> Tuple[List[Chapter], List[Dict[str, Any]]]:
        """Perform the initial transcript analysis.
        
        Args:
            transcript: The transcript to analyze
            save_raw_response: Optional path to save raw AI response
            save_notes: Optional path to save extracted notes
            
        Returns:
            Tuple of (chapters list, notes list)
        """
        import time
        import json
        from src.errors import ProcessingError, DependencyError, ValidationError
        
        processing_start = time.time()
        primary_error = None
        
        # Try primary provider first
        if self.primary_provider:
            primary_info = self.primary_provider.get_provider_info()
            
            if self.primary_provider.is_available():
                try:
                    print(f"🔄 Starting analysis with primary provider: {primary_info['name']}")
                    if primary_info.get('type') == 'external_api':
                        print("⚠️  Note: Using external API - data will be sent to external services")
                    
                    chapters, notes = self.primary_provider.analyze_transcript(transcript, save_raw_response, save_notes)
                    
                    # Save outputs if requested
                    if save_notes and notes:
                        with open(save_notes, 'w', encoding='utf-8') as f:
                            json.dump(notes, f, indent=2, ensure_ascii=False)
                    
                    processing_time = time.time() - processing_start
                    print(f"✅ Analysis completed successfully using {primary_info['name']} in {processing_time:.2f}s")
                    
                    return chapters, notes
                    
                except Exception as e:
                    primary_error = e
                    error_type = type(e).__name__
                    print(f"❌ Primary provider ({primary_info['name']}) failed: {error_type}: {e}")
                    
                    if not self.config.enable_fallback:
                        # No fallback enabled, re-raise with enhanced context
                        raise ProcessingError(
                            f"Primary AI provider failed and fallback is disabled",
                            {
                                "provider": primary_info['name'],
                                "error_type": error_type,
                                "cause": str(e),
                                "suggestion": "Enable fallback in configuration or fix the primary provider issue"
                            }
                        )
            else:
                primary_error = "Provider not available"
                print(f"⚠️  Primary provider ({primary_info['name']}) is not available")
                
                if not self.config.enable_fallback:
                    raise DependencyError(
                        f"Primary AI provider is not available and fallback is disabled",
                        {
                            "provider": primary_info['name'],
                            "provider_info": primary_info,
                            "suggestion": "Enable fallback in configuration or ensure primary provider dependencies are installed"
                        }
                    )
        
        # Try fallback provider if available and enabled
        if self.config.enable_fallback and self.fallback_provider:
            fallback_info = self.fallback_provider.get_provider_info()
            
            if self.fallback_provider.is_available():
                try:
                    # Determine fallback reason for user notification
                    if primary_error:
                        if isinstance(primary_error, Exception):
                            reason = f"Primary provider error: {type(primary_error).__name__}"
                        else:
                            reason = f"Primary provider: {primary_error}"
                    else:
                        reason = "Primary provider unavailable"
                    
                    print(f"🔄 Falling back to: {fallback_info['name']}")
                    print(f"📋 Fallback reason: {reason}")
                    
                    if fallback_info.get('type') == 'external_api':
                        print("⚠️  Note: Using external API fallback - data will be sent to external services")
                    
                    chapters, notes = self.fallback_provider.analyze_transcript(transcript, save_raw_response, save_notes)
                    
                    # Save outputs if requested
                    if save_notes and notes:
                        with open(save_notes, 'w', encoding='utf-8') as f:
                            json.dump(notes, f, indent=2, ensure_ascii=False)
                    
                    processing_time = time.time() - processing_start
                    print(f"✅ Analysis completed using fallback provider {fallback_info['name']} in {processing_time:.2f}s")
                    
                    return chapters, notes
                    
                except Exception as e:
                    fallback_error = e
                    error_type = type(e).__name__
                    print(f"❌ Fallback provider ({fallback_info['name']}) also failed: {error_type}: {e}")
                    
                    # Both providers failed
                    raise ProcessingError(
                        f"Both primary and fallback providers failed",
                        {
                            "primary_provider": self.primary_provider.get_provider_info()['name'] if self.primary_provider else "None",
                            "primary_error": str(primary_error) if primary_error else "Not available",
                            "fallback_provider": fallback_info['name'],
                            "fallback_error": str(e),
                            "suggestion": "Check your configuration and network connectivity, or try again later"
                        }
                    )
            else:
                fallback_error = "Fallback provider not available"
                print(f"❌ Fallback provider ({fallback_info['name']}) is also not available")
        
        # No providers available or fallback disabled
        if not self.config.enable_fallback:
            error_msg = "Primary AI provider failed and fallback is disabled"
            context = {
                "primary_provider": self.primary_provider.get_provider_info()['name'] if self.primary_provider else "None",
                "primary_error": str(primary_error) if primary_error else "Not configured",
                "fallback_enabled": False,
                "suggestion": "Enable fallback in configuration (set ENABLE_FALLBACK=true) or fix the primary provider"
            }
        else:
            error_msg = "No AI providers are available for transcript analysis"
            context = {
                "primary_provider": self.primary_provider.get_provider_info()['name'] if self.primary_provider else "None",
                "primary_available": self.primary_provider.is_available() if self.primary_provider else False,
                "primary_error": str(primary_error) if primary_error else "Not configured",
                "fallback_provider": self.fallback_provider.get_provider_info()['name'] if self.fallback_provider else "None",
                "fallback_available": self.fallback_provider.is_available() if self.fallback_provider else False,
                "fallback_error": str(fallback_error) if fallback_error else "Not configured",
                "suggestion": "Check your configuration and ensure required dependencies are installed"
            }
        
        raise DependencyError(error_msg, context)
    
    def _perform_review_passes(self, initial_chapters: List[Chapter], initial_notes: List[Dict[str, Any]], 
                              transcript: Transcript, save_raw_response: str = None, save_notes: str = None) -> Tuple[List[Chapter], List[Dict[str, Any]]]:
        """Perform iterative review passes to improve analysis quality.
        
        Args:
            initial_chapters: Initial chapters from first analysis
            initial_notes: Initial notes from first analysis
            transcript: The original transcript
            save_raw_response: Optional path to save raw AI response
            save_notes: Optional path to save extracted notes
            
        Returns:
            Tuple of (improved chapters list, improved notes list)
        """
        import time
        import json
        from src.chapter import Chapter
        
        current_chapters = initial_chapters
        current_notes = initial_notes
        
        print(f"🔄 Starting {self.config.review_passes - 1} review pass(es) to improve analysis quality...")
        
        for pass_num in range(2, self.config.review_passes + 1):
            print(f"📝 Review pass {pass_num}/{self.config.review_passes}")
            
            # Create the current result structure for review
            current_result = {
                "chapters": [
                    {
                        "timestamp_original": chapter.timestamp,
                        "timestamp_in_minutes": chapter.timestamp / 60.0,
                        "title": chapter.title
                    }
                    for chapter in current_chapters
                ],
                "notes": current_notes
            }
            
            # Perform review with the best available provider
            provider_to_use = None
            if self.primary_provider and self.primary_provider.is_available():
                provider_to_use = self.primary_provider
            elif self.fallback_provider and self.fallback_provider.is_available():
                provider_to_use = self.fallback_provider
            
            if not provider_to_use:
                print(f"⚠️  No providers available for review pass {pass_num}, using current results")
                break
            
            try:
                review_start = time.time()
                provider_info = provider_to_use.get_provider_info()
                
                # Generate review-specific save paths
                review_save_path = None
                if save_raw_response:
                    base_path = save_raw_response.rsplit('.', 1)[0] if '.' in save_raw_response else save_raw_response
                    review_save_path = f"{base_path}_review_pass_{pass_num}.txt"
                
                reviewed_chapters, reviewed_notes = provider_to_use.review_analysis(
                    current_result, transcript, review_save_path
                )
                
                review_time = time.time() - review_start
                
                # Update current results
                current_chapters = reviewed_chapters
                current_notes = reviewed_notes
                
                print(f"✅ Review pass {pass_num} completed using {provider_info['name']} in {review_time:.2f}s")
                print(f"   Chapters: {len(current_chapters)}, Notes: {len(current_notes)}")
                
            except Exception as e:
                print(f"⚠️  Review pass {pass_num} failed: {type(e).__name__}: {e}")
                print(f"   Continuing with results from previous pass")
                break
        
        # Save final reviewed results if requested
        if save_notes and current_notes:
            with open(save_notes, 'w', encoding='utf-8') as f:
                json.dump(current_notes, f, indent=2, ensure_ascii=False)
        
        return current_chapters, current_notes
    
    def get_available_providers(self) -> List[str]:
        """Get list of currently available providers.
        
        Returns:
            List of provider names that are available
        """
        available = []
        
        if self.primary_provider and self.primary_provider.is_available():
            available.append(self.primary_provider.get_provider_info()['name'])
        
        if self.fallback_provider and self.fallback_provider.is_available():
            fallback_name = self.fallback_provider.get_provider_info()['name']
            if fallback_name not in available:
                available.append(fallback_name)
        
        return available
    
    def _report_provider_status(self) -> None:
        """Report the current provider configuration and availability."""
        print("🔧 AI Provider Configuration:")
        
        # Report primary provider
        if self.primary_provider:
            primary_info = self.primary_provider.get_provider_info()
            status = "✅ Available" if self.primary_provider.is_available() else "❌ Unavailable"
            print(f"   Primary: {primary_info['name']} ({primary_info.get('type', 'unknown')}) - {status}")
            
            # Add model info if available
            if 'model' in primary_info:
                print(f"            Model: {primary_info['model']}")
        else:
            print("   Primary: ❌ Not configured")
        
        # Report fallback provider
        if self.config.enable_fallback:
            if self.fallback_provider:
                fallback_info = self.fallback_provider.get_provider_info()
                status = "✅ Available" if self.fallback_provider.is_available() else "❌ Unavailable"
                print(f"   Fallback: {fallback_info['name']} ({fallback_info.get('type', 'unknown')}) - {status}")
                
                # Add model info if available
                if 'model' in fallback_info:
                    print(f"             Model: {fallback_info['model']}")
            else:
                print("   Fallback: ❌ Not configured")
        else:
            print("   Fallback: ⚠️  Disabled")
        
        print()  # Empty line for readability
    
    def validate_configuration(self) -> List[str]:
        """Validate the current provider configuration.
        
        Returns:
            List of configuration issues/warnings
        """
        issues = []
        
        # Check if any provider is available
        if not self.primary_provider:
            issues.append("No primary AI provider configured")
        elif not self.primary_provider.is_available():
            primary_info = self.primary_provider.get_provider_info()
            issues.append(f"Primary provider ({primary_info['name']}) is not available")
        
        # Check fallback configuration
        if self.config.enable_fallback:
            if not self.fallback_provider:
                issues.append("Fallback is enabled but no fallback provider configured")
            elif not self.fallback_provider.is_available():
                fallback_info = self.fallback_provider.get_provider_info()
                issues.append(f"Fallback provider ({fallback_info['name']}) is not available")
        else:
            # Warn if primary is not available and fallback is disabled
            if self.primary_provider and not self.primary_provider.is_available():
                issues.append("Primary provider unavailable and fallback is disabled - consider enabling fallback")
        
        # Check if no providers are available at all
        available_providers = self.get_available_providers()
        if not available_providers:
            issues.append("No AI providers are currently available - transcript analysis will fail")
        
        return issues