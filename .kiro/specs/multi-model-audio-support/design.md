# Design Document: Multi-Model Audio Support

## Overview

This design extends the Meeting Video Chapter Tool with two key enhancements: sequential multi-model support for review passes and direct audio file processing. The implementation maintains backward compatibility while adding flexible model configuration and expanded input format support.

The design leverages the existing AI provider architecture, extending the configuration system to support model sequences and modifying the pipeline to handle audio inputs directly.

## Architecture

### Current Architecture
The system currently follows this flow:
```
MKV Input → Audio Extraction → Transcription → Chapter Analysis → Chapter Merging → Chaptered MKV
```

### Enhanced Architecture
The enhanced system supports multiple input types and model sequences:
```
Audio/Video Input → [Audio Extraction] → Transcription → Multi-Model Chapter Analysis → Output Generation
```

Key architectural changes:
- **Input Detection**: Determine file type and skip audio extraction for audio files
- **Model Sequencing**: Use different models for each review pass in configured order
- **Output Adaptation**: Generate appropriate outputs based on input type

## Components and Interfaces

### 1. Enhanced Configuration System

#### MultiModelConfig Class
```python
@dataclass
class MultiModelConfig:
    """Configuration for sequential multi-model usage."""
    models: List[str]  # Ordered list of model names
    framework: str = "ollama"  # Framework for all models
    base_url: str = "http://localhost:11434"
    fallback_enabled: bool = True
    
    def get_model_for_pass(self, pass_number: int) -> str:
        """Get model name for specific review pass (1-indexed)."""
        if not self.models:
            raise ValueError("No models configured")
        # Cycle through models if more passes than models
        return self.models[(pass_number - 1) % len(self.models)]
```

#### Enhanced Config Class
```python
# New fields added to existing Config class:
review_models: Optional[List[str]] = None  # Sequential model list
review_model_framework: str = "ollama"     # Framework for review models

# Configuration parsing logic:
def _parse_review_models(self, env_value: str) -> List[str]:
    """Parse comma-separated model list from environment."""
    if not env_value:
        return []
    return [model.strip() for model in env_value.split(',') if model.strip()]
```

### 2. Enhanced AI Provider Manager

#### Sequential Model Selection
```python
class AIProviderManager:
    def __init__(self, config):
        self.config = config
        self.review_models = self._initialize_review_models()
    
    def _initialize_review_models(self) -> List[BaseAIProvider]:
        """Initialize providers for each review model."""
        providers = []
        for model_name in self.config.review_models or []:
            provider = self._create_model_provider(model_name)
            if provider:
                providers.append(provider)
        return providers
    
    def get_review_provider(self, pass_number: int) -> BaseAIProvider:
        """Get provider for specific review pass."""
        if not self.review_models:
            # Fall back to primary provider
            return self.primary_provider
        
        # Cycle through available review models
        provider_index = (pass_number - 1) % len(self.review_models)
        return self.review_models[provider_index]
```

### 3. Input File Detection and Processing

#### FileTypeDetector Class
```python
class FileTypeDetector:
    """Detects and validates input file types."""
    
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg'}
    VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov'}
    
    @classmethod
    def detect_file_type(cls, file_path: str) -> str:
        """Detect if file is audio or video."""
        suffix = Path(file_path).suffix.lower()
        if suffix in cls.AUDIO_EXTENSIONS:
            return 'audio'
        elif suffix in cls.VIDEO_EXTENSIONS:
            return 'video'
        else:
            raise ValidationError(f"Unsupported file type: {suffix}")
    
    @classmethod
    def validate_audio_file(cls, file_path: str) -> bool:
        """Validate audio file has required properties."""
        # Use ffprobe to validate audio file
        # Similar to existing MKV validation logic
        pass
```

### 4. Enhanced Pipeline

#### Modified Pipeline Flow
```python
def run_pipeline(input_path: str, config: Config, progress_callback=None) -> PipelineResult:
    """Enhanced pipeline supporting audio and video inputs."""
    
    # Step 0: File Type Detection
    file_type = FileTypeDetector.detect_file_type(input_path)
    
    # Step 1: Audio Extraction (conditional)
    if file_type == 'video':
        audio_path = extract_audio(input_path)
    else:  # file_type == 'audio'
        audio_path = input_path  # Use audio file directly
    
    # Steps 2-3: Transcription and Analysis (unchanged)
    transcript = transcribe_audio(audio_path)
    chapters, notes = analyze_with_multi_model(transcript, config)
    
    # Step 4: Output Generation (conditional)
    if file_type == 'video':
        output_path = merge_chapters_to_video(input_path, chapters)
    else:  # file_type == 'audio'
        output_path = generate_audio_outputs(audio_path, chapters, transcript)
    
    return result
```

### 5. Multi-Model Review Implementation

#### Enhanced Review Logic
```python
def _perform_review_passes(self, initial_chapters, initial_notes, transcript, 
                          save_raw_response, save_notes):
    """Perform review passes using sequential models."""
    
    current_chapters = initial_chapters
    current_notes = initial_notes
    
    for pass_num in range(2, self.config.review_passes + 1):
        # Get provider for this specific pass
        provider = self.ai_provider_manager.get_review_provider(pass_num)
        
        if not provider or not provider.is_available():
            print(f"⚠️  Model for pass {pass_num} unavailable, skipping")
            continue
        
        provider_info = provider.get_provider_info()
        print(f"📝 Review pass {pass_num}/{self.config.review_passes} using {provider_info['model']}")
        
        # Perform review with selected model
        try:
            reviewed_chapters, reviewed_notes = provider.review_analysis(
                current_result, transcript, review_save_path
            )
            current_chapters = reviewed_chapters
            current_notes = reviewed_notes
        except Exception as e:
            print(f"⚠️  Review pass {pass_num} failed with {provider_info['model']}: {e}")
            # Continue with current results
    
    return current_chapters, current_notes
```

## Data Models

### Enhanced PipelineResult
```python
@dataclass
class PipelineResult:
    # Existing fields...
    
    # New fields for audio support
    input_type: str  # 'audio' or 'video'
    audio_chapters_file: Optional[str] = None  # For audio-only processing
    
    # New fields for multi-model tracking
    models_used: List[str] = field(default_factory=list)  # Track which models were used
    model_pass_mapping: Dict[int, str] = field(default_factory=dict)  # Pass number -> model name
```

### Configuration Extensions
```python
# New environment variables:
REVIEW_MODELS=phi4,mistral-nemo,llama3.2  # Comma-separated model sequence
REVIEW_MODEL_FRAMEWORK=ollama              # Framework for review models
AUDIO_OUTPUT_FORMAT=json                   # Output format for audio files
```

Now I'll use the prework tool to analyze the acceptance criteria before writing correctness properties:

<function_calls>
<invoke name="prework">
<parameter name="featureName">multi-model-audio-support

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Model Sequence Configuration Parsing
*For any* valid comma-separated model list in the .env file, parsing should produce an ordered list of model names that preserves the original sequence and validates each model name.
**Validates: Requirements 1.1**

### Property 2: Sequential Model Selection for Review Passes
*For any* configured model sequence and review pass number N, the system should select the Nth model from the sequence, cycling back to the first model when N exceeds the sequence length.
**Validates: Requirements 1.2, 1.3**

### Property 3: Model Fallback Within Sequence
*For any* model sequence where some models are unavailable, the system should skip unavailable models and use the next available model in the sequence, maintaining the sequential order.
**Validates: Requirements 1.4, 3.5**

### Property 4: Ultimate Fallback Behavior
*For any* configuration where all models in the review sequence are unavailable, the system should fall back to the primary configured model or external API.
**Validates: Requirements 1.5**

### Property 5: Audio File Pipeline Flow
*For any* valid audio file input, the system should skip audio extraction and proceed directly to transcription, then continue with the standard analysis pipeline.
**Validates: Requirements 2.1, 2.2**

### Property 6: Audio-Specific Output Generation
*For any* audio file input, the system should generate audio-appropriate outputs (transcript, chapters, notes) without attempting to create video outputs or perform video merging.
**Validates: Requirements 2.3**

### Property 7: Audio Format Support
*For any* file with a supported audio extension (MP3, WAV, FLAC, M4A), the system should accept it as valid input and process it successfully.
**Validates: Requirements 2.4**

### Property 8: Graceful Audio Metadata Handling
*For any* audio file with missing or malformed metadata, the system should continue processing without failing, using default values where necessary.
**Validates: Requirements 2.5**

### Property 9: Configuration Validation at Startup
*For any* system startup with a configured model sequence, all models in the sequence should be validated for availability and configuration errors should be reported with specific guidance.
**Validates: Requirements 4.1, 4.2, 4.5**

### Property 10: Configuration Status Reporting
*For any* multi-model configuration, the system should provide a summary showing each model's availability status and configuration details.
**Validates: Requirements 4.4**

### Property 11: Backward Compatibility Preservation
*For any* existing single-model configuration, the system should function identically to the current behavior without requiring configuration changes.
**Validates: Requirements 5.1, 5.3**

### Property 12: Default Value Application
*For any* configuration where new multi-model options are omitted, the system should apply sensible defaults and maintain existing functionality.
**Validates: Requirements 5.2, 5.4**

## Error Handling

### Configuration Errors
- **Invalid Model Names**: Validate model names against available models in the configured framework
- **Empty Sequences**: Handle empty or whitespace-only model sequences gracefully
- **Framework Mismatches**: Ensure all models in a sequence use the same framework
- **Circular Dependencies**: Prevent infinite loops in fallback logic

### Runtime Errors
- **Model Unavailability**: Gracefully handle models becoming unavailable during processing
- **Network Failures**: Implement retry logic for local model service connections
- **Resource Exhaustion**: Handle memory and timeout issues with large model sequences

### Input Validation Errors
- **Unsupported Formats**: Provide clear error messages for unsupported audio/video formats
- **Corrupted Files**: Detect and handle corrupted audio files gracefully
- **Permission Issues**: Handle file access permission errors appropriately

## Testing Strategy

### Dual Testing Approach
The implementation will use both unit tests and property-based tests to ensure comprehensive coverage:

**Unit Tests** will verify:
- Specific configuration parsing examples
- Error handling for known edge cases
- Integration between components
- Backward compatibility with existing configurations

**Property-Based Tests** will verify:
- Universal properties across all valid inputs using Hypothesis (Python's property-based testing library)
- Each property test will run a minimum of 100 iterations to ensure thorough coverage
- Tests will be tagged with references to design properties for traceability

### Property Test Configuration
Each property-based test will:
- Run minimum 100 iterations due to randomization
- Be tagged with format: **Feature: multi-model-audio-support, Property {number}: {property_text}**
- Reference the specific design document property being validated
- Use intelligent generators that constrain inputs to valid ranges

### Test Categories

**Configuration Testing**:
- Model sequence parsing with various formats
- Validation of different model availability scenarios
- Backward compatibility with existing .env files

**Pipeline Testing**:
- Audio vs video input detection and processing
- Multi-model review pass execution
- Output generation based on input type

**Error Handling Testing**:
- Model failure scenarios during review passes
- Invalid configuration handling
- File format validation and error reporting

**Integration Testing**:
- End-to-end processing with different input types
- Multi-model review workflows
- Fallback behavior under various failure conditions