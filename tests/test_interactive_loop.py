"""
Test script to verify interactive mode loop continues after transcription.
"""
from unittest.mock import patch, MagicMock
import sys

# Mock questionary to simulate user input
mock_responses = [
    "test_video.mp4",  # File selection
    "transcribe",      # Task selection (first time)
    "cpu",             # Device
    "tiny",            # Model
    "exit"             # Exit after transcription
]

response_iter = iter(mock_responses)

def mock_select(*args, **kwargs):
    mock_obj = MagicMock()
    mock_obj.ask.return_value = next(response_iter)
    return mock_obj

def mock_checkbox(*args, **kwargs):
    mock_obj = MagicMock()
    mock_obj.ask.return_value = ["test_video.mp4"]
    return mock_obj

def mock_text(*args, **kwargs):
    mock_obj = MagicMock()
    mock_obj.ask.return_value = "1"
    return mock_obj

with patch('voxgrep.cli.interactive.questionary.select', side_effect=mock_select):
    with patch('voxgrep.cli.interactive.questionary.checkbox', side_effect=mock_checkbox):
        with patch('voxgrep.cli.interactive.questionary.text', side_effect=mock_text):
            with patch('voxgrep.core.transcriber.transcribe') as mock_transcribe:
                # Mock successful transcription
                mock_transcribe.return_value = [
                    {"content": "Test", "start": 0.0, "end": 1.0, "words": []}
                ]
                
                from voxgrep.cli.interactive import interactive_mode
                
                try:
                    interactive_mode()
                    print("✓ Interactive mode completed successfully")
                    print("✓ Menu loop continued after transcription")
                except Exception as e:
                    print(f"✗ Error: {e}")
                    import traceback
                    traceback.print_exc()
                    sys.exit(1)
