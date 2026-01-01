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
    and handles fallback logic when the primary provider fails. It also supports
    sequential multi-model usage for review passes.
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
        self.review_providers: List[BaseAIProvider] = []
        
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
        
        # Initialize review providers for sequential model usage
        self._initialize_review_providers()
    
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
    
    def _initialize_review_providers(self) -> None:
        """Initialize providers for sequential review model usage.
        
        Creates provider instances for each model in the review sequence.
        """
        self.review_providers = []
        
        # If no review models configured, use empty list (will fall back to primary)
        if not self.config.review_models:
            return
        
        # Create provider for each review model
        for model_name in self.config.review_models:
            provider = self._create_model_provider(
                model_name, 
                self.config.review_model_framework
            )
            if provider:
                self.review_providers.append(provider)
                print(f"🔧 Initialized review provider for model: {model_name}")
            else:
                print(f"⚠️  Failed to initialize review provider for model: {model_name}")
    
    def _create_model_provider(self, model_name: str, framework: str = "ollama") -> Optional[BaseAIProvider]:
        """Create a provider for a specific model and framework.
        
        Args:
            model_name: Name of the model to create provider for
            framework: Framework to use ("ollama", "auto")
            
        Returns:
            Provider instance or None if creation fails
        """
        if not model_name or not model_name.strip():
            return None
        
        # Currently only support Ollama for review models
        if framework == "ollama" or framework == "auto":
            return self._try_create_ollama_provider_for_model(model_name)
        
        return None
    
    def _try_create_ollama_provider_for_model(self, model_name: str) -> Optional[BaseAIProvider]:
        """Try to create an Ollama provider for a specific model.
        
        Args:
            model_name: Name of the model to create provider for
            
        Returns:
            Ollama provider instance or None if not available
        """
        try:
            from src.providers.ollama_provider import OllamaProvider
            
            # Get model parameters from config
            model_params = self.config.model_parameters or {}
            
            provider = OllamaProvider(
                model_name=model_name,
                base_url=self.config.ollama_base_url,
                timeout=self.config.analysis_timeout,
                **model_params
            )
            
            # Test if provider is available (but don't log for each model)
            if provider.is_available():
                return provider
            else:
                return None
                
        except Exception as e:
            # Provider creation failed
            return None
    
    def get_review_provider(self, pass_number: int) -> BaseAIProvider:
        """Get provider for specific review pass with enhanced fallback logic and logging.
        
        This method implements the sequential model selection logic where each review
        pass uses a different model from the configured sequence. When a model is
        unavailable, it falls back to the next available model in the sequence.
        
        Args:
            pass_number: Review pass number (1-indexed)
            
        Returns:
            Provider instance to use for the review pass
            
        Raises:
            ValueError: If pass_number is less than 1
            RuntimeError: If no providers are available
        """
        if pass_number < 1:
            raise ValueError("Pass number must be at least 1")
        
        # If no review providers configured, fall back to primary provider
        if not self.review_providers:
            if self.primary_provider and self.primary_provider.is_available():
                primary_info = self.primary_provider.get_provider_info()
                print(f"   📌 No review models configured, using primary provider: {primary_info.get('model', 'unknown')}")
                return self.primary_provider
            elif self.fallback_provider and self.fallback_provider.is_available():
                fallback_info = self.fallback_provider.get_provider_info()
                print(f"   📌 No review models configured, using fallback provider: {fallback_info.get('model', 'unknown')}")
                return self.fallback_provider
            else:
                raise RuntimeError("No available providers for review pass (no review models configured and no primary/fallback available)")
        
        # Calculate which model should be used for this pass (cycling through sequence)
        provider_index = (pass_number - 1) % len(self.review_providers)
        target_provider = self.review_providers[provider_index]
        expected_model = self.config.review_models[provider_index]
        
        # If target provider is available, use it
        if target_provider.is_available():
            # Log successful sequential model selection
            if pass_number <= len(self.config.review_models):
                print(f"   🎯 Sequential model selection: pass {pass_number} → {expected_model}")
            else:
                cycle_number = ((pass_number - 1) // len(self.config.review_models)) + 1
                position_in_cycle = ((pass_number - 1) % len(self.config.review_models)) + 1
                print(f"   🔄 Cycling through models (cycle {cycle_number}, position {position_in_cycle}): pass {pass_number} → {expected_model}")
            
            return target_provider
        
        # Target provider not available, try fallback within sequence
        print(f"   ⚠️  Target model '{expected_model}' unavailable for pass {pass_number}")
        return self._get_fallback_review_provider(pass_number, provider_index)
    
    def _get_fallback_review_provider(self, pass_number: int, failed_index: int) -> BaseAIProvider:
        """Get fallback provider when the target review provider is unavailable.
        
        This method implements comprehensive fallback logic:
        1. Try other models in the review sequence
        2. Fall back to primary provider
        3. Fall back to fallback provider
        
        Args:
            pass_number: Review pass number (1-indexed)
            failed_index: Index of the provider that failed
            
        Returns:
            Available provider instance
            
        Raises:
            RuntimeError: If no providers are available
        """
        failed_model = self.config.review_models[failed_index]
        
        # Try other providers in the review sequence first
        for i, provider in enumerate(self.review_providers):
            if i != failed_index and provider.is_available():
                fallback_model = self.config.review_models[i]
                print(f"   🔄 Fallback within sequence: '{failed_model}' → '{fallback_model}'")
                return provider
        
        # No review providers available, fall back to primary provider
        if self.primary_provider and self.primary_provider.is_available():
            primary_info = self.primary_provider.get_provider_info()
            print(f"   🔄 Fallback to primary provider: '{failed_model}' → {primary_info.get('model', 'unknown')}")
            return self.primary_provider
        
        # Fall back to fallback provider as last resort
        if self.fallback_provider and self.fallback_provider.is_available():
            fallback_info = self.fallback_provider.get_provider_info()
            print(f"   🔄 Fallback to fallback provider: '{failed_model}' → {fallback_info.get('model', 'unknown')}")
            return self.fallback_provider
        
        # No providers available at all
        available_models = [
            self.config.review_models[i] for i, p in enumerate(self.review_providers) 
            if p.is_available()
        ]
        
        primary_status = "available" if (self.primary_provider and self.primary_provider.is_available()) else "unavailable"
        fallback_status = "available" if (self.fallback_provider and self.fallback_provider.is_available()) else "unavailable"
        
        error_details = [
            f"Failed model: {failed_model}",
            f"Available review models: {available_models if available_models else 'none'}",
            f"Primary provider: {primary_status}",
            f"Fallback provider: {fallback_status}"
        ]
        
        raise RuntimeError(f"No available providers for review pass {pass_number}. {'; '.join(error_details)}")
    
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
        """Perform iterative review passes using sequential models to improve analysis quality.
        
        This method implements sequential multi-model support where each review pass
        uses a different model from the configured sequence. Models cycle when more
        passes are requested than models configured.
        
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
        
        total_review_passes = self.config.review_passes - 1
        print(f"🔄 Starting {total_review_passes} review pass(es) to improve analysis quality...")
        
        # Log the model sequence configuration for transparency
        if self.config.review_models and len(self.config.review_models) > 0:
            print(f"📋 Review model sequence: {' → '.join(self.config.review_models)}")
            if total_review_passes > len(self.config.review_models):
                print(f"   Note: {total_review_passes} passes requested with {len(self.config.review_models)} models - will cycle through sequence")
        else:
            print("📋 No review model sequence configured - using primary/fallback providers")
        
        successful_passes = 0
        failed_passes = 0
        
        for pass_num in range(2, self.config.review_passes + 1):
            print(f"\n📝 Review pass {pass_num}/{self.config.review_passes}")
            
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
            
            # Get provider for this specific review pass with detailed logging
            try:
                provider_to_use = self.get_review_provider(pass_num)
                provider_info = provider_to_use.get_provider_info()
                
                # Log detailed model selection information
                if self.config.review_models and len(self.config.review_models) > 0:
                    expected_model_index = (pass_num - 1) % len(self.config.review_models)
                    expected_model = self.config.review_models[expected_model_index]
                    actual_model = provider_info.get('model', 'unknown')
                    
                    if actual_model == expected_model:
                        print(f"   ✅ Using sequential model {pass_num - 1}: {actual_model}")
                    else:
                        print(f"   ⚠️  Expected model '{expected_model}' but using '{actual_model}' (fallback)")
                else:
                    print(f"   📌 Using provider: {provider_info['name']} (model: {provider_info.get('model', 'unknown')})")
                
            except RuntimeError as e:
                print(f"   ❌ No available providers for pass {pass_num}: {e}")
                print(f"   📊 Skipping remaining review passes")
                failed_passes += (self.config.review_passes - pass_num + 1)
                break
            
            # Perform the review pass with comprehensive error handling
            try:
                review_start = time.time()
                
                # Generate review-specific save paths
                review_save_path = None
                if save_raw_response:
                    base_path = save_raw_response.rsplit('.', 1)[0] if '.' in save_raw_response else save_raw_response
                    review_save_path = f"{base_path}_review_pass_{pass_num}.txt"
                
                print(f"   🔄 Processing with {provider_info['name']}...")
                
                reviewed_chapters, reviewed_notes = provider_to_use.review_analysis(
                    current_result, transcript, review_save_path
                )
                
                review_time = time.time() - review_start
                
                # Validate the reviewed results
                if not reviewed_chapters:
                    print(f"   ⚠️  Review pass {pass_num} returned no chapters - keeping previous results")
                    failed_passes += 1
                    continue
                
                # Update current results
                previous_chapter_count = len(current_chapters)
                previous_notes_count = len(current_notes)
                
                current_chapters = reviewed_chapters
                current_notes = reviewed_notes
                
                successful_passes += 1
                
                # Log detailed results
                chapter_change = len(current_chapters) - previous_chapter_count
                notes_change = len(current_notes) - previous_notes_count
                
                print(f"   ✅ Review pass {pass_num} completed in {review_time:.2f}s")
                print(f"      Chapters: {len(current_chapters)} ({chapter_change:+d})")
                print(f"      Notes: {len(current_notes)} ({notes_change:+d})")
                print(f"      Provider: {provider_info['name']} ({provider_info.get('model', 'unknown')})")
                
            except Exception as e:
                error_type = type(e).__name__
                print(f"   ❌ Review pass {pass_num} failed: {error_type}: {e}")
                print(f"      Provider: {provider_info['name']} ({provider_info.get('model', 'unknown')})")
                print(f"      Continuing with results from previous pass")
                failed_passes += 1
                
                # Log fallback information if this was a fallback provider
                if self.config.review_models and len(self.config.review_models) > 0:
                    expected_model_index = (pass_num - 1) % len(self.config.review_models)
                    expected_model = self.config.review_models[expected_model_index]
                    actual_model = provider_info.get('model', 'unknown')
                    
                    if actual_model != expected_model:
                        print(f"      Note: This was already a fallback from '{expected_model}'")
                
                # Continue to next pass instead of breaking to be more resilient
                continue
        
        # Log final summary of review passes
        print(f"\n📊 Review passes summary:")
        print(f"   ✅ Successful: {successful_passes}")
        print(f"   ❌ Failed: {failed_passes}")
        print(f"   📈 Final result: {len(current_chapters)} chapters, {len(current_notes)} notes")
        
        # Save final reviewed results if requested
        if save_notes and current_notes:
            try:
                with open(save_notes, 'w', encoding='utf-8') as f:
                    json.dump(current_notes, f, indent=2, ensure_ascii=False)
                print(f"   💾 Saved final notes to: {save_notes}")
            except Exception as e:
                print(f"   ⚠️  Failed to save notes: {e}")
        
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
        
        # Report review providers
        if self.config.review_models and self.config.review_passes > 1:
            print(f"   Review Models ({len(self.config.review_models)} configured):")
            for i, model_name in enumerate(self.config.review_models):
                if i < len(self.review_providers):
                    provider = self.review_providers[i]
                    status = "✅ Available" if provider.is_available() else "❌ Unavailable"
                    print(f"     {i+1}. {model_name} - {status}")
                else:
                    print(f"     {i+1}. {model_name} - ❌ Failed to initialize")
        elif self.config.review_passes > 1:
            print("   Review Models: ⚠️  Using primary/fallback providers")
        
        print()  # Empty line for readability
    
    def validate_configuration(self) -> List[str]:
        """Validate the current provider configuration.
        
        This method implements startup validation for model sequence availability
        as required by Requirements 4.1, 4.2, and 4.5.
        
        Returns:
            List of configuration issues/warnings
        """
        issues = []
        
        # Use config-level model availability validation
        config_issues = self.config.validate_model_availability()
        issues.extend(config_issues)
        
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
        
        # Check review provider configuration
        if self.config.review_models and self.config.review_passes > 1:
            available_review_providers = sum(1 for p in self.review_providers if p.is_available())
            total_review_models = len(self.config.review_models)
            
            if available_review_providers == 0:
                issues.append("No review models are available - review passes will use primary/fallback providers")
            elif available_review_providers < total_review_models:
                unavailable_count = total_review_models - available_review_providers
                issues.append(f"{unavailable_count} of {total_review_models} review models are unavailable")
            
            # Check for specific model availability issues
            for i, model_name in enumerate(self.config.review_models):
                if i < len(self.review_providers):
                    if not self.review_providers[i].is_available():
                        issues.append(f"Review model '{model_name}' is not available")
                else:
                    issues.append(f"Review model '{model_name}' failed to initialize")
        
        # Check if no providers are available at all
        available_providers = self.get_available_providers()
        if not available_providers:
            issues.append("No AI providers are currently available - transcript analysis will fail")
        
        return issues
    
    def get_configuration_status(self) -> Dict[str, Any]:
        """Get comprehensive provider configuration status.
        
        This method implements configuration status reporting as required
        by Requirements 4.4.
        
        Returns:
            Dictionary containing detailed provider status
        """
        status = {
            "providers": {
                "primary": None,
                "fallback": None,
                "review_models": []
            },
            "availability": {
                "primary_available": False,
                "fallback_available": False,
                "review_models_available": 0,
                "total_available": 0
            },
            "configuration_issues": [],
            "recommendations": []
        }
        
        # Primary provider status
        if self.primary_provider:
            primary_info = self.primary_provider.get_provider_info()
            primary_available = self.primary_provider.is_available()
            status["providers"]["primary"] = {
                "name": primary_info.get("name", "unknown"),
                "type": primary_info.get("type", "unknown"),
                "model": primary_info.get("model", "unknown"),
                "available": primary_available
            }
            status["availability"]["primary_available"] = primary_available
            if primary_available:
                status["availability"]["total_available"] += 1
        
        # Fallback provider status
        if self.fallback_provider:
            fallback_info = self.fallback_provider.get_provider_info()
            fallback_available = self.fallback_provider.is_available()
            status["providers"]["fallback"] = {
                "name": fallback_info.get("name", "unknown"),
                "type": fallback_info.get("type", "unknown"),
                "model": fallback_info.get("model", "unknown"),
                "available": fallback_available
            }
            status["availability"]["fallback_available"] = fallback_available
            if fallback_available:
                status["availability"]["total_available"] += 1
        
        # Review models status
        if self.config.review_models:
            for i, model_name in enumerate(self.config.review_models):
                model_status = {
                    "name": model_name,
                    "position": i + 1,
                    "available": False,
                    "provider_info": None
                }
                
                if i < len(self.review_providers):
                    provider = self.review_providers[i]
                    available = provider.is_available()
                    model_status["available"] = available
                    model_status["provider_info"] = provider.get_provider_info()
                    
                    if available:
                        status["availability"]["review_models_available"] += 1
                        status["availability"]["total_available"] += 1
                
                status["providers"]["review_models"].append(model_status)
        
        # Get configuration issues
        status["configuration_issues"] = self.validate_configuration()
        
        # Generate recommendations
        status["recommendations"] = self._generate_configuration_recommendations(status)
        
        return status
    
    def _generate_configuration_recommendations(self, status: Dict[str, Any]) -> List[str]:
        """Generate configuration recommendations based on current status.
        
        Args:
            status: Current configuration status
            
        Returns:
            List of recommendations for improving configuration
        """
        recommendations = []
        
        # Check if fallback should be enabled
        if not self.config.enable_fallback and not status["availability"]["primary_available"]:
            recommendations.append("Enable fallback (ENABLE_FALLBACK=true) since primary provider is unavailable")
        elif not self.config.enable_fallback and status["availability"]["primary_available"]:
            recommendations.append("Consider enabling fallback (ENABLE_FALLBACK=true) for better reliability")
        
        # Check review model configuration
        if self.config.review_passes > 1 and not self.config.review_models:
            recommendations.append("Configure REVIEW_MODELS for better multi-pass analysis with different models")
        elif self.config.review_models and status["availability"]["review_models_available"] == 0:
            recommendations.append("No review models are available - check Ollama service and model installation")
        elif self.config.review_models and status["availability"]["review_models_available"] < len(self.config.review_models):
            unavailable = len(self.config.review_models) - status["availability"]["review_models_available"]
            recommendations.append(f"Install missing review models: {unavailable} models are unavailable")
        
        # Check if no providers are available
        if status["availability"]["total_available"] == 0:
            recommendations.append("No AI providers are available - check service status and configuration")
        
        # Check for single point of failure
        if status["availability"]["total_available"] == 1 and not self.config.enable_fallback:
            recommendations.append("Only one provider available - consider enabling fallback for redundancy")
        
        return recommendations
    
    def print_configuration_status(self) -> None:
        """Print a human-readable provider configuration status report.
        
        This method provides user-friendly provider status reporting
        as required by Requirements 4.4.
        """
        status = self.get_configuration_status()
        
        print("🤖 AI Provider Status Report")
        print("=" * 40)
        
        # Primary provider
        primary = status["providers"]["primary"]
        if primary:
            status_icon = "✅" if primary["available"] else "❌"
            print(f"Primary: {status_icon} {primary['name']} ({primary['model']})")
        else:
            print("Primary: ❌ Not configured")
        
        # Fallback provider
        fallback = status["providers"]["fallback"]
        if self.config.enable_fallback:
            if fallback:
                status_icon = "✅" if fallback["available"] else "❌"
                print(f"Fallback: {status_icon} {fallback['name']} ({fallback['model']})")
            else:
                print("Fallback: ❌ Not configured")
        else:
            print("Fallback: ⚠️  Disabled")
        
        # Review models
        review_models = status["providers"]["review_models"]
        if review_models:
            available_count = status["availability"]["review_models_available"]
            total_count = len(review_models)
            print(f"Review Models: {available_count}/{total_count} available")
            
            for model in review_models:
                status_icon = "✅" if model["available"] else "❌"
                print(f"  {model['position']}. {status_icon} {model['name']}")
        else:
            print("Review Models: Not configured")
        
        # Overall availability
        total_available = status["availability"]["total_available"]
        print(f"\nTotal Available Providers: {total_available}")
        
        # Configuration issues
        if status["configuration_issues"]:
            print("\n⚠️  Configuration Issues:")
            for issue in status["configuration_issues"]:
                print(f"   • {issue}")
        
        # Recommendations
        if status["recommendations"]:
            print("\n💡 Recommendations:")
            for rec in status["recommendations"]:
                print(f"   • {rec}")
        
        print("=" * 40)