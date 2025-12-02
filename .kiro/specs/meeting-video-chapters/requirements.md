# Requirements Document

## Introduction

This document specifies the requirements for a Meeting Video Chapter Tool that processes MKV video files from recorded meetings, transcribes the audio content, identifies logical chapter boundaries, and adds chapter markers to the video files for easy navigation and reference.

## Glossary

- **MKV File**: A Matroska video container file format that stores video, audio, and metadata
- **Chapter Marker**: A timestamped metadata entry in a video file that marks the beginning of a logical section
- **Transcription**: The process of converting spoken audio content into written text
- **Audio Extraction**: The process of extracting audio data from a video container into a separate audio file
- **Chapter Merging**: The process of embedding chapter metadata into a video file
- **Whisper Model**: OpenAI's speech recognition model for audio transcription
- **Gemini Model**: Google's large language model for text analysis and generation
- **System**: The Meeting Video Chapter Tool

## Requirements

### Requirement 1

**User Story:** As a meeting attendee, I want to extract audio from my MKV recording files, so that I can process the audio for transcription.

#### Acceptance Criteria

1. WHEN a user provides a path to an MKV file, THE System SHALL extract the audio track using ffmpeg
2. WHEN audio extraction completes, THE System SHALL save the audio as an MP3 file in the same directory as the source MKV
3. WHEN the MKV file does not exist, THE System SHALL report an error and halt processing
4. WHEN the MKV file contains no audio track, THE System SHALL report an error and halt processing
5. WHEN audio extraction fails, THE System SHALL preserve the original MKV file unchanged

### Requirement 2

**User Story:** As a meeting attendee, I want to transcribe the extracted audio using Whisper, so that I can obtain a text representation of the meeting content.

#### Acceptance Criteria

1. WHEN a user initiates transcription on an MP3 file, THE System SHALL process the audio using the openai/whisper-large-v3-turbo model
2. WHEN transcription completes, THE System SHALL save the transcript with timestamps to a text file
3. WHEN the MP3 file does not exist, THE System SHALL report an error and halt processing
4. WHEN transcription fails, THE System SHALL report the error with diagnostic information
5. WHEN the audio file is empty or contains no speech, THE System SHALL handle the condition gracefully and report it to the user

### Requirement 3

**User Story:** As a meeting attendee, I want the system to identify logical chapter boundaries in the transcript, so that I can navigate to different topics discussed in the meeting.

#### Acceptance Criteria

1. WHEN a user requests chapter identification from a transcript, THE System SHALL analyze the transcript using the gemini-flash-latest model
2. WHEN chapter identification completes, THE System SHALL generate a list of chapters with timestamps and descriptive titles
3. WHEN the transcript is empty, THE System SHALL report an error and halt processing
4. WHEN the Gemini API call fails, THE System SHALL report the error with diagnostic information
5. WHEN chapters are generated, THE System SHALL ensure each chapter has a unique timestamp and a non-empty title

### Requirement 4

**User Story:** As a meeting attendee, I want to merge the generated chapters into my MKV file, so that I can use video player chapter navigation features.

#### Acceptance Criteria

1. WHEN a user requests chapter merging with a chapter list and MKV file, THE System SHALL embed the chapter metadata using ffmpeg
2. WHEN chapter merging completes, THE System SHALL create a new MKV file with embedded chapters
3. WHEN the chapter list is empty, THE System SHALL report an error and halt processing
4. WHEN chapter timestamps are invalid or out of order, THE System SHALL report an error and halt processing
5. WHEN chapter merging fails, THE System SHALL preserve the original MKV file unchanged

### Requirement 5

**User Story:** As a meeting attendee, I want to process my meeting video from start to finish with a single command, so that I can efficiently add chapters without manual intervention.

#### Acceptance Criteria

1. WHEN a user provides an MKV file path to the System, THE System SHALL execute all processing steps in sequence: audio extraction, transcription, chapter identification, and chapter merging
2. WHEN any processing step fails, THE System SHALL report which step failed and halt further processing
3. WHEN all processing steps complete successfully, THE System SHALL produce a final MKV file with embedded chapters
4. WHEN processing completes, THE System SHALL report the location of all generated files to the user
5. WHEN intermediate files already exist from a previous run, THE System SHALL provide an option to skip regeneration or overwrite them

### Requirement 6

**User Story:** As a meeting attendee, I want clear error messages when processing fails, so that I can understand what went wrong and how to fix it.

#### Acceptance Criteria

1. WHEN an error occurs during processing, THE System SHALL display a clear error message describing the problem
2. WHEN an external dependency (ffmpeg, Whisper, Gemini API) fails, THE System SHALL include the dependency name in the error message
3. WHEN a file operation fails, THE System SHALL include the file path in the error message
4. WHEN an API rate limit is exceeded, THE System SHALL report the rate limit error and suggest retry timing
5. WHEN processing completes with warnings, THE System SHALL display all warnings to the user

### Requirement 7

**User Story:** As a meeting attendee, I want to configure API keys and model parameters, so that I can use my own credentials and adjust processing behavior.

#### Acceptance Criteria

1. WHEN the System starts, THE System SHALL load configuration from environment variables or a configuration file
2. WHEN required API keys are missing, THE System SHALL report which keys are missing and halt processing
3. WHEN a user provides custom model names, THE System SHALL use the specified models instead of defaults
4. WHEN a user provides custom output paths, THE System SHALL save generated files to the specified locations
5. WHEN configuration is invalid, THE System SHALL report specific validation errors before processing begins
