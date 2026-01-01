"""Simple file type detector."""

from pathlib import Path


class SimpleFileDetector:
    """Simple file type detector."""
    
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg'}
    VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov', '.webm'}
    
    @classmethod
    def detect_file_type(cls, file_path: str) -> str:
        """Detect if file is audio or video based on extension."""
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if suffix in cls.AUDIO_EXTENSIONS:
            return 'audio'
        elif suffix in cls.VIDEO_EXTENSIONS:
            return 'video'
        else:
            raise ValueError(f"Unsupported file format: {suffix}")