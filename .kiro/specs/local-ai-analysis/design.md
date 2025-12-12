# Design Document

## Overview

This design document outlines the enhancement of the Meeting Video Chapter Tool to support local open source AI models (primarily Phi4) for transcript analysis, with Google Gemini API as a fallback option. The enhancement introduces a flexible AI provider system that allows users to process their meeting transcripts locally for improved privacy and reduced dependency on external APIs.

The system will implement a provider pattern with optional user-controlled fallback capabilities, supporting multiple local AI frameworks (Ollama, Hugging Face Transformers) while maintaining compatibility with the existing Gemini API integration.

## Architecture

### High-Level Architecture

The enhanced system introduces an AI Provider abstraction layer that sits between the existing ChapterAnalyzer and the actual AI services. This layer manages provider selection, fallback logic, and output normalization.

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Pipeline      │───▶│ ChapterAnalyzer  │───▶│ AI Provider     │
│                 │    │                  │    │ Manager         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                              ┌─────────────────────────────────────┐
                              │         Provider Selection          │
                              │                                     │
                              │  ┌─────────────┐  ┌─────────────┐  │
                              │  │   Primary   │  │  Fallback   │  │
                              │  │  Provider   │  │  Provider   │  │
                              │  └─────────────┘  └─────────────┘  │
                              └─────────────────────────────────────┘
                                         │
                                         ▼
                    ┌──────────────────────────────────────────────┐
                    │              AI Providers                    │
                    │                                              │
                    │ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
                    │ │   Ollama    │ │ Transformers│ │ Gemini  │ │
                    │ │  Provider   │ │  Provider   │ │Provider │ │
                    │ └─────────────┘ └─────────────┘ └─────────┘ │
                    └──────────────────────────────────────────────┘
```

### Provider System Design

The AI Provider system consists of:

1. **AIProviderManager**: Orchestrates provider selection and fallback logic
2. **BaseAIProvider**: Abstract base class defining the provider interface
3. **Concrete Providers**: Implementations for Ollama, Transformers, and Gemini
4. **ProviderConfig**: Configuration management for each provider type
5. **OutputNormalizer**: Ensures consistent output format across providers

## Components and Interfaces

### AIProviderManager

The central component that manages AI provider selection and execution:

```python
class AIProviderManager:
    def __init__(self, config: Config):
        self.primary_provider: BaseAIProvider
        self.fallback_provider: Optional[BaseAIProvider]
        self.config = config
    
    def analyze_transcript(self, transcript: Transcript) -> Tuple[List[Chapter], List]:
        # Try primary provider first, fallback on failure
        pass
    
    def _create_provider(self, provider_type: str) -> BaseAIProvider:
        # Factory method for creating providers
        pass
```

### BaseAIProvider

Abstract interface that all AI providers must implement:

```python
from abc import ABC, abstractmethod

class BaseAIProvider(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and functional"""
        pass
    
    @abstractmethod
    def analyze_transcript(self, transcript: Transcript) -> Tuple[List[Chapter], List]:
        """Analyze transcript and return chapters and notes"""
        pass
    
    @abstractmethod
    def get_provider_info(self) -> Dict[str, Any]:
        """Return provider information for logging"""
        pass
```

### OllamaProvider

Implements local AI analysis using Ollama:

```python
class OllamaProvider(BaseAIProvider):
    def __init__(self, model_name: str = "phi4", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.client = None
    
    def is_available(self) -> bool:
        # Check if Ollama is running and model is available
        pass
    
    def analyze_transcript(self, transcript: Transcript) -> Tuple[List[Chapter], List]:
        # Use Ollama API for analysis
        pass
```

### TransformersProvider

Implements local AI analysis using Hugging Face Transformers:

```python
class TransformersProvider(BaseAIProvider):
    def __init__(self, model_name: str = "microsoft/Phi-3.5-mini-instruct", device: str = "auto"):
        self.model_name = model_name
        self.device = device
        self.model = None
        self.tokenizer = None
    
    def is_available(self) -> bool:
        # Check if transformers is installed and model can be loaded
        pass
    
    def analyze_transcript(self, transcript: Transcript) -> Tuple[List[Chapter], List]:
        # Use transformers pipeline for analysis
        pass
```

### GeminiProvider

Wraps the existing Gemini API functionality:

```python
class GeminiProvider(BaseAIProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-flash-latest"):
        self.api_key = api_key
        self.model_name = model_name
    
    def is_available(self) -> bool:
        # Check if API key is valid and service is reachable
        pass
    
    def analyze_transcript(self, transcript: Transcript) -> Tuple[List[Chapter], List]:
        # Use existing ChapterAnalyzer logic
        pass
```

## Data Models

### ProviderConfig

Configuration structure for AI providers:

```python
@dataclass
class ProviderConfig:
    provider_type: str  # "ollama", "transformers", "gemini"
    model_name: str
    parameters: Dict[str, Any]  # Provider-specific parameters
    timeout: int = 300  # Timeout in seconds
    max_retries: int = 2
```

### AnalysisResult

Standardized result format from AI providers:

```python
@dataclass
class AnalysisResult:
    chapters: List[Chapter]
    notes: List[Dict[str, Any]]
    provider_used: str
    processing_time: float
    confidence_score: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
```

### Enhanced Config

Extended configuration to support multiple AI providers:

```python
@dataclass
class Config:
    # Existing fields...
    gemini_api_key: str
    whisper_model: str = "openai/whisper-large-v3-turbo"
    gemini_model: str = "gemini-flash-latest"
    
    # New AI provider fields
    ai_provider: str = "local"  # "local", "gemini"
    enable_fallback: bool = False  # Whether to use Gemini as fallback
    local_model_name: str = "phi4"
    local_model_framework: str = "auto"  # "ollama", "transformers", "auto"
    
    # Provider-specific settings
    ollama_base_url: str = "http://localhost:11434"
    transformers_device: str = "auto"
    model_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Performance settings
    analysis_timeout: int = 300
    max_memory_usage: Optional[int] = None  # MB
    use_gpu: bool = True
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Local Provider Usage
*For any* transcript and local AI configuration, when the local model is available and configured as primary, the system should use the local model for analysis without making external API calls
**Validates: Requirements 1.1, 1.2**

### Property 2: Model Loading Consistency
*For any* specified model name and framework, when a user configures a specific local model, the system should load and use exactly that model for analysis
**Validates: Requirements 1.3, 4.1**

### Property 3: Output Format Consistency
*For any* transcript processed by different providers, the output format (chapters and notes structure) should be identical regardless of which AI provider was used
**Validates: Requirements 1.4, 7.1**

### Property 4: Conditional Fallback Activation
*For any* local provider failure scenario when fallback is enabled, the system should switch to the Gemini API fallback provider
**Validates: Requirements 2.1, 2.3**

### Property 5: Fallback Logging
*For any* fallback activation, the system should log the specific reason for the fallback and which provider was used as replacement
**Validates: Requirements 2.4, 6.2**

### Property 6: Configuration-Driven Provider Selection
*For any* valid provider configuration, the system should use the provider specified in the AI_PROVIDER environment variable as the primary analysis method
**Validates: Requirements 3.1, 3.2**

### Property 7: Default Configuration Behavior
*For any* system startup without explicit provider configuration, the system should default to local model as primary with fallback disabled
**Validates: Requirements 3.3**

### Property 8: Parameter Application
*For any* configured model parameters (temperature, max_tokens, etc.), the system should apply these exact parameters during model inference
**Validates: Requirements 4.2**

### Property 9: Framework Support Detection
*For any* available AI framework (Ollama, Transformers), when the framework is installed and functional, the system should be able to use it for local model analysis
**Validates: Requirements 5.1, 5.2**

### Property 10: Framework Selection Logic
*For any* system with multiple available frameworks, the system should use the framework specified in configuration or follow the default preference order
**Validates: Requirements 5.3**

### Property 11: Provider Reporting
*For any* analysis session, the system should report which AI provider is being used at the start and which provider successfully completed the analysis
**Validates: Requirements 6.1, 6.3**

### Property 12: Functional Equivalence
*For any* transcript, the types and quality of extracted chapters and actionable notes should be equivalent between local AI models and Gemini API
**Validates: Requirements 7.2**

### Property 13: Output Normalization
*For any* AI provider output that differs from the standard format, the system should normalize it to match the expected chapter and notes structure
**Validates: Requirements 7.4**

### Property 14: Resource Constraint Handling
*For any* system with insufficient resources for the selected model, the system should report specific resource requirements and suggest appropriate alternatives
**Validates: Requirements 8.1**

### Property 15: GPU Utilization
*For any* system with available GPU acceleration, the system should utilize GPU resources to improve local model processing performance
**Validates: Requirements 8.3**

## Error Handling

### Provider Initialization Errors

The system must handle various provider initialization failures gracefully:

1. **Missing Dependencies**: When required libraries (ollama, transformers) are not installed
2. **Model Loading Failures**: When specified models cannot be loaded due to memory constraints or corruption
3. **Network Connectivity**: When Ollama service is not running or unreachable
4. **Invalid Configuration**: When model names, paths, or parameters are invalid

Error handling strategy:
- Immediate validation of provider availability during initialization
- Graceful degradation to fallback providers
- Clear error messages with actionable suggestions
- Logging of all error conditions for debugging

### Runtime Processing Errors

During transcript analysis, the system must handle:

1. **Model Inference Failures**: Crashes, timeouts, or memory exhaustion during processing
2. **Output Parsing Errors**: Invalid JSON or unexpected response formats
3. **Resource Exhaustion**: Running out of memory or disk space during processing
4. **API Rate Limits**: When fallback to external APIs hits rate limits

Error recovery mechanisms:
- Automatic retry with exponential backoff for transient failures
- Provider switching for persistent failures
- Resource monitoring and throttling
- Comprehensive error reporting with context

### Configuration Validation

The system validates configuration at startup:

```python
class ConfigValidator:
    def validate_provider_config(self, config: Config) -> List[str]:
        errors = []
        
        # Validate provider types
        if config.ai_provider not in ["local", "gemini", "auto"]:
            errors.append(f"Invalid AI provider: {config.ai_provider}")
        
        # Validate model availability
        if config.ai_provider == "local":
            if not self._check_local_model_availability(config.local_model_name):
                errors.append(f"Local model not available: {config.local_model_name}")
        
        # Validate API keys for fallback
        if config.fallback_provider == "gemini" and not config.gemini_api_key:
            errors.append("Gemini API key required for fallback provider")
        
        return errors
```

## Testing Strategy

### Dual Testing Approach

The system requires both unit testing and property-based testing approaches:

- **Unit tests** verify specific examples, edge cases, and error conditions
- **Property tests** verify universal properties that should hold across all inputs
- Together they provide comprehensive coverage: unit tests catch concrete bugs, property tests verify general correctness

### Unit Testing Requirements

Unit tests will cover:
- Provider initialization and availability checking
- Configuration validation and error handling
- Output parsing and normalization
- Fallback logic activation
- Resource constraint handling
- Integration points between components

### Property-Based Testing Requirements

The system will use **Hypothesis** as the property-based testing library for Python. Each property-based test will run a minimum of 100 iterations to ensure thorough coverage of the random input space.

Property-based tests will be tagged with comments explicitly referencing the correctness property in the design document using this format: '**Feature: local-ai-analysis, Property {number}: {property_text}**'

Each correctness property will be implemented by a single property-based test that:
- Generates random but valid inputs (transcripts, configurations, provider states)
- Exercises the system behavior described in the property
- Verifies the expected outcomes hold across all generated inputs

### Test Environment Setup

Testing will require:
- Mock implementations of AI providers for controlled testing
- Docker containers for Ollama testing
- GPU/CPU testing environments for performance validation
- Network isolation for testing external API fallback behavior

### Integration Testing

Integration tests will verify:
- End-to-end processing with different provider combinations
- Provider switching scenarios under various failure conditions
- Performance characteristics across different hardware configurations
- Compatibility with existing pipeline components

### Performance Testing

Performance tests will validate:
- Memory usage stays within configured limits
- Processing time improvements with GPU acceleration
- Throughput comparison between local and external providers
- Resource cleanup after processing completion

The testing strategy ensures that the enhanced system maintains reliability while adding significant new functionality for local AI processing.