"""Configuration management for the Meeting Video Chapter Tool.

This module handles loading and validating configuration from environment
variables and .env files, with environment variables taking precedence.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
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
    
    # Provider-specific settings
    ollama_base_url: str = "http://localhost:11434"
    model_parameters: Optional[dict] = None
    
    # Performance settings
    analysis_timeout: int = 300
    max_memory_usage: Optional[int] = None
    use_gpu: bool = True
    
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
        
        # Provider-specific settings
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model_parameters_str = os.getenv("MODEL_PARAMETERS", "{}")
        
        # Performance settings
        analysis_timeout_str = os.getenv("ANALYSIS_TIMEOUT", "300")
        max_memory_usage_str = os.getenv("MAX_MEMORY_USAGE", "")
        use_gpu_str = os.getenv("USE_GPU", "true").lower()
        
        # Parse boolean values
        skip_existing = skip_existing_str in ("true", "1", "yes", "on")
        overlay_chapter_titles = overlay_chapter_titles_str in ("true", "1", "yes", "on")
        enable_fallback = enable_fallback_str in ("true", "1", "yes", "on")
        use_gpu = use_gpu_str in ("true", "1", "yes", "on")
        
        # Parse numeric values
        try:
            analysis_timeout = int(analysis_timeout_str)
        except ValueError:
            analysis_timeout = 300
        
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
            ollama_base_url=ollama_base_url,
            model_parameters=model_parameters,
            analysis_timeout=analysis_timeout,
            max_memory_usage=max_memory_usage,
            use_gpu=use_gpu
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
