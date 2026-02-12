"""Audio file converter service.

This module handles conversion of audio files (FLAC, WAV, AAC/m4a) to MP3 format.
"""

import io
import logging

from pydub import AudioSegment

logger = logging.getLogger(__name__)

# Supported audio formats
SUPPORTED_FORMATS = {".flac", ".wav", ".m4a", ".mp3"}


class AudioConverter:
    """Audio format converter using pydub."""

    @staticmethod
    def convert_to_mp3(audio_data: bytes, file_extension: str, bitrate: str = "192k") -> bytes:
        """Convert audio file to MP3 format.

        Args:
            audio_data: Raw audio file data as bytes
            file_extension: File extension including the dot (e.g., '.flac', '.wav', '.m4a')
            bitrate: Target bitrate for MP3 (default: '192k')

        Returns:
            MP3 encoded audio data as bytes

        Raises:
            ValueError: If file extension is not supported
            Exception: If conversion fails

        Examples:
            >>> converter = AudioConverter()
            >>> with open("audio.flac", "rb") as f:
            ...     audio_data = f.read()
            >>> mp3_data = converter.convert_to_mp3(audio_data, ".flac")
        """
        file_extension = file_extension.lower()

        if file_extension not in SUPPORTED_FORMATS:
            msg = f"Unsupported audio format: {file_extension}. Supported formats: {SUPPORTED_FORMATS}"
            logger.error(msg)
            raise ValueError(msg)

        # If already MP3, return as is
        if file_extension == ".mp3":
            logger.info("Audio is already in MP3 format, skipping conversion")
            return audio_data

        try:
            # Load audio from bytes
            logger.info("Loading audio from bytes (format: %s)", file_extension)
            audio = AudioSegment.from_file(io.BytesIO(audio_data), format=file_extension[1:])

            # Export to MP3
            logger.info("Converting audio to MP3 with bitrate %s", bitrate)
            output_buffer = io.BytesIO()
            audio.export(output_buffer, format="mp3", bitrate=bitrate)
            output_buffer.seek(0)
            mp3_data = output_buffer.read()

            logger.info("Audio conversion successful, output size: %d bytes", len(mp3_data))
            return mp3_data

        except Exception as e:
            logger.exception("Failed to convert audio to MP3")
            raise
