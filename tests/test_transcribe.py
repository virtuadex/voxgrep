import pytest
from unittest.mock import patch, MagicMock
from videogrep import transcribe
import os
import json

@patch('videogrep.transcribe.WhisperModel')
def test_transcribe_whisper_mock(mock_whisper, tmp_path):
    # Mock the WhisperModel instance and its transcribe method
    mock_model = MagicMock()
    mock_whisper.return_value = mock_model
    
    # Mock segment
    mock_segment = MagicMock()
    mock_segment.text = "Hello world"
    mock_segment.start = 0.0
    mock_segment.end = 1.0
    mock_segment.words = [
        MagicMock(word="Hello", start=0.0, end=0.5, probability=0.9),
        MagicMock(word="world", start=0.5, end=1.0, probability=0.9)
    ]
    
    # model.transcribe returns (generator, info)
    mock_model.transcribe.return_value = ([mock_segment], MagicMock(duration=1.0, language="en"))
    
    # Create a dummy video file
    dummy_video = tmp_path / "test.mp4"
    dummy_video.write_text("dummy")
    
    # Run transcribe
    result = transcribe.transcribe(str(dummy_video), model_name="tiny")
    
    assert len(result) == 1
    assert result[0]["content"] == "Hello world"
    assert len(result[0]["words"]) == 2
    assert result[0]["words"][0]["word"] == "Hello"
    
    # Check if JSON file was created
    json_file = tmp_path / "test.json"
    assert json_file.exists()
    with open(json_file) as f:
        data = json.load(f)
        assert data[0]["content"] == "Hello world"

@patch('videogrep.transcribe.mlx_whisper')
def test_transcribe_mlx_mock(mock_mlx, tmp_path):
    # Mock result from mlx_whisper.transcribe
    mock_mlx.transcribe.return_value = {
        "text": "Hello mlx",
        "segments": [
            {
                "text": "Hello mlx",
                "start": 0.0,
                "end": 1.0,
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 0.5, "probability": 0.9},
                    {"word": "mlx", "start": 0.5, "end": 1.0, "probability": 0.9}
                ]
            }
        ]
    }
    
    dummy_video = tmp_path / "test_mlx.mp4"
    dummy_video.write_text("dummy")
    
    # We need to force MLX_AVAILABLE to True for this test if it defaulted to False
    with patch('videogrep.transcribe.MLX_AVAILABLE', True):
        result = transcribe.transcribe(str(dummy_video), device="mlx")
    
    mock_mlx.transcribe.assert_called_once()
    assert len(result) == 1
    assert result[0]["content"] == "Hello mlx"
    assert len(result[0]["words"]) == 2
    assert result[0]["words"][0]["word"] == "Hello"

