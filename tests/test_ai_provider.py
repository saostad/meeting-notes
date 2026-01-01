"""Unit tests for AI provider system."""

import pytest
from unittest.mock import Mock, patch
from src.ai_provider import BaseAIProvider, AIProviderManager, ProviderConfig, AnalysisResult
from src.config import Config
from src.chapter import Chapter
from src.transcript import Transcript, TranscriptSegment
from src.errors import ProcessingError, DependencyError


class MockProvider(BaseAIProvider):
    """Mock AI provider for testing."""
    
    def __init__(self, name: str, available: bool = True, should_fail: bool = False):
        self.name = name
        self.available = available
        self.should_fail = should_fail
    
    def is_available(self) -> bool:
        return self.available
    
    def analyze_transcript(self, transcript, save_raw_response=None, save_notes=None):
        if self.should_fail:
            raise Exception(f"{self.name} provider failed")
        
        # Return mock chapters and notes
        chapters = [
            Chapter(timestamp=0.0, title="Introduction"),
            Chapter(timestamp=60.0, title="Main Discussion")
        ]
        notes = [{"details": "Test note from " + self.name}]
        return chapters, notes
    
    def review_analysis(self, original_result, transcript, save_raw_response=None):
        if self.should_fail:
            raise Exception(f"{self.name} provider failed")
        
        # Return mock reviewed chapters and notes
        chapters = [
            Chapter(timestamp=0.0, title="Introduction (Reviewed)"),
            Chapter(timestamp=60.0, title="Main Discussion (Reviewed)")
        ]
        notes = [{"details": "Reviewed note from " + self.name}]
        return chapters, notes
    
    def get_provider_info(self):
        return {"name": self.name, "type": "mock", "model": self.name}


class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""
    
    def test_provider_config_defaults(self):
        """Test ProviderConfig default values."""
        config = ProviderConfig(
            provider_type="test",
            model_name="test-model"
        )
        
        assert config.provider_type == "test"
        assert config.model_name == "test-model"
        assert config.parameters == {}
        assert config.timeout == 600
        assert config.max_retries == 2
    
    def test_provider_config_custom_values(self):
        """Test ProviderConfig with custom values."""
        config = ProviderConfig(
            provider_type="ollama",
            model_name="phi4",
            parameters={"temperature": 0.7},
            timeout=600,
            max_retries=5
        )
        
        assert config.provider_type == "ollama"
        assert config.model_name == "phi4"
        assert config.parameters == {"temperature": 0.7}
        assert config.timeout == 600
        assert config.max_retries == 5


class TestAnalysisResult:
    """Tests for AnalysisResult dataclass."""
    
    def test_analysis_result_creation(self):
        """Test AnalysisResult creation."""
        chapters = [Chapter(timestamp=0.0, title="Test")]
        notes = [{"details": "Test note"}]
        
        result = AnalysisResult(
            chapters=chapters,
            notes=notes,
            provider_used="test",
            processing_time=1.5
        )
        
        assert result.chapters == chapters
        assert result.notes == notes
        assert result.provider_used == "test"
        assert result.processing_time == 1.5
        assert result.confidence_score is None
        assert result.warnings == []


class TestAIProviderManager:
    """Tests for AIProviderManager."""
    
    def create_test_config(self, **kwargs):
        """Create a test configuration with defaults."""
        defaults = {
            "gemini_api_key": "test_key",
            "ai_provider": "local",
            "enable_fallback": False,
            "local_model_name": "phi4",
            "local_model_framework": "auto",
            "review_models": None,
            "review_model_framework": "ollama",
            "review_passes": 1,
            "enable_review": False,
            "ollama_base_url": "http://localhost:11434",
            "analysis_timeout": 600,
            "model_parameters": None
        }
        defaults.update(kwargs)
        
        # Create a mock config object
        config = Mock(spec=Config)
        for key, value in defaults.items():
            setattr(config, key, value)
        
        return config
    
    def create_test_transcript(self):
        """Create a test transcript."""
        segments = [
            TranscriptSegment(start_time=0.0, end_time=30.0, text="Hello everyone"),
            TranscriptSegment(start_time=30.0, end_time=60.0, text="Let's discuss the project")
        ]
        full_text = "Hello everyone Let's discuss the project"
        duration = 60.0
        return Transcript(segments=segments, full_text=full_text, duration=duration)
    
    @patch('src.ai_provider.AIProviderManager._create_local_provider')
    @patch('src.ai_provider.AIProviderManager._create_gemini_provider')
    def test_initialization_local_provider(self, mock_gemini, mock_local):
        """Test AIProviderManager initialization with local provider."""
        config = self.create_test_config(ai_provider="local", enable_fallback=False)
        mock_local.return_value = MockProvider("local")
        mock_gemini.return_value = None
        
        manager = AIProviderManager(config)
        
        assert mock_local.called
        assert not mock_gemini.called
        assert manager.primary_provider is not None
        assert manager.fallback_provider is None
    
    @patch('src.ai_provider.AIProviderManager._create_local_provider')
    @patch('src.ai_provider.AIProviderManager._create_gemini_provider')
    def test_initialization_with_fallback(self, mock_gemini, mock_local):
        """Test AIProviderManager initialization with fallback enabled."""
        config = self.create_test_config(ai_provider="local", enable_fallback=True)
        mock_local.return_value = MockProvider("local")
        mock_gemini.return_value = MockProvider("gemini")
        
        manager = AIProviderManager(config)
        
        assert mock_local.called
        assert mock_gemini.called
        assert manager.primary_provider is not None
        assert manager.fallback_provider is not None
    
    @patch('src.ai_provider.AIProviderManager._create_local_provider')
    @patch('src.ai_provider.AIProviderManager._create_gemini_provider')
    def test_initialization_gemini_provider(self, mock_gemini, mock_local):
        """Test AIProviderManager initialization with Gemini provider."""
        config = self.create_test_config(ai_provider="gemini", enable_fallback=False)
        mock_local.return_value = None
        mock_gemini.return_value = MockProvider("gemini")
        
        manager = AIProviderManager(config)
        
        assert not mock_local.called
        assert mock_gemini.called
        assert manager.primary_provider is not None
        assert manager.fallback_provider is None
    
    def test_analyze_transcript_success(self):
        """Test successful transcript analysis."""
        config = self.create_test_config()
        manager = AIProviderManager(config)
        
        # Mock the primary provider
        manager.primary_provider = MockProvider("test", available=True)
        
        transcript = self.create_test_transcript()
        chapters, notes = manager.analyze_transcript(transcript)
        
        assert len(chapters) == 2
        assert chapters[0].title == "Introduction"
        assert len(notes) == 1
        assert "Test note from test" in notes[0]["details"]
    
    def test_analyze_transcript_fallback(self):
        """Test transcript analysis with fallback."""
        config = self.create_test_config(enable_fallback=True)
        manager = AIProviderManager(config)
        
        # Mock providers - primary fails, fallback succeeds
        manager.primary_provider = MockProvider("primary", available=True, should_fail=True)
        manager.fallback_provider = MockProvider("fallback", available=True)
        
        transcript = self.create_test_transcript()
        chapters, notes = manager.analyze_transcript(transcript)
        
        assert len(chapters) == 2
        assert "Test note from fallback" in notes[0]["details"]
    
    def test_analyze_transcript_no_providers(self):
        """Test transcript analysis when no providers are available."""
        config = self.create_test_config()
        manager = AIProviderManager(config)
        
        # No providers available
        manager.primary_provider = None
        manager.fallback_provider = None
        
        transcript = self.create_test_transcript()
        
        with pytest.raises(DependencyError) as exc_info:
            manager.analyze_transcript(transcript)
        
        assert "Primary AI provider failed and fallback is disabled" in str(exc_info.value)
    
    def test_analyze_transcript_all_providers_fail(self):
        """Test transcript analysis when all providers fail."""
        config = self.create_test_config(enable_fallback=True)
        manager = AIProviderManager(config)
        
        # Both providers fail
        manager.primary_provider = MockProvider("primary", available=True, should_fail=True)
        manager.fallback_provider = MockProvider("fallback", available=True, should_fail=True)
        
        transcript = self.create_test_transcript()
        
        with pytest.raises(ProcessingError) as exc_info:
            manager.analyze_transcript(transcript)
        
        assert "Both primary and fallback providers failed" in str(exc_info.value)
    
    def test_get_available_providers(self):
        """Test getting list of available providers."""
        config = self.create_test_config()
        manager = AIProviderManager(config)
        
        # Mock providers
        manager.primary_provider = MockProvider("primary", available=True)
        manager.fallback_provider = MockProvider("fallback", available=True)
        
        available = manager.get_available_providers()
        
        assert "primary" in available
        assert "fallback" in available
        assert len(available) == 2
    
    def test_get_available_providers_unavailable(self):
        """Test getting list when providers are unavailable."""
        config = self.create_test_config()
        manager = AIProviderManager(config)
        
        # Mock unavailable providers
        manager.primary_provider = MockProvider("primary", available=False)
        manager.fallback_provider = MockProvider("fallback", available=False)
        
        available = manager.get_available_providers()
        
        assert len(available) == 0
    
    def test_get_review_provider_no_review_models(self):
        """Test get_review_provider when no review models are configured."""
        config = self.create_test_config()
        manager = AIProviderManager(config)
        
        # Mock primary provider
        manager.primary_provider = MockProvider("primary", available=True)
        
        provider = manager.get_review_provider(1)
        
        assert provider.name == "primary"
    
    def test_get_review_provider_with_review_models(self):
        """Test get_review_provider with configured review models."""
        config = self.create_test_config(
            review_models=["phi4", "mistral-nemo", "llama3"],
            review_passes=3
        )
        manager = AIProviderManager(config)
        
        # Mock review providers
        manager.review_providers = [
            MockProvider("phi4", available=True),
            MockProvider("mistral-nemo", available=True),
            MockProvider("llama3", available=True)
        ]
        
        # Test sequential selection
        provider1 = manager.get_review_provider(1)
        provider2 = manager.get_review_provider(2)
        provider3 = manager.get_review_provider(3)
        
        assert provider1.name == "phi4"
        assert provider2.name == "mistral-nemo"
        assert provider3.name == "llama3"
    
    def test_get_review_provider_cycling(self):
        """Test get_review_provider cycles through models when more passes than models."""
        config = self.create_test_config(
            review_models=["phi4", "mistral-nemo"],
            review_passes=4
        )
        manager = AIProviderManager(config)
        
        # Mock review providers
        manager.review_providers = [
            MockProvider("phi4", available=True),
            MockProvider("mistral-nemo", available=True)
        ]
        
        # Test cycling behavior
        provider1 = manager.get_review_provider(1)
        provider2 = manager.get_review_provider(2)
        provider3 = manager.get_review_provider(3)  # Should cycle back to phi4
        provider4 = manager.get_review_provider(4)  # Should cycle to mistral-nemo
        
        assert provider1.name == "phi4"
        assert provider2.name == "mistral-nemo"
        assert provider3.name == "phi4"
        assert provider4.name == "mistral-nemo"
    
    def test_get_review_provider_fallback_within_sequence(self):
        """Test get_review_provider falls back within sequence when target is unavailable."""
        config = self.create_test_config(
            review_models=["phi4", "mistral-nemo", "llama3"],
            review_passes=3
        )
        manager = AIProviderManager(config)
        
        # Mock review providers - middle one unavailable
        manager.review_providers = [
            MockProvider("phi4", available=True),
            MockProvider("mistral-nemo", available=False),  # Unavailable
            MockProvider("llama3", available=True)
        ]
        
        # Test fallback within sequence
        provider1 = manager.get_review_provider(1)
        provider2 = manager.get_review_provider(2)  # Should fall back to available model
        
        assert provider1.name == "phi4"
        assert provider2.name in ["phi4", "llama3"]  # Should be one of the available ones
    
    def test_get_review_provider_fallback_to_primary(self):
        """Test get_review_provider falls back to primary when no review models available."""
        config = self.create_test_config(
            review_models=["phi4", "mistral-nemo"],
            review_passes=2
        )
        manager = AIProviderManager(config)
        
        # Mock review providers - all unavailable
        manager.review_providers = [
            MockProvider("phi4", available=False),
            MockProvider("mistral-nemo", available=False)
        ]
        
        # Mock primary provider as available
        manager.primary_provider = MockProvider("primary", available=True)
        
        provider = manager.get_review_provider(1)
        
        assert provider.name == "primary"
    
    def test_get_review_provider_no_available_providers(self):
        """Test get_review_provider raises error when no providers available."""
        config = self.create_test_config(
            review_models=["phi4"],
            review_passes=1
        )
        manager = AIProviderManager(config)
        
        # Mock all providers as unavailable
        manager.review_providers = [MockProvider("phi4", available=False)]
        manager.primary_provider = MockProvider("primary", available=False)
        manager.fallback_provider = MockProvider("fallback", available=False)
        
        with pytest.raises(RuntimeError) as exc_info:
            manager.get_review_provider(1)
        
        assert "No available providers for review pass 1" in str(exc_info.value)
    
    def test_get_review_provider_invalid_pass_number(self):
        """Test get_review_provider raises error for invalid pass number."""
        config = self.create_test_config()
        manager = AIProviderManager(config)
        
        with pytest.raises(ValueError) as exc_info:
            manager.get_review_provider(0)
        
        assert "Pass number must be at least 1" in str(exc_info.value)
    
    @patch('src.ai_provider.AIProviderManager._try_create_ollama_provider_for_model')
    def test_initialize_review_providers(self, mock_create_provider):
        """Test initialization of review providers."""
        config = self.create_test_config(
            review_models=["phi4", "mistral-nemo"],
            review_model_framework="ollama"
        )
        
        # Mock provider creation
        mock_create_provider.side_effect = [
            MockProvider("phi4", available=True),
            MockProvider("mistral-nemo", available=True)
        ]
        
        manager = AIProviderManager(config)
        
        assert len(manager.review_providers) == 2
        assert mock_create_provider.call_count == 2
        mock_create_provider.assert_any_call("phi4")
        mock_create_provider.assert_any_call("mistral-nemo")
    
    @patch('src.ai_provider.AIProviderManager._try_create_ollama_provider_for_model')
    def test_initialize_review_providers_some_fail(self, mock_create_provider):
        """Test initialization when some review providers fail to initialize."""
        config = self.create_test_config(
            review_models=["phi4", "mistral-nemo", "llama3"],
            review_model_framework="ollama"
        )
        
        # Mock provider creation - middle one fails
        mock_create_provider.side_effect = [
            MockProvider("phi4", available=True),
            None,  # Failed to create
            MockProvider("llama3", available=True)
        ]
        
        manager = AIProviderManager(config)
        
        assert len(manager.review_providers) == 2  # Only successful ones
        assert mock_create_provider.call_count == 3


class TestAIProviderValidationAndReporting:
    """Tests for AI provider validation and reporting functionality."""
    
    def create_test_config(self, **kwargs):
        """Create a test configuration with defaults."""
        defaults = {
            "gemini_api_key": "test_key",
            "ai_provider": "local",
            "enable_fallback": False,
            "local_model_name": "phi4",
            "local_model_framework": "auto",
            "review_models": None,
            "review_model_framework": "ollama",
            "review_passes": 1,
            "enable_review": False,
            "ollama_base_url": "http://localhost:11434",
            "analysis_timeout": 600,
            "model_parameters": None
        }
        defaults.update(kwargs)
        
        # Create a mock config object
        config = Mock(spec=Config)
        for key, value in defaults.items():
            setattr(config, key, value)
        
        # Mock the validate_model_availability method
        config.validate_model_availability.return_value = []
        
        return config
    
    def test_validate_configuration_all_providers_available(self):
        """Test configuration validation when all providers are available."""
        config = self.create_test_config(
            enable_fallback=True,
            review_models=["phi4", "mistral-nemo"]
        )
        manager = AIProviderManager(config)
        
        # Mock all providers as available
        manager.primary_provider = MockProvider("primary", available=True)
        manager.fallback_provider = MockProvider("fallback", available=True)
        manager.review_providers = [
            MockProvider("phi4", available=True),
            MockProvider("mistral-nemo", available=True)
        ]
        
        issues = manager.validate_configuration()
        
        # Should have no issues
        assert len(issues) == 0
    
    def test_validate_configuration_primary_unavailable(self):
        """Test configuration validation when primary provider is unavailable."""
        config = self.create_test_config(enable_fallback=False)
        manager = AIProviderManager(config)
        
        # Mock primary provider as unavailable
        manager.primary_provider = MockProvider("primary", available=False)
        
        issues = manager.validate_configuration()
        
        # Should have issues about primary provider and suggest fallback
        assert len(issues) > 0
        assert any("Primary provider" in issue and "not available" in issue for issue in issues)
        assert any("fallback is disabled" in issue for issue in issues)
    
    def test_validate_configuration_review_models_unavailable(self):
        """Test configuration validation when review models are unavailable."""
        config = self.create_test_config(
            review_models=["phi4", "mistral-nemo", "llama3"],
            review_passes=3
        )
        manager = AIProviderManager(config)
        
        # Mock primary provider as available
        manager.primary_provider = MockProvider("primary", available=True)
        
        # Mock review providers - some unavailable
        manager.review_providers = [
            MockProvider("phi4", available=True),
            MockProvider("mistral-nemo", available=False),
            MockProvider("llama3", available=False)
        ]
        
        issues = manager.validate_configuration()
        
        # Should have issues about unavailable review models
        assert len(issues) > 0
        assert any("review models are unavailable" in issue for issue in issues)
        assert any("mistral-nemo" in issue and "not available" in issue for issue in issues)
        assert any("llama3" in issue and "not available" in issue for issue in issues)
    
    def test_validate_configuration_no_providers_available(self):
        """Test configuration validation when no providers are available."""
        config = self.create_test_config()
        manager = AIProviderManager(config)
        
        # Mock all providers as unavailable
        manager.primary_provider = MockProvider("primary", available=False)
        manager.fallback_provider = None
        manager.review_providers = []
        
        issues = manager.validate_configuration()
        
        # Should have critical issue about no providers available
        assert len(issues) > 0
        assert any("No AI providers are currently available" in issue for issue in issues)
    
    def test_get_configuration_status_comprehensive(self):
        """Test comprehensive configuration status reporting."""
        config = self.create_test_config(
            enable_fallback=True,
            review_models=["phi4", "mistral-nemo"],
            review_passes=2
        )
        manager = AIProviderManager(config)
        
        # Mock providers with mixed availability
        manager.primary_provider = MockProvider("primary", available=True)
        manager.fallback_provider = MockProvider("fallback", available=True)
        manager.review_providers = [
            MockProvider("phi4", available=True),
            MockProvider("mistral-nemo", available=False)
        ]
        
        status = manager.get_configuration_status()
        
        # Check structure
        assert "providers" in status
        assert "availability" in status
        assert "configuration_issues" in status
        assert "recommendations" in status
        
        # Check provider status
        providers = status["providers"]
        assert providers["primary"]["name"] == "primary"
        assert providers["primary"]["available"] is True
        assert providers["fallback"]["name"] == "fallback"
        assert providers["fallback"]["available"] is True
        
        # Check review models status
        review_models = providers["review_models"]
        assert len(review_models) == 2
        assert review_models[0]["name"] == "phi4"
        assert review_models[0]["available"] is True
        assert review_models[1]["name"] == "mistral-nemo"
        assert review_models[1]["available"] is False
        
        # Check availability summary
        availability = status["availability"]
        assert availability["primary_available"] is True
        assert availability["fallback_available"] is True
        assert availability["review_models_available"] == 1
        assert availability["total_available"] == 3  # primary + fallback + 1 review model
    
    def test_generate_configuration_recommendations(self):
        """Test configuration recommendation generation."""
        config = self.create_test_config(
            enable_fallback=False,
            review_models=["phi4", "mistral-nemo"],
            review_passes=2
        )
        manager = AIProviderManager(config)
        
        # Mock primary available, no fallback, mixed review models
        manager.primary_provider = MockProvider("primary", available=True)
        manager.fallback_provider = None
        manager.review_providers = [
            MockProvider("phi4", available=True),
            MockProvider("mistral-nemo", available=False)
        ]
        
        status = manager.get_configuration_status()
        recommendations = status["recommendations"]
        
        # Should recommend enabling fallback and fixing review models
        assert len(recommendations) > 0
        assert any("fallback" in rec.lower() for rec in recommendations)
        assert any("missing review models" in rec or "models are unavailable" in rec for rec in recommendations)
    
    def test_print_configuration_status(self, capsys):
        """Test configuration status printing."""
        config = self.create_test_config(
            enable_fallback=True,
            review_models=["phi4", "mistral-nemo"]
        )
        manager = AIProviderManager(config)
        
        # Mock providers
        manager.primary_provider = MockProvider("primary", available=True)
        manager.fallback_provider = MockProvider("fallback", available=True)
        manager.review_providers = [
            MockProvider("phi4", available=True),
            MockProvider("mistral-nemo", available=False)
        ]
        
        manager.print_configuration_status()
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Check that key sections are present
        assert "AI Provider Status Report" in output
        assert "Primary:" in output
        assert "Fallback:" in output
        assert "Review Models:" in output
        assert "Total Available Providers:" in output
        
        # Check specific status indicators
        assert "✅" in output  # Available providers
        assert "❌" in output  # Unavailable providers
        assert "phi4" in output
        assert "mistral-nemo" in output