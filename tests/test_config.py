"""Unit tests for configuration management."""

import os
import pytest
from pathlib import Path
from src.config import Config, ConfigurationError


class TestConfigLoad:
    """Tests for Config.load() method."""
    
    def test_load_with_valid_env_vars(self, monkeypatch, tmp_path):
        """Test loading configuration from environment variables."""
        # Set environment variables
        monkeypatch.setenv("GEMINI_API_KEY", "test_api_key_123")
        monkeypatch.setenv("WHISPER_MODEL", "custom/whisper-model")
        monkeypatch.setenv("GEMINI_MODEL", "custom-gemini")
        monkeypatch.setenv("OUTPUT_DIR", str(tmp_path))
        monkeypatch.setenv("SKIP_EXISTING", "true")
        
        # Load config
        config = Config.load()
        
        # Verify values
        assert config.gemini_api_key == "test_api_key_123"
        assert config.whisper_model == "custom/whisper-model"
        assert config.gemini_model == "custom-gemini"
        assert config.output_dir == str(tmp_path)
        assert config.skip_existing is True
    
    def test_load_with_defaults(self, monkeypatch, tmp_path):
        """Test loading configuration with default values."""
        # Set only required API key
        monkeypatch.setenv("GEMINI_API_KEY", "test_api_key_123")
        
        # Clear other env vars to ensure defaults are used
        monkeypatch.delenv("WHISPER_MODEL", raising=False)
        monkeypatch.delenv("GEMINI_MODEL", raising=False)
        monkeypatch.delenv("OUTPUT_DIR", raising=False)
        monkeypatch.delenv("SKIP_EXISTING", raising=False)
        
        # Load config with non-existent env file to avoid loading project .env
        non_existent_env = tmp_path / "nonexistent.env"
        config = Config.load(env_file=str(non_existent_env))
        
        # Verify defaults
        assert config.gemini_api_key == "test_api_key_123"
        assert config.whisper_model == "openai/whisper-large-v3-turbo"
        assert config.gemini_model == "gemini-flash-latest"
        assert config.output_dir is None
        assert config.skip_existing is False
    
    def test_load_from_env_file(self, monkeypatch, tmp_path):
        """Test loading configuration from .env file."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            "GEMINI_API_KEY=env_file_key\n"
            "WHISPER_MODEL=env/whisper\n"
            "GEMINI_MODEL=env-gemini\n"
            "OUTPUT_DIR=/tmp/output\n"
            "SKIP_EXISTING=yes\n"
        )
        
        # Clear environment variables to ensure .env file is used
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("WHISPER_MODEL", raising=False)
        monkeypatch.delenv("GEMINI_MODEL", raising=False)
        monkeypatch.delenv("OUTPUT_DIR", raising=False)
        monkeypatch.delenv("SKIP_EXISTING", raising=False)
        
        # Load config from the .env file
        config = Config.load(str(env_file))
        
        # Verify values from .env file
        assert config.gemini_api_key == "env_file_key"
        assert config.whisper_model == "env/whisper"
        assert config.gemini_model == "env-gemini"
        assert config.output_dir == "/tmp/output"
        assert config.skip_existing is True
    
    def test_env_vars_override_env_file(self, monkeypatch, tmp_path):
        """Test that environment variables override .env file values."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            "GEMINI_API_KEY=env_file_key\n"
            "WHISPER_MODEL=env/whisper\n"
        )
        
        # Clear all env vars first
        monkeypatch.delenv("WHISPER_MODEL", raising=False)
        monkeypatch.delenv("GEMINI_MODEL", raising=False)
        monkeypatch.delenv("OUTPUT_DIR", raising=False)
        monkeypatch.delenv("SKIP_EXISTING", raising=False)
        
        # Set environment variable (should override .env file)
        monkeypatch.setenv("GEMINI_API_KEY", "env_var_key")
        
        # Load config
        config = Config.load(str(env_file))
        
        # Verify environment variable takes precedence
        assert config.gemini_api_key == "env_var_key"
        assert config.whisper_model == "env/whisper"  # From .env file
    
    def test_skip_existing_boolean_parsing(self, monkeypatch):
        """Test parsing of SKIP_EXISTING boolean values."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("", False),
        ]
        
        for value, expected in test_cases:
            monkeypatch.setenv("GEMINI_API_KEY", "test_key")
            monkeypatch.setenv("SKIP_EXISTING", value)
            
            config = Config.load()
            assert config.skip_existing == expected, f"Failed for value: {value}"


class TestConfigValidation:
    """Tests for Config.validate() method."""
    
    def test_validate_missing_api_key(self, monkeypatch, tmp_path):
        """Test validation fails when API key is missing for Gemini provider."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("AI_PROVIDER", "gemini")  # Set to gemini to require API key
        
        # Use non-existent env file to avoid loading project .env
        non_existent_env = tmp_path / "nonexistent.env"
        
        with pytest.raises(ConfigurationError) as exc_info:
            Config.load(env_file=str(non_existent_env))
        
        assert "GEMINI_API_KEY" in str(exc_info.value)
    
    def test_validate_placeholder_api_key(self, monkeypatch):
        """Test validation fails when API key is placeholder value."""
        monkeypatch.setenv("GEMINI_API_KEY", "your_api_key_here")
        monkeypatch.setenv("AI_PROVIDER", "gemini")  # Set to gemini to require API key
        
        with pytest.raises(ConfigurationError) as exc_info:
            Config.load()
        
        assert "GEMINI_API_KEY" in str(exc_info.value)
    
    def test_validate_empty_whisper_model(self, monkeypatch):
        """Test validation fails when Whisper model is empty."""
        monkeypatch.setenv("GEMINI_API_KEY", "valid_key")
        monkeypatch.setenv("WHISPER_MODEL", "")
        
        with pytest.raises(ConfigurationError) as exc_info:
            Config.load()
        
        assert "WHISPER_MODEL" in str(exc_info.value)
    
    def test_validate_empty_gemini_model(self, monkeypatch):
        """Test validation fails when Gemini model is empty."""
        monkeypatch.setenv("GEMINI_API_KEY", "valid_key")
        monkeypatch.setenv("GEMINI_MODEL", "   ")
        
        with pytest.raises(ConfigurationError) as exc_info:
            Config.load()
        
        assert "GEMINI_MODEL" in str(exc_info.value)
    
    def test_validate_multiple_errors(self, monkeypatch, tmp_path):
        """Test validation reports multiple errors at once."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("WHISPER_MODEL", "")
        monkeypatch.setenv("AI_PROVIDER", "gemini")  # Set to gemini to require API key
        
        # Use non-existent env file to avoid loading project .env
        non_existent_env = tmp_path / "nonexistent.env"
        
        with pytest.raises(ConfigurationError) as exc_info:
            Config.load(env_file=str(non_existent_env))
        
        error_msg = str(exc_info.value)
        assert "GEMINI_API_KEY" in error_msg
        assert "WHISPER_MODEL" in error_msg
    
    def test_validate_valid_config(self, monkeypatch):
        """Test validation passes with valid configuration."""
        monkeypatch.setenv("GEMINI_API_KEY", "valid_key_123")
        monkeypatch.setenv("WHISPER_MODEL", "openai/whisper-large-v3-turbo")
        monkeypatch.setenv("GEMINI_MODEL", "gemini-flash-latest")
        
        # Should not raise exception
        config = Config.load()
        assert config.gemini_api_key == "valid_key_123"
    
    def test_validate_local_provider_no_api_key_required(self, monkeypatch, tmp_path):
        """Test validation passes for local provider without API key."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("AI_PROVIDER", "local")
        monkeypatch.setenv("ENABLE_FALLBACK", "false")
        
        # Use non-existent env file to avoid loading project .env
        non_existent_env = tmp_path / "nonexistent.env"
        
        # Should not raise exception
        config = Config.load(env_file=str(non_existent_env))
        assert config.ai_provider == "local"
        assert config.enable_fallback is False
    
    def test_validate_fallback_requires_api_key(self, monkeypatch, tmp_path):
        """Test validation fails when fallback is enabled but API key is missing."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("AI_PROVIDER", "local")
        monkeypatch.setenv("ENABLE_FALLBACK", "true")
        
        # Use non-existent env file to avoid loading project .env
        non_existent_env = tmp_path / "nonexistent.env"
        
        with pytest.raises(ConfigurationError) as exc_info:
            Config.load(env_file=str(non_existent_env))
        
        assert "GEMINI_API_KEY" in str(exc_info.value)
        assert "fallback" in str(exc_info.value)
    
    def test_validate_invalid_ai_provider(self, monkeypatch):
        """Test validation fails with invalid AI provider."""
        monkeypatch.setenv("GEMINI_API_KEY", "valid_key")
        monkeypatch.setenv("AI_PROVIDER", "invalid_provider")
        
        with pytest.raises(ConfigurationError) as exc_info:
            Config.load()
        
        assert "AI_PROVIDER" in str(exc_info.value)
    
    def test_validate_invalid_framework(self, monkeypatch):
        """Test validation fails with invalid local model framework."""
        monkeypatch.setenv("GEMINI_API_KEY", "valid_key")
        monkeypatch.setenv("AI_PROVIDER", "local")
        monkeypatch.setenv("LOCAL_MODEL_FRAMEWORK", "invalid_framework")
        
        with pytest.raises(ConfigurationError) as exc_info:
            Config.load()
        
        assert "LOCAL_MODEL_FRAMEWORK" in str(exc_info.value)
    
    def test_validate_transformers_framework_rejected(self, monkeypatch):
        """Test validation fails when transformers framework is specified."""
        monkeypatch.setenv("GEMINI_API_KEY", "valid_key")
        monkeypatch.setenv("AI_PROVIDER", "local")
        monkeypatch.setenv("LOCAL_MODEL_FRAMEWORK", "transformers")
        
        with pytest.raises(ConfigurationError) as exc_info:
            Config.load()
        
        assert "LOCAL_MODEL_FRAMEWORK" in str(exc_info.value)
        assert "ollama" in str(exc_info.value)
        assert "auto" in str(exc_info.value)


class TestAIProviderConfig:
    """Tests for AI provider configuration."""
    
    def test_ai_provider_defaults(self, monkeypatch, tmp_path):
        """Test AI provider default values."""
        # Clear all AI provider env vars to test defaults
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("AI_PROVIDER", raising=False)
        monkeypatch.delenv("ENABLE_FALLBACK", raising=False)
        monkeypatch.delenv("LOCAL_MODEL_NAME", raising=False)
        monkeypatch.delenv("LOCAL_MODEL_FRAMEWORK", raising=False)
        
        # Use non-existent env file to avoid loading project .env
        non_existent_env = tmp_path / "nonexistent.env"
        
        config = Config.load(env_file=str(non_existent_env))
        
        # Verify defaults
        assert config.ai_provider == "local"
        assert config.enable_fallback is False
        assert config.local_model_name == "phi4"
        assert config.local_model_framework == "auto"
        assert config.ollama_base_url == "http://localhost:11434"
        assert config.analysis_timeout == 300
        assert config.use_gpu is True
    
    def test_ai_provider_env_vars(self, monkeypatch):
        """Test loading AI provider settings from environment variables."""
        monkeypatch.setenv("AI_PROVIDER", "gemini")
        monkeypatch.setenv("ENABLE_FALLBACK", "true")
        monkeypatch.setenv("LOCAL_MODEL_NAME", "llama2")
        monkeypatch.setenv("LOCAL_MODEL_FRAMEWORK", "ollama")
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom:8080")
        monkeypatch.setenv("ANALYSIS_TIMEOUT", "600")
        monkeypatch.setenv("USE_GPU", "false")
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        
        config = Config.load()
        
        assert config.ai_provider == "gemini"
        assert config.enable_fallback is True
        assert config.local_model_name == "llama2"
        assert config.local_model_framework == "ollama"
        assert config.ollama_base_url == "http://custom:8080"
        assert config.analysis_timeout == 600
        assert config.use_gpu is False
