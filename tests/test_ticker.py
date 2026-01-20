from unittest.mock import patch, MagicMock
import os
import json
import pytest
from voxgrep.core import transcriber

def test_transcribe_whisper_ticker_callback(tmp_path):
    """
    Test that the progress callback in transcribe_whisper receives the 'text' argument.
    """
    # Create a dummy video file
    dummy_video = tmp_path / "ticker_test.mp4"
    dummy_video.write_text("fake video content")
    
    # Mock WhisperModel
    with patch('voxgrep.core.transcriber.WhisperModel') as mock_whisper:
        mock_model = MagicMock()
        mock_whisper.return_value = mock_model
        
        # Mock segments
        mock_segment = MagicMock()
        mock_segment.text = "Hello ticker"
        mock_segment.start = 0.0
        mock_segment.end = 1.0
        mock_segment.words = []
        
        # model.transcribe returns (generator, info)
        mock_model.transcribe.return_value = ([mock_segment], MagicMock(duration=1.0, language="en"))
        
        # Callback to capture calls
        callback_calls = []
        def my_callback(current, total, text=None):
            callback_calls.append((current, total, text))
            
        # Run transcription
        # We need to ensure we don't use a cached transcript
        transcript_path = os.path.splitext(str(dummy_video))[0] + ".json"
        if os.path.exists(transcript_path):
            os.remove(transcript_path)
            
        transcriber.transcribe(
            str(dummy_video), 
            model_name="tiny", 
            progress_callback=my_callback
        )
        
        # Verify callback was called with text
        assert len(callback_calls) > 0
        _, _, text = callback_calls[0]
        assert text == "Hello ticker"

@patch('voxgrep.core.transcriber.WhisperModel')
def test_transcribe_whisper_legacy_callback(mock_whisper, tmp_path):
    """
    Test that the progress callback still works even if it doesn't accept 'text'.
    """
    mock_model = MagicMock()
    mock_whisper.return_value = mock_model
    
    mock_segment = MagicMock()
    mock_segment.text = "Legacy test"
    mock_segment.start = 0.0
    mock_segment.end = 1.0
    mock_segment.words = []
    
    mock_model.transcribe.return_value = ([mock_segment], MagicMock(duration=1.0, language="en"))
    
    dummy_video = tmp_path / "legacy_test.mp4"
    dummy_video.write_text("dummy")
    
    # Legacy callback only accepts 2 args
    callback_calls = []
    def legacy_callback(current, total):
        callback_calls.append((current, total))
        
    # Should not raise TypeError
    transcriber.transcribe(
        str(dummy_video), 
        model_name="tiny", 
        progress_callback=legacy_callback
    )
    
    assert len(callback_calls) > 0
    assert callback_calls[0] == (1.0, 1.0)
