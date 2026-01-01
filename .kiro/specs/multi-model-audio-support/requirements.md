# Requirements Document

## Introduction

This feature enhances the Meeting Video Chapter Tool with two key capabilities: support for multiple local AI models in review steps and direct audio file processing. These improvements provide greater flexibility in AI model selection and expand input format support beyond video files.

## Glossary

- **System**: The Meeting Video Chapter Tool
- **Local_Model**: An AI model running locally (e.g., via Ollama)
- **Review_Pass**: An iterative analysis step that improves chapter identification quality
- **Audio_File**: A standalone audio file (MP3, WAV, FLAC, etc.)
- **Pipeline**: The complete processing workflow from input to chaptered output
- **Model_Sequence**: An ordered list of local models configured for sequential use in review passes

## Requirements

### Requirement 1: Sequential Multi-Model Configuration

**User Story:** As a system administrator, I want to configure a sequence of local AI models in the .env file, so that each review pass uses a different model (e.g., phi4 for pass 1, mistral-nemo for pass 2, llama3 for pass 3) for improved analysis quality through model diversity.

#### Acceptance Criteria

1. WHEN multiple local models are defined in sequence in the .env file, THE System SHALL parse and validate all model configurations in order
2. WHEN review pass N is initiated, THE System SHALL use the Nth model from the configured sequence
3. WHEN more review passes are requested than models configured, THE System SHALL cycle through the model sequence
4. WHEN a specific model in the sequence fails, THE System SHALL attempt to use the next available model in the sequence
5. WHEN no local models in the sequence are available, THE System SHALL fall back to the primary configured model or external API

### Requirement 2: Audio File Input Support

**User Story:** As a user, I want to process audio recordings directly, so that I can generate chapters for audio-only content without needing video files.

#### Acceptance Criteria

1. WHEN an Audio_File is provided as input, THE System SHALL accept it and skip audio extraction
2. WHEN processing an Audio_File, THE Pipeline SHALL proceed directly to transcription
3. WHEN generating output for Audio_Files, THE System SHALL create audio-specific output files (no video merging)
4. THE System SHALL support common audio formats including MP3, WAV, FLAC, and M4A
5. WHEN an Audio_File lacks required metadata, THE System SHALL handle it gracefully and continue processing

### Requirement 3: Sequential Model Selection Logic

**User Story:** As a power user, I want the system to use models in the specified sequence for review passes, so that I get consistent and predictable model usage (phi4 → mistral-nemo → llama3) for optimal chapter analysis.

#### Acceptance Criteria

1. WHEN multiple review passes are configured, THE System SHALL use models in the exact sequence specified in the configuration
2. WHEN review pass 1 starts, THE System SHALL use the first model in the Model_Sequence
3. WHEN review pass 2 starts, THE System SHALL use the second model in the Model_Sequence
4. WHEN more review passes are requested than models in the sequence, THE System SHALL cycle back to the first model
5. WHEN a model in the sequence is unavailable, THE System SHALL skip to the next model in the sequence and log the substitution

### Requirement 4: Configuration Validation and Management

**User Story:** As a system administrator, I want comprehensive validation of multi-model configurations, so that I can identify and fix configuration issues before processing begins.

#### Acceptance Criteria

1. WHEN the System starts, THE System SHALL validate all models in the configured Model_Sequence for availability
2. WHEN a model configuration is invalid, THE System SHALL provide specific error messages with correction guidance
3. WHEN model availability changes during runtime, THE System SHALL adapt gracefully
4. THE System SHALL provide a configuration summary showing available models and their status
5. WHEN configuration validation fails, THE System SHALL prevent processing and display actionable error messages

### Requirement 5: Backward Compatibility

**User Story:** As an existing user, I want my current configuration to continue working unchanged, so that the new features don't break my existing workflows.

#### Acceptance Criteria

1. WHEN existing single-model configurations are used, THE System SHALL function identically to the current behavior
2. WHEN new configuration options are not specified, THE System SHALL use sensible defaults
3. WHEN legacy .env files are loaded, THE System SHALL maintain full compatibility
4. THE System SHALL support both old and new configuration formats simultaneously
5. WHEN migration is needed, THE System SHALL provide clear guidance on configuration updates