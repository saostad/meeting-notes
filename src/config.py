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
    """
    gemini_api_key: str
    whisper_model: str = "openai/whisper-large-v3-turbo"
    gemini_model: str = "gemini-flash-latest"
    output_dir: Optional[str] = None
    skip_existing: bool = False
    
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
        
        # Parse boolean value
        skip_existing = skip_existing_str in ("true", "1", "yes", "on")
        
        # Create config instance
        config = cls(
            gemini_api_key=gemini_api_key,
            whisper_model=whisper_model,
            gemini_model=gemini_model,
            output_dir=output_dir,
            skip_existing=skip_existing
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
        
        # Check required API keys
        if not self.gemini_api_key or self.gemini_api_key == "your_api_key_here":
            errors.append("Missing required API key: GEMINI_API_KEY")
        
        # Validate model names (basic check - not empty)
        if not self.whisper_model or not self.whisper_model.strip():
            errors.append("Invalid WHISPER_MODEL: model name cannot be empty")
        
        if not self.gemini_model or not self.gemini_model.strip():
            errors.append("Invalid GEMINI_MODEL: model name cannot be empty")
        
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
