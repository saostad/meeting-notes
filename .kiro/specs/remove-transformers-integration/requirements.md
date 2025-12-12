# Requirements Document

## Introduction

This document outlines the requirements for removing the Hugging Face Transformers integration from the Meeting Video Chapter Tool. The system currently supports multiple AI providers including Ollama, Transformers, and Gemini API. The user has determined that the Transformers integration is unnecessary since Ollama provides sufficient local AI capabilities. This cleanup will simplify the codebase, reduce dependencies, and improve maintainability.

## Glossary

- **Transformers Provider**: The AI provider implementation using Hugging Face Transformers library for local model execution
- **Ollama Provider**: The AI provider implementation using Ollama service for local model execution  
- **AI Provider Manager**: The system component that orchestrates provider selection and fallback logic
- **Configuration System**: The environment-based configuration management system
- **Dependency Management**: The system for managing Python package requirements

## Requirements

### Requirement 1

**User Story:** As a developer, I want to remove the Transformers provider implementation, so that the codebase is simplified and focuses only on necessary AI providers.

#### Acceptance Criteria

1. WHEN the system initializes AI providers, THE system SHALL NOT attempt to create or use TransformersProvider
2. WHEN the local model framework is set to "transformers", THE system SHALL treat this as an invalid configuration
3. WHEN the local model framework is set to "auto", THE system SHALL only attempt to use Ollama provider
4. WHEN configuration validation occurs, THE system SHALL reject "transformers" as a valid framework option
5. WHEN the system reports available providers, THE system SHALL NOT include Transformers in the list

### Requirement 2

**User Story:** As a system administrator, I want Transformers-related dependencies removed from the project, so that the installation is lighter and has fewer potential security vulnerabilities.

#### Acceptance Criteria

1. WHEN installing project dependencies, THE system SHALL NOT require transformers library
2. WHEN installing project dependencies, THE system SHALL NOT require torch library
3. WHEN the Docker container builds, THE system SHALL NOT include transformers or torch packages
4. WHEN environment validation occurs, THE system SHALL NOT check for transformers availability
5. WHEN the system starts, THE system SHALL NOT attempt to import transformers modules

### Requirement 3

**User Story:** As a developer, I want all Transformers-related configuration options removed, so that the configuration is cleaner and less confusing.

#### Acceptance Criteria

1. WHEN loading configuration, THE system SHALL NOT recognize TRANSFORMERS_DEVICE environment variable
2. WHEN validating configuration, THE system SHALL NOT validate transformers-specific settings
3. WHEN displaying configuration help, THE system SHALL NOT mention transformers options
4. WHEN using Docker environment, THE system SHALL NOT set TRANSFORMERS_CACHE environment variable
5. WHEN the local framework is "auto", THE system SHALL default to ollama only

### Requirement 4

**User Story:** As a developer, I want all Transformers-related code and tests removed, so that the codebase is cleaner and easier to maintain.

#### Acceptance Criteria

1. WHEN browsing the codebase, THE system SHALL NOT contain TransformersProvider class
2. WHEN running tests, THE system SHALL NOT execute transformers-related test cases
3. WHEN importing AI providers, THE system SHALL NOT reference transformers provider module
4. WHEN the AI provider manager initializes, THE system SHALL NOT contain transformers creation logic
5. WHEN documentation is generated, THE system SHALL NOT reference transformers functionality

### Requirement 5

**User Story:** As a user, I want existing functionality to continue working with Ollama as the primary local provider, so that my workflows are not disrupted.

#### Acceptance Criteria

1. WHEN using local AI provider with Ollama available, THE system SHALL analyze transcripts successfully
2. WHEN Ollama is not available and fallback is enabled, THE system SHALL fall back to Gemini API
3. WHEN configuration specifies "ollama" framework, THE system SHALL use Ollama provider exclusively
4. WHEN existing environment files specify transformers settings, THE system SHALL ignore them gracefully
5. WHEN the system validates providers, THE system SHALL report Ollama availability correctly