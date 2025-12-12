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
    
    def get_provider_info(self):
        return {"name": self.name, "type": "mock"}


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
        assert config.timeout == 300
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
            "local_model_framework": "auto"
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