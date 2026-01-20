from unittest.mock import patch, MagicMock, mock_open
import os
import json
import pytest
from voxgrep.core import transcriber

def test_transcribe_with_matching_metadata(tmp_path):
    """
    Test that existing transcript is reused when metadata matches.
    """
    dummy_video = tmp_path / "meta_test.mp4"
    dummy_video.write_text("fake video")
    
    transcript_file = tmp_path / "meta_test.json"
    metadata_file = tmp_path / "meta_test.transcript_meta.json"
    
    # Create existing transcript and metadata
    existing_transcript = [{"content": "Existing segment", "start": 0.0, "end": 1.0, "words": []}]
    existing_metadata = {
        "model": "tiny",
        "device": "cpu",
        "language": None,
        "compute_type": "int8"
    }
    
    with open(transcript_file, "w") as f:
        json.dump(existing_transcript, f)
    with open(metadata_file, "w") as f:
        json.dump(existing_metadata, f)
    
    # Request transcription with same settings
    result = transcriber.transcribe(
        str(dummy_video),
        model_name="tiny",
        device="cpu",
        compute_type="int8"
    )
    
    # Should reuse existing transcript
    assert result == existing_transcript

def test_transcribe_with_different_model_no_callback(tmp_path):
    """
    Test that warning is logged when model differs but no callback provided.
    """
    dummy_video = tmp_path / "diff_model_test.mp4"
    dummy_video.write_text("fake video")
    
    transcript_file = tmp_path / "diff_model_test.json"
    metadata_file = tmp_path / "diff_model_test.transcript_meta.json"
    
    # Create existing transcript with tiny model
    existing_transcript = [{"content": "Tiny model segment", "start": 0.0, "end": 1.0, "words": []}]
    existing_metadata = {
        "model": "tiny",
        "device": "cpu",
        "language": None,
        "compute_type": "int8"
    }
    
    with open(transcript_file, "w") as f:
        json.dump(existing_transcript, f)
    with open(metadata_file, "w") as f:
        json.dump(existing_metadata, f)
    
    # Request with different model (no callback = should reuse with warning)
    with patch('voxgrep.core.transcriber.logger') as mock_logger:
        result = transcriber.transcribe(
            str(dummy_video),
            model_name="base",  # Different model
            device="cpu"
        )
        
        # Should still reuse existing
        assert result == existing_transcript
        
        # Should have logged warning
        mock_logger.warning.assert_called()
        warning_msg = mock_logger.warning.call_args[0][0]
        assert "tiny" in warning_msg
        assert "base" in warning_msg

def test_transcribe_with_different_model_callback_reuse(tmp_path):
    """
    Test callback is called when model differs and user chooses to reuse.
    """
    dummy_video = tmp_path / "callback_reuse_test.mp4"
    dummy_video.write_text("fake video")
    
    transcript_file = tmp_path / "callback_reuse_test.json"
    metadata_file = tmp_path / "callback_reuse_test.transcript_meta.json"
    
    existing_transcript = [{"content": "Old transcript", "start": 0.0, "end": 1.0, "words": []}]
    existing_metadata = {
        "model": "tiny",
        "device": "cpu",
        "language": None,
        "compute_type": "int8"
    }
    
    with open(transcript_file, "w") as f:
        json.dump(existing_transcript, f)
    with open(metadata_file, "w") as f:
        json.dump(existing_metadata, f)
    
    callback_called = []
    def mock_callback(existing_meta, current_meta):
        callback_called.append((existing_meta, current_meta))
        return True  # User chooses to reuse
    
    result = transcriber.transcribe(
        str(dummy_video),
        model_name="large-v3",
        device="cuda",
        on_existing_transcript=mock_callback
    )
    
    # Callback should have been called
    assert len(callback_called) == 1
    assert callback_called[0][0]["model"] == "tiny"
    assert callback_called[0][1]["model"] == "large-v3"
    
    # Should reuse existing
    assert result == existing_transcript

def test_transcribe_with_different_model_callback_regenerate(tmp_path):
    """
    Test that new transcription is generated when user chooses to regenerate.
    """
    dummy_video = tmp_path / "callback_regen_test.mp4"
    dummy_video.write_text("fake video")
    
    transcript_file = tmp_path / "callback_regen_test.json"
    metadata_file = tmp_path / "callback_regen_test.transcript_meta.json"
    
    existing_transcript = [{"content": "Old transcript", "start": 0.0, "end": 1.0, "words": []}]
    existing_metadata = {
        "model": "tiny",
        "device": "cpu",
        "language": None,
        "compute_type": "int8"
    }
    
    with open(transcript_file, "w") as f:
        json.dump(existing_transcript, f)
    with open(metadata_file, "w") as f:
        json.dump(existing_metadata, f)
    
    def mock_callback(existing_meta, current_meta):
        return False  # User chooses to regenerate
    
    with patch('voxgrep.core.transcriber.WhisperModel') as mock_whisper:
        mock_model = MagicMock()
        mock_whisper.return_value = mock_model
        
        mock_segment = MagicMock()
        mock_segment.text = "New transcript"
        mock_segment.start = 0.0
        mock_segment.end = 1.0
        mock_segment.words = []
        
        mock_model.transcribe.return_value = ([mock_segment], MagicMock(duration=1.0, language="en"))
        
        result = transcriber.transcribe(
            str(dummy_video),
            model_name="large-v3",
            device="cpu",
            on_existing_transcript=mock_callback
        )
        
        # Should have new transcript
        assert result[0]["content"] == "New transcript"
        
        # Metadata should be updated
        with open(metadata_file, "r") as f:
            saved_meta = json.load(f)
            assert saved_meta["model"] == "large-v3"
