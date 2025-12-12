# Requirements Document

## Introduction

This document specifies the requirements for enhancing the Meeting Video Chapter Tool to support local open source AI models (primarily Phi4) for transcript analysis, with Google Gemini API as a fallback option. This enhancement will reduce dependency on external APIs, improve privacy, and provide users with more control over their data processing.

## Glossary

- **Local AI Model**: An open source language model running locally on the user's machine (e.g., Phi4, Llama, etc.)
- **Phi4**: Microsoft's open source small language model optimized for reasoning and analysis tasks
- **Ollama**: A tool for running large language models locally
- **Hugging Face Transformers**: A library for running transformer-based models locally
- **Analysis Provider**: The AI service used for transcript analysis (local model or Gemini API)
- **Fallback Provider**: The backup AI service used when the primary provider fails
- **System**: The Meeting Video Chapter Tool with enhanced AI provider support
- **Transcript Analysis**: The process of analyzing meeting transcripts to identify chapter boundaries and extract actionable notes

## Requirements

### Requirement 1

**User Story:** As a meeting attendee, I want to use a local AI model for transcript analysis, so that I can process my meeting data privately without sending it to external APIs.

#### Acceptance Criteria

1. WHEN a user configures a local AI model as the primary analysis provider, THE System SHALL use the local model for transcript analysis
2. WHEN the local AI model is available and functional, THE System SHALL process transcripts without making external API calls
3. WHEN a user specifies Phi4 as the local model, THE System SHALL load and use the Phi4 model for analysis
4. WHEN the local model processes a transcript, THE System SHALL generate chapters and notes in the same format as the Gemini API
5. WHEN local processing completes successfully, THE System SHALL not attempt to use the fallback provider

### Requirement 2

**User Story:** As a meeting attendee, I want the option to use Gemini API as a fallback when local processing fails, so that I can choose whether to use external services when local models have issues.

#### Acceptance Criteria

1. WHEN a user enables the fallback option and the local AI model fails to load or initialize, THE System SHALL switch to the Gemini API fallback
2. WHEN fallback is disabled and the local AI model fails, THE System SHALL report the error and halt processing
3. WHEN fallback is enabled and the local model produces invalid output, THE System SHALL retry using the Gemini API
4. WHEN using the fallback provider, THE System SHALL log the reason for the fallback and notify the user
5. WHEN fallback is enabled and both providers fail, THE System SHALL report the errors from both attempts

### Requirement 3

**User Story:** As a meeting attendee, I want to configure which AI provider to use and whether to enable fallback, so that I can choose the best setup for my needs and environment.

#### Acceptance Criteria

1. WHEN a user sets the AI_PROVIDER environment variable, THE System SHALL use the specified provider as the primary analysis method
2. WHEN a user sets the ENABLE_FALLBACK environment variable to true, THE System SHALL use Gemini API as backup when the primary provider fails
3. WHEN no AI provider is configured, THE System SHALL default to local model as primary with fallback disabled
4. WHEN fallback is disabled and the primary provider fails, THE System SHALL report the error and halt processing
5. WHEN provider configuration is invalid, THE System SHALL report specific configuration errors before processing begins

### Requirement 4

**User Story:** As a meeting attendee, I want to configure local AI model parameters, so that I can optimize performance and quality for my hardware and requirements.

#### Acceptance Criteria

1. WHEN a user specifies a local model name, THE System SHALL attempt to load the specified model
2. WHEN a user configures model parameters like temperature or max tokens, THE System SHALL apply these settings during analysis
3. WHEN a user specifies a custom model path, THE System SHALL load the model from the specified location
4. WHEN local model configuration is invalid, THE System SHALL report the configuration error and suggest corrections
5. WHEN the specified local model is not available, THE System SHALL report the missing model and available alternatives

### Requirement 5

**User Story:** As a meeting attendee, I want the system to support multiple local AI frameworks, so that I can use the framework that works best in my environment.

#### Acceptance Criteria

1. WHEN Ollama is available on the system, THE System SHALL support using Ollama-hosted models for analysis
2. WHEN Hugging Face Transformers is available, THE System SHALL support loading models directly through the transformers library
3. WHEN multiple frameworks are available, THE System SHALL use the framework specified in configuration or default to a preferred order
4. WHEN no supported frameworks are available, THE System SHALL report the missing dependencies and installation instructions
5. WHEN a framework fails to load a model, THE System SHALL try alternative frameworks before falling back to the external API

### Requirement 6

**User Story:** As a meeting attendee, I want clear feedback about which AI provider is being used, so that I can understand how my data is being processed.

#### Acceptance Criteria

1. WHEN transcript analysis begins, THE System SHALL report which AI provider is being used for processing
2. WHEN the system falls back to an alternative provider, THE System SHALL notify the user about the provider switch and reason
3. WHEN analysis completes, THE System SHALL report which provider successfully processed the transcript
4. WHEN multiple providers are attempted, THE System SHALL log all attempts and their outcomes
5. WHEN processing uses an external API, THE System SHALL clearly indicate that data is being sent to external services

### Requirement 7

**User Story:** As a meeting attendee, I want the local AI analysis to produce the same quality output as the Gemini API, so that I get consistent results regardless of which provider is used.

#### Acceptance Criteria

1. WHEN using a local AI model, THE System SHALL generate chapters with timestamps and descriptive titles matching the Gemini API format
2. WHEN extracting actionable notes, THE System SHALL identify the same types of tasks and instructions as the Gemini API version
3. WHEN parsing model output, THE System SHALL handle both local model and Gemini API response formats correctly
4. WHEN local model output format differs from expected, THE System SHALL attempt to normalize it to the standard format
5. WHEN output quality is significantly lower than expected, THE System SHALL provide warnings about potential accuracy issues

### Requirement 8

**User Story:** As a meeting attendee, I want the system to handle resource constraints gracefully, so that local AI processing works reliably on different hardware configurations.

#### Acceptance Criteria

1. WHEN system memory is insufficient for the selected model, THE System SHALL report the memory requirement and suggest smaller models
2. WHEN local processing is taking too long, THE System SHALL provide progress updates and allow user cancellation
3. WHEN GPU acceleration is available, THE System SHALL utilize it to improve processing speed
4. WHEN CPU-only processing is required, THE System SHALL adjust model parameters for optimal CPU performance
5. WHEN resource usage exceeds safe limits, THE System SHALL throttle processing or suggest configuration changes
