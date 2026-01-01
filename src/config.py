"""Configuration management for the Meeting Video Chapter Tool.

This module handles loading and validating configuration from environment
variables and .env files, with environment variables taking precedence.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when configuration is invalid or incomplete."""
    pass


@dataclass
class Config:
    """Configuration for the Meeting Video Chapter Tool.
    
    Attributes:
        gemini_api_key: API key for Google Gemini
        whisper_model: Name of the Whisper model to use
        gemini_model: Name of the Gemini model to use
        output_dir: Directory where generated files will be saved
        skip_existing: Whether to skip regenerating existing files
        overlay_chapter_titles: Whether to overlay chapter titles on the video
        
        # AI Provider settings
        ai_provider: Primary AI provider to use ("local", "gemini")
        enable_fallback: Whether to use Gemini as fallback when primary fails
        local_model_name: Name of the local model to use
        local_model_framework: Framework for local models ("ollama", "auto")
        
        # Multi-model review settings
        review_models: Sequential list of models for review passes
        review_model_framework: Framework for review models ("ollama", "auto")
        
        # Provider-specific settings
        ollama_base_url: Base URL for Ollama service
        model_parameters: Provider-specific model parameters
        
        # Performance settings
        analysis_timeout: Timeout for analysis operations in seconds
        max_memory_usage: Maximum memory usage in MB (None for unlimited)
        use_gpu: Whether to use GPU acceleration when available
    """
    gemini_api_key: str
    whisper_model: str = "openai/whisper-large-v3-turbo"
    gemini_model: str = "gemini-flash-latest"
    output_dir: Optional[str] = None
    skip_existing: bool = False
    overlay_chapter_titles: bool = False
    
    # AI Provider settings
    ai_provider: str = "local"
    enable_fallback: bool = False
    local_model_name: str = "phi4"
    local_model_framework: str = "auto"
    
    # Multi-model review settings
    review_models: Optional[List[str]] = None
    review_model_framework: str = "ollama"
    
    # Provider-specific settings
    ollama_base_url: str = "http://localhost:11434"
    model_parameters: Optional[dict] = None
    
    # Performance settings
    analysis_timeout: int = 600
    max_memory_usage: Optional[int] = None
    use_gpu: bool = True
    
    # Review settings
    enable_review: bool = False
    review_passes: int = 1
    
    def get_model_for_review_pass(self, pass_number: int) -> str:
        """Get model name for specific review pass (1-indexed).
        
        Args:
            pass_number: Review pass number (1-indexed)
            
        Returns:
            str: Model name for the specified pass
            
        Raises:
            ValueError: If pass_number is less than 1
        """
        if pass_number < 1:
            raise ValueError("Pass number must be at least 1")
        
        # If no review models configured, use primary local model
        if not self.review_models:
            return self.local_model_name
        
        # Cycle through models if more passes than models
        model_index = (pass_number - 1) % len(self.review_models)
        return self.review_models[model_index]
    
    @classmethod
    def _parse_review_models(cls, env_value: str) -> Optional[List[str]]:
        """Parse comma-separated model list from environment variable.
        
        Args:
            env_value: Raw environment variable value
            
        Returns:
            List of model names, or None if empty/invalid
        """
        if not env_value or not env_value.strip():
            return None
        
        # Split by comma and strip whitespace, but preserve empty entries for validation
        models = [model.strip() for model in env_value.split(',')]
        
        # Return None if no entries found
        return models if models else None
    
    @classmethod
    def load(cls, env_file: str = ".env") -> "Config":
        """Load configuration from .env file and environment variables.
        
        Environment variables take precedence over .env file values.
        
        Args:
            env_file: Path to the .env file (default: ".env")
            
        Returns:
            Config: Loaded and validated configuration
            
        Raises:
            ConfigurationError: If configuration is invalid or incomplete
        """
        # Load .env file if it exists (doesn't override existing env vars)
        env_path = Path(env_file)
        if env_path.exists():
            load_dotenv(env_path)
        
        # Load configuration from environment variables
        gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        whisper_model = os.getenv("WHISPER_MODEL", "openai/whisper-large-v3-turbo")
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
        output_dir = os.getenv("OUTPUT_DIR")
        skip_existing_str = os.getenv("SKIP_EXISTING", "false").lower()
        overlay_chapter_titles_str = os.getenv("OVERLAY_CHAPTER_TITLES", "false").lower()
        
        # AI Provider settings
        ai_provider = os.getenv("AI_PROVIDER", "local")
        enable_fallback_str = os.getenv("ENABLE_FALLBACK", "false").lower()
        local_model_name = os.getenv("LOCAL_MODEL_NAME", "phi4")
        local_model_framework = os.getenv("LOCAL_MODEL_FRAMEWORK", "auto")
        
        # Multi-model review settings
        review_models_str = os.getenv("REVIEW_MODELS", "")
        review_model_framework = os.getenv("REVIEW_MODEL_FRAMEWORK", "ollama")
        
        # Provider-specific settings
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model_parameters_str = os.getenv("MODEL_PARAMETERS", "{}")
        
        # Performance settings
        analysis_timeout_str = os.getenv("ANALYSIS_TIMEOUT", "600")
        max_memory_usage_str = os.getenv("MAX_MEMORY_USAGE", "")
        use_gpu_str = os.getenv("USE_GPU", "true").lower()
        
        # Review settings
        enable_review_str = os.getenv("ENABLE_REVIEW", "false").lower()
        review_passes_str = os.getenv("REVIEW_PASSES", "1")
        
        # Parse boolean values
        skip_existing = skip_existing_str in ("true", "1", "yes", "on")
        overlay_chapter_titles = overlay_chapter_titles_str in ("true", "1", "yes", "on")
        enable_fallback = enable_fallback_str in ("true", "1", "yes", "on")
        use_gpu = use_gpu_str in ("true", "1", "yes", "on")
        enable_review = enable_review_str in ("true", "1", "yes", "on")
        
        # Parse numeric values
        try:
            analysis_timeout = int(analysis_timeout_str)
        except ValueError:
            analysis_timeout = 600
        
        try:
            review_passes = int(review_passes_str)
            if review_passes < 1:
                review_passes = 1
        except ValueError:
            review_passes = 1
        
        max_memory_usage = None
        if max_memory_usage_str:
            try:
                max_memory_usage = int(max_memory_usage_str)
            except ValueError:
                max_memory_usage = None
        
        # Parse model parameters JSON
        model_parameters = None
        if model_parameters_str and model_parameters_str != "{}":
            try:
                import json
                model_parameters = json.loads(model_parameters_str)
            except json.JSONDecodeError:
                model_parameters = None
        
        # Parse review models list
        review_models = cls._parse_review_models(review_models_str)
        
        # Create config instance
        config = cls(
            gemini_api_key=gemini_api_key,
            whisper_model=whisper_model,
            gemini_model=gemini_model,
            output_dir=output_dir,
            skip_existing=skip_existing,
            overlay_chapter_titles=overlay_chapter_titles,
            ai_provider=ai_provider,
            enable_fallback=enable_fallback,
            local_model_name=local_model_name,
            local_model_framework=local_model_framework,
            review_models=review_models,
            review_model_framework=review_model_framework,
            ollama_base_url=ollama_base_url,
            model_parameters=model_parameters,
            analysis_timeout=analysis_timeout,
            max_memory_usage=max_memory_usage,
            use_gpu=use_gpu,
            enable_review=enable_review,
            review_passes=review_passes
        )
        
        # Validate configuration
        config.validate()
        
        return config
    
    def validate(self) -> None:
        """Validate the configuration.
        
        Raises:
            ConfigurationError: If configuration is invalid
        """
        errors = []
        
        # Validate AI provider settings
        valid_providers = ["local", "gemini"]
        if self.ai_provider not in valid_providers:
            errors.append(f"Invalid AI_PROVIDER: must be one of {valid_providers}")
        
        # Check API key requirements based on provider configuration
        if self.ai_provider == "gemini" or self.enable_fallback:
            if not self.gemini_api_key or self.gemini_api_key == "your_api_key_here":
                if self.ai_provider == "gemini":
                    errors.append("Missing required API key: GEMINI_API_KEY (required for Gemini provider)")
                else:
                    errors.append("Missing required API key: GEMINI_API_KEY (required for fallback)")
        
        # Validate local model settings
        if self.ai_provider == "local":
            if not self.local_model_name or not self.local_model_name.strip():
                errors.append("Invalid LOCAL_MODEL_NAME: model name cannot be empty when using local provider")
            
            valid_frameworks = ["ollama", "auto"]
            if self.local_model_framework not in valid_frameworks:
                errors.append(f"Invalid LOCAL_MODEL_FRAMEWORK: must be one of {valid_frameworks}")
        
        # Validate review model settings
        if self.review_models:
            # Check for empty model names in sequence
            for i, model in enumerate(self.review_models):
                if not model or not model.strip():
                    errors.append(f"Invalid REVIEW_MODELS: model at position {i+1} cannot be empty")
            
            # Check for duplicate models in sequence
            if len(self.review_models) != len(set(self.review_models)):
                errors.append("Invalid REVIEW_MODELS: duplicate models found in sequence")
            
            # Validate review model framework
            valid_review_frameworks = ["ollama", "auto"]
            if self.review_model_framework not in valid_review_frameworks:
                errors.append(f"Invalid REVIEW_MODEL_FRAMEWORK: must be one of {valid_review_frameworks}")
            
            # Check maximum sequence length to prevent excessive configuration
            if len(self.review_models) > 10:
                errors.append("Invalid REVIEW_MODELS: maximum of 10 models allowed in sequence")
        
        # Validate model names (basic check - not empty)
        if not self.whisper_model or not self.whisper_model.strip():
            errors.append("Invalid WHISPER_MODEL: model name cannot be empty")
        
        # Validate Whisper model variants (Requirement 7.2)
        valid_whisper_models = [
            "openai/whisper-base",
            "openai/whisper-small", 
            "openai/whisper-medium",
            "openai/whisper-large",
            "openai/whisper-large-v2",
            "openai/whisper-large-v3",
            "openai/whisper-large-v3-turbo"
        ]
        if self.whisper_model not in valid_whisper_models:
            # Allow custom models but warn about validation
            import sys
            print(f"Warning: Using non-standard Whisper model: {self.whisper_model}", file=sys.stderr)
            print(f"Supported models: {', '.join(valid_whisper_models)}", file=sys.stderr)
        
        if not self.gemini_model or not self.gemini_model.strip():
            errors.append("Invalid GEMINI_MODEL: model name cannot be empty")
        
        # Validate provider-specific settings
        if self.ollama_base_url and not self.ollama_base_url.startswith(("http://", "https://")):
            errors.append("Invalid OLLAMA_BASE_URL: must start with http:// or https://")
        
        # Validate performance settings
        if self.analysis_timeout <= 0:
            errors.append("Invalid ANALYSIS_TIMEOUT: must be positive")
        
        if self.max_memory_usage is not None and self.max_memory_usage <= 0:
            errors.append("Invalid MAX_MEMORY_USAGE: must be positive or None")
        
        # Validate review settings
        if self.review_passes < 1:
            errors.append("Invalid REVIEW_PASSES: must be at least 1")
        
        if self.review_passes > 10:
            errors.append("Invalid REVIEW_PASSES: maximum of 10 passes allowed to prevent excessive processing")
        
        # Validate output directory if specified
        if self.output_dir:
            output_path = Path(self.output_dir)
            # Check if path is valid (not checking existence, just validity)
            try:
                output_path.resolve()
            except (OSError, ValueError) as e:
                errors.append(f"Invalid OUTPUT_DIR path: {e}")
        
        # If there are validation errors, raise exception with all errors
        if errors:
            error_message = "Configuration validation failed:\n"
            for error in errors:
                error_message += f"  - {error}\n"
            error_message += "\nSet via environment variable or .env file"
            raise ConfigurationError(error_message)
    
    def validate_model_availability(self) -> List[str]:
        """Validate availability of configured models at startup.
        
        This method performs startup validation of model sequence availability
        as required by Requirements 4.1, 4.2, and 4.5.
        
        Returns:
            List of validation issues/warnings about model availability
        """
        issues = []
        
        # Validate primary local model availability
        if self.ai_provider == "local":
            primary_issue = self._validate_single_model_availability(
                self.local_model_name, 
                self.local_model_framework,
                "primary local model"
            )
            if primary_issue:
                issues.append(primary_issue)
        
        # Validate review models availability if configured
        if self.review_models and len(self.review_models) > 0:
            available_count = 0
            for i, model_name in enumerate(self.review_models):
                model_issue = self._validate_single_model_availability(
                    model_name,
                    self.review_model_framework,
                    f"review model {i+1} '{model_name}'"
                )
                if model_issue:
                    issues.append(model_issue)
                else:
                    available_count += 1
            
            # Check if any review models are available
            if available_count == 0:
                issues.append(
                    "No review models are available - review passes will fall back to primary/fallback providers. "
                    "Consider checking your model configuration or Ollama service status."
                )
            elif available_count < len(self.review_models):
                unavailable_count = len(self.review_models) - available_count
                issues.append(
                    f"{unavailable_count} of {len(self.review_models)} review models are unavailable. "
                    f"Sequential model selection will use fallback logic for unavailable models."
                )
        
        # Validate Gemini API key if needed for fallback
        if self.enable_fallback and (not self.gemini_api_key or self.gemini_api_key == "your_api_key_here"):
            issues.append(
                "Fallback is enabled but GEMINI_API_KEY is missing or invalid. "
                "Fallback to Gemini will not work. Set a valid API key or disable fallback."
            )
        
        return issues
    
    def _validate_single_model_availability(self, model_name: str, framework: str, description: str) -> Optional[str]:
        """Validate availability of a single model.
        
        Args:
            model_name: Name of the model to validate
            framework: Framework to use for validation ("ollama", "auto")
            description: Human-readable description for error messages
            
        Returns:
            Error message if model is unavailable, None if available
        """
        if not model_name or not model_name.strip():
            return f"Invalid {description}: model name is empty"
        
        # Currently only validate Ollama models
        if framework in ["ollama", "auto"]:
            return self._validate_ollama_model_availability(model_name, description)
        
        # For other frameworks, just check name validity
        return None
    
    def _validate_ollama_model_availability(self, model_name: str, description: str) -> Optional[str]:
        """Validate availability of an Ollama model.
        
        Args:
            model_name: Name of the Ollama model
            description: Human-readable description for error messages
            
        Returns:
            Error message if model is unavailable, None if available
        """
        try:
            import requests
            import json
            
            # Check if Ollama service is running
            try:
                response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
                if response.status_code != 200:
                    return f"Ollama service not accessible at {self.ollama_base_url} for {description}"
            except requests.exceptions.RequestException:
                return f"Ollama service not running at {self.ollama_base_url} for {description}"
            
            # Check if specific model is available
            try:
                models_data = response.json()
                available_models = [model.get("name", "").split(":")[0] for model in models_data.get("models", [])]
                
                # Check exact match or partial match (for models with tags)
                model_base_name = model_name.split(":")[0]
                if model_name not in available_models and model_base_name not in available_models:
                    return (
                        f"Model '{model_name}' not found in Ollama for {description}. "
                        f"Available models: {', '.join(available_models) if available_models else 'none'}. "
                        f"Run 'ollama pull {model_name}' to install it."
                    )
            except (json.JSONDecodeError, KeyError):
                return f"Unable to parse Ollama model list for {description}"
                
        except ImportError:
            # requests not available, skip validation
            return f"Cannot validate {description} - requests library not available"
        except Exception as e:
            return f"Error validating {description}: {type(e).__name__}: {e}"
        
        return None  # Model is available
    
    def get_configuration_status(self) -> Dict[str, Any]:
        """Get comprehensive configuration status report.
        
        This method implements configuration status reporting as required
        by Requirements 4.4.
        
        Returns:
            Dictionary containing detailed configuration status
        """
        status = {
            "configuration_valid": True,
            "validation_errors": [],
            "validation_warnings": [],
            "ai_providers": {},
            "model_configuration": {},
            "performance_settings": {},
            "feature_flags": {},
            "backward_compatibility": {
                "legacy_config_detected": False,
                "migration_needed": False,
                "compatibility_notes": []
            }
        }
        
        # Run basic configuration validation
        try:
            self.validate()
        except ConfigurationError as e:
            status["configuration_valid"] = False
            status["validation_errors"] = str(e).split('\n')[1:-1]  # Extract error lines
        
        # Run model availability validation
        model_issues = self.validate_model_availability()
        status["validation_warnings"] = model_issues
        
        # AI Provider status
        status["ai_providers"] = {
            "primary_provider": self.ai_provider,
            "fallback_enabled": self.enable_fallback,
            "local_model": {
                "name": self.local_model_name,
                "framework": self.local_model_framework,
                "base_url": self.ollama_base_url if self.local_model_framework in ["ollama", "auto"] else None
            },
            "gemini_configured": bool(self.gemini_api_key and self.gemini_api_key != "your_api_key_here")
        }
        
        # Model configuration status
        status["model_configuration"] = {
            "whisper_model": self.whisper_model,
            "gemini_model": self.gemini_model,
            "review_models": {
                "enabled": bool(self.review_models),
                "count": len(self.review_models) if self.review_models else 0,
                "models": self.review_models or [],
                "framework": self.review_model_framework,
                "review_passes": self.review_passes
            }
        }
        
        # Performance settings
        status["performance_settings"] = {
            "analysis_timeout": self.analysis_timeout,
            "max_memory_usage": self.max_memory_usage,
            "use_gpu": self.use_gpu
        }
        
        # Feature flags
        status["feature_flags"] = {
            "skip_existing": self.skip_existing,
            "overlay_chapter_titles": self.overlay_chapter_titles,
            "enable_review": self.enable_review
        }
        
        # Backward compatibility analysis
        status["backward_compatibility"] = self._analyze_backward_compatibility()
        
        return status
    
    def _analyze_backward_compatibility(self) -> Dict[str, Any]:
        """Analyze configuration for backward compatibility issues.
        
        This method ensures backward compatibility with existing configurations
        as required by Requirements 5.1 and 5.2.
        
        Returns:
            Dictionary containing backward compatibility analysis
        """
        compatibility = {
            "legacy_config_detected": False,
            "migration_needed": False,
            "compatibility_notes": []
        }
        
        # Check for legacy single-model configuration
        if not self.review_models and self.review_passes == 1:
            compatibility["legacy_config_detected"] = True
            compatibility["compatibility_notes"].append(
                "Using legacy single-model configuration - fully compatible with new system"
            )
        
        # Check if user is using new multi-model features
        if self.review_models and len(self.review_models) > 0:
            compatibility["compatibility_notes"].append(
                f"Using new multi-model configuration with {len(self.review_models)} review models"
            )
        
        # Check for deprecated or changed settings
        if self.local_model_framework == "transformers":
            compatibility["migration_needed"] = True
            compatibility["compatibility_notes"].append(
                "DEPRECATED: transformers framework is no longer supported. "
                "Please use 'ollama' or 'auto' for LOCAL_MODEL_FRAMEWORK."
            )
        
        # Check for potential configuration improvements
        if self.ai_provider == "local" and not self.enable_fallback:
            compatibility["compatibility_notes"].append(
                "SUGGESTION: Consider enabling fallback (ENABLE_FALLBACK=true) for better reliability"
            )
        
        if self.review_passes > 1 and not self.review_models:
            compatibility["compatibility_notes"].append(
                "SUGGESTION: Configure REVIEW_MODELS for better multi-pass analysis with different models"
            )
        
        return compatibility
    
    def print_configuration_status(self) -> None:
        """Print a human-readable configuration status report.
        
        This method provides user-friendly configuration status reporting
        as required by Requirements 4.4.
        """
        status = self.get_configuration_status()
        
        print("🔧 Configuration Status Report")
        print("=" * 50)
        
        # Overall status
        if status["configuration_valid"]:
            print("✅ Configuration is valid")
        else:
            print("❌ Configuration has errors")
            for error in status["validation_errors"]:
                print(f"   • {error}")
        
        # Warnings
        if status["validation_warnings"]:
            print("\n⚠️  Configuration warnings:")
            for warning in status["validation_warnings"]:
                print(f"   • {warning}")
        
        # AI Providers
        print(f"\n🤖 AI Provider Configuration:")
        providers = status["ai_providers"]
        print(f"   Primary: {providers['primary_provider']}")
        print(f"   Fallback: {'enabled' if providers['fallback_enabled'] else 'disabled'}")
        
        if providers["primary_provider"] == "local":
            local = providers["local_model"]
            print(f"   Local Model: {local['name']} ({local['framework']})")
            if local["base_url"]:
                print(f"   Ollama URL: {local['base_url']}")
        
        print(f"   Gemini API: {'configured' if providers['gemini_configured'] else 'not configured'}")
        
        # Model Configuration
        print(f"\n📋 Model Configuration:")
        models = status["model_configuration"]
        print(f"   Whisper: {models['whisper_model']}")
        print(f"   Gemini: {models['gemini_model']}")
        
        review = models["review_models"]
        if review["enabled"]:
            print(f"   Review Models: {review['count']} configured ({review['framework']})")
            for i, model in enumerate(review["models"], 1):
                print(f"     {i}. {model}")
            print(f"   Review Passes: {review['review_passes']}")
        else:
            print("   Review Models: not configured")
        
        # Performance Settings
        print(f"\n⚡ Performance Settings:")
        perf = status["performance_settings"]
        print(f"   Timeout: {perf['analysis_timeout']}s")
        print(f"   Memory Limit: {perf['max_memory_usage'] or 'unlimited'}")
        print(f"   GPU: {'enabled' if perf['use_gpu'] else 'disabled'}")
        
        # Feature Flags
        print(f"\n🎛️  Feature Flags:")
        features = status["feature_flags"]
        print(f"   Skip Existing: {features['skip_existing']}")
        print(f"   Chapter Overlay: {features['overlay_chapter_titles']}")
        print(f"   Review Enabled: {features['enable_review']}")
        
        # Backward Compatibility
        compat = status["backward_compatibility"]
        if compat["legacy_config_detected"] or compat["migration_needed"] or compat["compatibility_notes"]:
            print(f"\n🔄 Backward Compatibility:")
            
            if compat["legacy_config_detected"]:
                print("   📜 Legacy configuration detected - fully supported")
            
            if compat["migration_needed"]:
                print("   🚨 Migration needed for deprecated settings")
            
            for note in compat["compatibility_notes"]:
                if note.startswith("DEPRECATED:"):
                    print(f"   ❌ {note}")
                elif note.startswith("SUGGESTION:"):
                    print(f"   💡 {note}")
                else:
                    print(f"   ℹ️  {note}")
        
        print("\n" + "=" * 50)
