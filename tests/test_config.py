"""Unit tests for configuration management."""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
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
        monkeypatch.delenv("ANALYSIS_TIMEOUT", raising=False)
        monkeypatch.delenv("WHISPER_MODEL", raising=False)
        monkeypatch.delenv("GEMINI_MODEL", raising=False)
        monkeypatch.delenv("OUTPUT_DIR", raising=False)
        monkeypatch.delenv("SKIP_EXISTING", raising=False)
        monkeypatch.delenv("OVERLAY_CHAPTER_TITLES", raising=False)
        monkeypatch.delenv("MODEL_PARAMETERS", raising=False)
        monkeypatch.delenv("ENABLE_REVIEW", raising=False)
        monkeypatch.delenv("REVIEW_PASSES", raising=False)
        
        # Use non-existent env file to avoid loading project .env
        non_existent_env = tmp_path / "nonexistent.env"
        
        config = Config.load(env_file=str(non_existent_env))
        
        # Verify defaults
        assert config.ai_provider == "local"
        assert config.enable_fallback is False
        assert config.local_model_name == "phi4"
        assert config.local_model_framework == "auto"
        assert config.ollama_base_url == "http://localhost:11434"
        assert config.analysis_timeout == 600
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


class TestMultiModelConfig:
    """Tests for multi-model review configuration."""
    
    def test_parse_review_models_valid_sequence(self, monkeypatch):
        """Test parsing valid comma-separated model sequence."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("REVIEW_MODELS", "phi4,mistral-nemo,llama3.2")
        
        config = Config.load()
        
        assert config.review_models == ["phi4", "mistral-nemo", "llama3.2"]
        assert config.review_model_framework == "ollama"  # default
    
    def test_parse_review_models_with_spaces(self, monkeypatch):
        """Test parsing model sequence with extra spaces."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("REVIEW_MODELS", " phi4 , mistral-nemo , llama3.2 ")
        
        config = Config.load()
        
        assert config.review_models == ["phi4", "mistral-nemo", "llama3.2"]
    
    def test_parse_review_models_empty_string(self, monkeypatch):
        """Test parsing empty review models string."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("REVIEW_MODELS", "")
        
        config = Config.load()
        
        assert config.review_models is None
    
    def test_parse_review_models_whitespace_only(self, monkeypatch):
        """Test parsing whitespace-only review models string."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("REVIEW_MODELS", "   ")
        
        config = Config.load()
        
        assert config.review_models is None
    
    def test_parse_review_models_with_empty_entries(self, monkeypatch):
        """Test parsing model sequence with empty entries fails validation."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("REVIEW_MODELS", "phi4,,mistral-nemo,")
        
        # Should fail validation due to empty entries
        with pytest.raises(ConfigurationError):
            Config.load()
    
    def test_review_model_framework_custom(self, monkeypatch):
        """Test setting custom review model framework."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("REVIEW_MODELS", "phi4,mistral-nemo")
        monkeypatch.setenv("REVIEW_MODEL_FRAMEWORK", "auto")
        
        config = Config.load()
        
        assert config.review_model_framework == "auto"
    
    def test_get_model_for_review_pass_no_sequence(self, monkeypatch):
        """Test getting model for review pass when no sequence configured."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("LOCAL_MODEL_NAME", "default-model")
        
        config = Config.load()
        
        # Should fall back to primary local model
        assert config.get_model_for_review_pass(1) == "default-model"
        assert config.get_model_for_review_pass(2) == "default-model"
        assert config.get_model_for_review_pass(5) == "default-model"
    
    def test_get_model_for_review_pass_with_sequence(self, monkeypatch):
        """Test getting model for review pass with configured sequence."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("REVIEW_MODELS", "phi4,mistral-nemo,llama3.2")
        
        config = Config.load()
        
        # Test sequential selection
        assert config.get_model_for_review_pass(1) == "phi4"
        assert config.get_model_for_review_pass(2) == "mistral-nemo"
        assert config.get_model_for_review_pass(3) == "llama3.2"
    
    def test_get_model_for_review_pass_cycling(self, monkeypatch):
        """Test model cycling when more passes than models."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("REVIEW_MODELS", "phi4,mistral-nemo")
        
        config = Config.load()
        
        # Test cycling behavior
        assert config.get_model_for_review_pass(1) == "phi4"
        assert config.get_model_for_review_pass(2) == "mistral-nemo"
        assert config.get_model_for_review_pass(3) == "phi4"  # cycles back
        assert config.get_model_for_review_pass(4) == "mistral-nemo"
        assert config.get_model_for_review_pass(5) == "phi4"
    
    def test_get_model_for_review_pass_invalid_pass_number(self, monkeypatch):
        """Test error handling for invalid pass numbers."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("REVIEW_MODELS", "phi4,mistral-nemo")
        
        config = Config.load()
        
        with pytest.raises(ValueError) as exc_info:
            config.get_model_for_review_pass(0)
        
        assert "Pass number must be at least 1" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            config.get_model_for_review_pass(-1)
        
        assert "Pass number must be at least 1" in str(exc_info.value)


class TestMultiModelValidation:
    """Tests for multi-model configuration validation."""
    
    def test_validate_empty_model_in_sequence(self, monkeypatch):
        """Test validation fails when sequence contains empty model."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("REVIEW_MODELS", "phi4,,mistral-nemo")
        
        with pytest.raises(ConfigurationError) as exc_info:
            Config.load()
        
        error_msg = str(exc_info.value)
        assert "REVIEW_MODELS" in error_msg
        assert "position 2" in error_msg
        assert "cannot be empty" in error_msg
    
    def test_validate_duplicate_models_in_sequence(self, monkeypatch):
        """Test validation fails when sequence contains duplicate models."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("REVIEW_MODELS", "phi4,mistral-nemo,phi4")
        
        with pytest.raises(ConfigurationError) as exc_info:
            Config.load()
        
        error_msg = str(exc_info.value)
        assert "REVIEW_MODELS" in error_msg
        assert "duplicate models" in error_msg
    
    def test_validate_invalid_review_model_framework(self, monkeypatch):
        """Test validation fails with invalid review model framework."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("REVIEW_MODELS", "phi4,mistral-nemo")
        monkeypatch.setenv("REVIEW_MODEL_FRAMEWORK", "invalid_framework")
        
        with pytest.raises(ConfigurationError) as exc_info:
            Config.load()
        
        error_msg = str(exc_info.value)
        assert "REVIEW_MODEL_FRAMEWORK" in error_msg
        assert "ollama" in error_msg
        assert "auto" in error_msg
    
    def test_validate_too_many_models_in_sequence(self, monkeypatch):
        """Test validation fails when sequence has too many models."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        # Create sequence with 11 models (exceeds limit of 10)
        models = [f"model{i}" for i in range(1, 12)]
        monkeypatch.setenv("REVIEW_MODELS", ",".join(models))
        
        with pytest.raises(ConfigurationError) as exc_info:
            Config.load()
        
        error_msg = str(exc_info.value)
        assert "REVIEW_MODELS" in error_msg
        assert "maximum of 10 models" in error_msg
    
    def test_validate_valid_review_models_config(self, monkeypatch):
        """Test validation passes with valid review models configuration."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("REVIEW_MODELS", "phi4,mistral-nemo,llama3.2")
        monkeypatch.setenv("REVIEW_MODEL_FRAMEWORK", "ollama")
        
        # Should not raise exception
        config = Config.load()
        assert config.review_models == ["phi4", "mistral-nemo", "llama3.2"]
        assert config.review_model_framework == "ollama"


class TestConfigurationValidationAndReporting:
    """Tests for configuration validation and reporting functionality."""
    
    @patch('requests.get')
    def test_validate_model_availability_ollama_service_running(self, mock_get, monkeypatch):
        """Test model availability validation when Ollama service is running."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("AI_PROVIDER", "local")
        monkeypatch.setenv("LOCAL_MODEL_NAME", "phi4")
        monkeypatch.setenv("REVIEW_MODELS", "phi4,mistral-nemo")
        
        # Mock successful Ollama API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "phi4:latest"},
                {"name": "mistral-nemo:latest"}
            ]
        }
        mock_get.return_value = mock_response
        
        config = Config.load()
        issues = config.validate_model_availability()
        
        # Should have no issues since all models are available
        assert len(issues) == 0
    
    @patch('requests.get')
    def test_validate_model_availability_missing_model(self, mock_get, monkeypatch):
        """Test model availability validation when a model is missing."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("AI_PROVIDER", "local")
        monkeypatch.setenv("LOCAL_MODEL_NAME", "phi4")
        monkeypatch.setenv("REVIEW_MODELS", "phi4,missing-model")
        
        # Mock Ollama API response with only one model
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "phi4:latest"}
            ]
        }
        mock_get.return_value = mock_response
        
        config = Config.load()
        issues = config.validate_model_availability()
        
        # Should have issue about missing model
        assert len(issues) > 0
        assert any("missing-model" in issue for issue in issues)
        assert any("not found in Ollama" in issue for issue in issues)
    
    @patch('requests.get')
    def test_validate_model_availability_ollama_service_down(self, mock_get, monkeypatch):
        """Test model availability validation when Ollama service is down."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("AI_PROVIDER", "local")
        monkeypatch.setenv("LOCAL_MODEL_NAME", "phi4")
        
        # Mock connection error
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("Connection refused")
        
        config = Config.load()
        issues = config.validate_model_availability()
        
        # Should have issue about service not running
        assert len(issues) > 0
        assert any("service not running" in issue.lower() or "not accessible" in issue.lower() for issue in issues)
    
    def test_validate_model_availability_fallback_api_key_missing(self, monkeypatch, tmp_path):
        """Test validation detects missing API key when fallback is enabled."""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("AI_PROVIDER", "local")
        monkeypatch.setenv("ENABLE_FALLBACK", "true")
        
        # Use non-existent env file to avoid loading project .env
        non_existent_env = tmp_path / "nonexistent.env"
        
        # This should fail basic validation first, so we need to catch that
        with pytest.raises(ConfigurationError):
            Config.load(env_file=str(non_existent_env))
        
        # Test the model availability validation separately
        # Create a config that passes basic validation but has fallback issues
        monkeypatch.setenv("GEMINI_API_KEY", "")  # Empty but present
        config = Config(
            gemini_api_key="",
            ai_provider="local",
            enable_fallback=True,
            local_model_name="phi4"
        )
        
        issues = config.validate_model_availability()
        
        # Should have issue about missing API key for fallback
        assert len(issues) > 0
        assert any("GEMINI_API_KEY" in issue and "fallback" in issue for issue in issues)
    
    def test_get_configuration_status_basic(self, monkeypatch):
        """Test basic configuration status reporting."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("AI_PROVIDER", "local")
        monkeypatch.setenv("LOCAL_MODEL_NAME", "phi4")
        monkeypatch.setenv("LOCAL_MODEL_FRAMEWORK", "auto")  # Explicitly set to auto
        monkeypatch.setenv("REVIEW_MODELS", "phi4,mistral-nemo")
        monkeypatch.setenv("ENABLE_FALLBACK", "true")
        
        config = Config.load()
        status = config.get_configuration_status()
        
        # Check basic structure
        assert "configuration_valid" in status
        assert "validation_errors" in status
        assert "validation_warnings" in status
        assert "ai_providers" in status
        assert "model_configuration" in status
        assert "performance_settings" in status
        assert "feature_flags" in status
        assert "backward_compatibility" in status
        
        # Check AI provider configuration
        ai_providers = status["ai_providers"]
        assert ai_providers["primary_provider"] == "local"
        assert ai_providers["fallback_enabled"] is True
        assert ai_providers["local_model"]["name"] == "phi4"
        assert ai_providers["local_model"]["framework"] == "auto"
        assert ai_providers["gemini_configured"] is True
        
        # Check model configuration
        model_config = status["model_configuration"]
        assert model_config["review_models"]["enabled"] is True
        assert model_config["review_models"]["count"] == 2
        assert model_config["review_models"]["models"] == ["phi4", "mistral-nemo"]
    
    def test_get_configuration_status_legacy_config(self, monkeypatch):
        """Test configuration status with legacy single-model configuration."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("AI_PROVIDER", "local")
        monkeypatch.setenv("LOCAL_MODEL_NAME", "phi4")
        monkeypatch.setenv("REVIEW_PASSES", "1")  # Explicitly set to 1 for legacy
        # No REVIEW_MODELS set - legacy configuration
        
        config = Config.load()
        status = config.get_configuration_status()
        
        # Check backward compatibility analysis
        compat = status["backward_compatibility"]
        assert compat["legacy_config_detected"] is True
        assert any("legacy single-model configuration" in note for note in compat["compatibility_notes"])
    
    def test_analyze_backward_compatibility_deprecated_framework(self, monkeypatch):
        """Test backward compatibility analysis detects deprecated settings."""
        # Create config manually to test compatibility analysis
        config = Config(
            gemini_api_key="test_key",
            ai_provider="local",
            local_model_framework="transformers"  # Deprecated
        )
        
        compat = config._analyze_backward_compatibility()
        assert compat["migration_needed"] is True
        assert any("DEPRECATED" in note for note in compat["compatibility_notes"])
        assert any("transformers framework" in note for note in compat["compatibility_notes"])
    
    def test_print_configuration_status(self, monkeypatch, capsys):
        """Test configuration status printing."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_key")
        monkeypatch.setenv("AI_PROVIDER", "local")
        monkeypatch.setenv("LOCAL_MODEL_NAME", "phi4")
        monkeypatch.setenv("REVIEW_MODELS", "phi4,mistral-nemo")
        
        config = Config.load()
        config.print_configuration_status()
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Check that key sections are present
        assert "Configuration Status Report" in output
        assert "AI Provider Configuration" in output
        assert "Model Configuration" in output
        assert "Performance Settings" in output
        assert "Feature Flags" in output
        
        # Check specific values
        assert "Primary: local" in output
        assert "phi4" in output
        assert "mistral-nemo" in output
