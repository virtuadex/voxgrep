from unittest.mock import patch, MagicMock
import pytest
from voxgrep.core import transcriber

def test_transcribe_whisper_keyboard_interrupt(tmp_path):
    """
    Test that KeyboardInterrupt during transcription saves partial results.
    """
    # Create a dummy video file
    dummy_video = tmp_path / "cancel_test.mp4"
    dummy_video.write_text("fake video content")
    
    # Mock WhisperModel
    with patch('voxgrep.core.transcriber.WhisperModel') as mock_whisper:
        mock_model = MagicMock()
        mock_whisper.return_value = mock_model
        
        # Create multiple mock segments
        def segment_generator():
            for i in range(5):
                seg = MagicMock()
                seg.text = f"Segment {i}"
                seg.start = float(i)
                seg.end = float(i + 1)
                seg.words = []
                yield seg
                # Simulate user pressing Ctrl+C after 2 segments
                if i == 1:
                    raise KeyboardInterrupt()
        
        # model.transcribe returns (generator, info)
        mock_model.transcribe.return_value = (segment_generator(), MagicMock(duration=5.0, language="en"))
        
        # Run transcription
        result = transcriber.transcribe(str(dummy_video), model_name="tiny")
        
        # Should have saved 2 segments before interruption
        assert len(result) == 2
        assert result[0]["content"] == "Segment 0"
        assert result[1]["content"] == "Segment 1"
        
        # Check that partial JSON was saved
        import json
        import os
        json_file = os.path.splitext(str(dummy_video))[0] + ".json"
        assert os.path.exists(json_file)
        with open(json_file) as f:
            data = json.load(f)
            assert len(data) == 2
            assert data[0]["content"] == "Segment 0"

def test_transcribe_whisper_keyboard_interrupt_with_callback(tmp_path):
    """
    Test that KeyboardInterrupt works correctly with progress callback.
    """
    dummy_video = tmp_path / "cancel_callback_test.mp4"
    dummy_video.write_text("fake video content")
    
    with patch('voxgrep.core.transcriber.WhisperModel') as mock_whisper:
        mock_model = MagicMock()
        mock_whisper.return_value = mock_model
        
        def segment_generator():
            for i in range(5):
                seg = MagicMock()
                seg.text = f"Callback segment {i}"
                seg.start = float(i)
                seg.end = float(i + 1)
                seg.words = []
                yield seg
                if i == 2:
                    raise KeyboardInterrupt()
        
        mock_model.transcribe.return_value = (segment_generator(), MagicMock(duration=5.0, language="en"))
        
        callback_calls = []
        def my_callback(current, total, text=None):
            callback_calls.append((current, total, text))
        
        result = transcriber.transcribe(
            str(dummy_video), 
            model_name="tiny",
            progress_callback=my_callback
        )
        
        # Should have 3 segments (0, 1, 2)
        assert len(result) == 3
        assert result[2]["content"] == "Callback segment 2"
        
        # Callback should have been called 3 times
        assert len(callback_calls) == 3
