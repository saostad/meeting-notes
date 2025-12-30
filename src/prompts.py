"""Centralized prompt management for AI providers.

This module contains all prompts used by different AI providers
to ensure consistency and maintainability.
"""

import json
from typing import List
from src.transcript import Transcript


def format_review_prompt(original_result: dict, transcript: Transcript) -> str:
    """Generate a prompt for reviewing and improving transcript analysis results.
    
    This function creates a prompt that asks the AI to review the initial analysis
    and add any missing chapters or notes that might have been overlooked.
    
    Args:
        original_result: The original analysis result with chapters and notes
        transcript: The original transcript for reference
        
    Returns:
        Formatted review prompt string ready for AI model consumption
    """
    # Build raw transcript data for reference
    transcript_data = {
        "segments": [
            {
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "text": segment.text
            }
            for segment in transcript.segments
        ],
        "duration": transcript.duration
    }
    
    # Convert to JSON strings
    original_json = json.dumps(original_result, indent=2, ensure_ascii=False)
    transcript_json = json.dumps(transcript_data, indent=2, ensure_ascii=False)
    
    # Define the expected JSON format
    json_format_example = """{
  "chapters": [
    {"timestamp_original": 0.0, "timestamp_in_minutes": 0.0, "title": "Introduction"},
    {"timestamp_original": 120.5, "timestamp_in_minutes": 2.0, "title": "Main Discussion"},
    {"timestamp_original": 300.0, "timestamp_in_minutes": 5.5, "title": "Conclusion"}
  ],
  "notes": [
    {"timestamp_original": 0.0, "timestamp_in_minutes": 0.0, "person_name": "Saeid", "details": "Switch the test workspace branch back to main after the PR merge."},
    {"timestamp_original": 180.0, "timestamp_in_minutes": 3.0, "person_name": "John", "details": "Update the documentation with the new API endpoints."}
  ]
}"""
    
    prompt = f"""Here is the meeting notes and chapters of attached JSON meeting transcription. Please review and add missing parts.

ORIGINAL ANALYSIS RESULT:
{original_json}

Your task is to:
1. Review the original analysis for completeness
2. Check if any important chapters or topic changes were missed
3. Look for additional actionable instructions, tasks, or steps that weren't captured
4. Add any missing chapters that represent significant topic changes
5. Add any missing notes with actionable instructions, technical steps, or tasks

IMPORTANT GUIDELINES:
- Keep all existing chapters and notes that are correct
- Only ADD missing content, don't remove or modify existing good content
- For chapters: Look for topic transitions, new discussion points, or significant shifts in conversation
- For notes: Focus on actionable items, technical steps, setup instructions, tasks assigned to people, or sequential workflows
- Be specific in note details and include step order/index when mentioned in the meeting
- Use exact timestamps from the transcript segments' "start_time" field
- CRITICAL: Ensure all chapters are listed in chronological order by timestamp

CRITICAL RULES FOR TIMESTAMPS:
- Extract timestamps directly from the transcript segments' "start_time" field without modification or rounding
- Use the exact timestamp values from the JSON data
- List all chapters in ascending chronological order (earliest timestamp first)
- Each chapter must have a unique timestamp (no duplicates)
- Violation of these rules will invalidate the entire response

Return your response in this exact JSON format:
{json_format_example}

CRITICAL: You MUST return ONLY valid JSON in the exact format specified above. Do not include any explanations, markdown formatting, or additional text. Start your response with {{ and end with }}. Ensure chapters are sorted by timestamp in ascending order.

TRANSCRIPT REFERENCE (for finding missing content):
{transcript_json}
"""
    
    return prompt


def format_transcript_analysis_prompt(transcript: Transcript) -> str:
    """Generate a unified prompt for transcript analysis across all AI providers.
    
    This function creates a standardized prompt that works with both
    Ollama and Gemini providers for chapter identification and note extraction.
    
    Args:
        transcript: The transcript to analyze
        
    Returns:
        Formatted prompt string ready for AI model consumption
    """
    # Build raw transcript data (segments only, no full_text)
    transcript_data = {
        "segments": [
            {
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "text": segment.text
            }
            for segment in transcript.segments
        ],
        "duration": transcript.duration
    }
    
    # Convert to JSON string for the AI
    transcript_json = json.dumps(transcript_data, indent=2, ensure_ascii=False)
    
    # Define the expected JSON format as an example
    json_format_example = """{
  "chapters": [
    {"timestamp_original": 0.0, "timestamp_in_minutes": 0.0, "title": "Introduction"},
    {"timestamp_original": 120.5, "timestamp_in_minutes": 2.0, "title": "Main Discussion"},
    {"timestamp_original": 300.0, "timestamp_in_minutes": 5.0, "title": "Conclusion"}
  ],
  "notes": [
    {"timestamp_original": 0.0, "timestamp_in_minutes": 0.0, "person_name": "Saeid", "details": "Switch the test workspace branch back to main after the PR merge."}
  ]
}"""
    
    # Create the unified prompt
    prompt = f"""Analyze the following meeting transcript JSON data and identify logical chapter boundaries.

The transcript is provided as JSON with segments containing start_time, end_time, and text fields.

For each chapter, provide:
1. The timestamp (in seconds) where the chapter begins. Use the exact "start_time" values from the segments.
2. A concise, descriptive title for the chapter.

The chapters should represent major topic changes or sections in the meeting.
Aim for 3-80 chapters depending on the content length and structure.

Additionally, extract any actionable instructions or tasks mentioned in the meeting. 
"notes" should be a list of actionable instructions and tasks found in the meeting. If none found, leave this as an empty array.
Be specific for note details, if possible include order/index of the steps mentioned in meeting to guide the person.
Look for:
- Technical steps that need to be done (e.g., "first do this, then do that")
- Action items assigned to people
- Setup instructions or configuration steps
- Implementation tasks or procedures
- Any sequential instructions or workflows

CRITICAL RULES FOR TIMESTAMPS:
- Extract timestamps directly from the transcript segments' "start_time" field without modification or rounding.
- Use the exact timestamp values from the JSON data.
- List all chapters in ascending chronological order (earliest timestamp first).
- Each chapter must have a unique timestamp (no duplicates).
- Violation of these rules will invalidate the entire response.

Return your response in this exact JSON format:
{json_format_example}

CRITICAL: You MUST return ONLY valid JSON in the exact format specified above. Do not include any explanations, markdown formatting, or additional text. Start your response with {{ and end with }}. Ensure chapters are sorted by timestamp in ascending order.

Transcript JSON Data:
{transcript_json}
"""
    
    return prompt


def _format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS timestamp.
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string (MM:SS)
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


# Additional prompt templates can be added here for future use
def get_prompt_templates() -> dict:
    """Get all available prompt templates.
    
    Returns:
        Dictionary of prompt template names and descriptions
    """
    return {
        "transcript_analysis": {
            "function": "format_transcript_analysis_prompt",
            "description": "Unified prompt for transcript chapter analysis and note extraction",
            "supported_providers": ["ollama", "gemini"]
        },
        "review_analysis": {
            "function": "format_review_prompt", 
            "description": "Review prompt for improving and completing analysis results",
            "supported_providers": ["ollama", "gemini"]
        }
    }