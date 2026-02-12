"""Tests for AudioConverter."""

import pytest

from services import AudioConverter


def test_convert_to_mp3_passthrough_for_mp3() -> None:
    """MP3 input should be returned as-is without conversion."""
    sample_bytes = b"fake-mp3-data"
    output_bytes = AudioConverter.convert_to_mp3(sample_bytes, ".mp3")
    assert output_bytes == sample_bytes


def test_convert_to_mp3_unsupported_extension() -> None:
    """Unsupported extensions should raise ValueError."""
    with pytest.raises(ValueError, match="Unsupported audio format"):
        AudioConverter.convert_to_mp3(b"data", ".ogg")
