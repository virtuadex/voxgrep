#!/usr/bin/env python
"""
Demo script showing the model metadata tracking feature.

This demonstrates what happens when you try to transcribe a video
with different model settings than what was used originally.
"""

import os
import json
import tempfile
from pathlib import Path

# Create a temporary test environment
with tempfile.TemporaryDirectory() as tmpdir:
    # Simulate a video file
    video_path = Path(tmpdir) / "demo_video.mp4"
    video_path.write_text("fake video content")
    
    # Simulate an existing transcript created with tiny model on CPU
    transcript_path = Path(tmpdir) / "demo_video.json"
    metadata_path = Path(tmpdir) / "demo_video.transcript_meta.json"
    
    existing_transcript = [
        {"content": "Hello world", "start": 0.0, "end": 1.0, "words": []},
        {"content": "This is a test", "start": 1.0, "end": 2.0, "words": []}
    ]
    
    existing_metadata = {
        "model": "tiny",
        "device": "cpu",
        "language": None,
        "compute_type": "int8"
    }
    
    with open(transcript_path, "w") as f:
        json.dump(existing_transcript, f, indent=2)
    
    with open(metadata_path, "w") as f:
        json.dump(existing_metadata, f, indent=2)
    
    print("=" * 60)
    print("VoxGrep Model Metadata Tracking Demo")
    print("=" * 60)
    print()
    print("Scenario: You previously transcribed a video with:")
    print(f"  Model: {existing_metadata['model']}")
    print(f"  Device: {existing_metadata['device']}")
    print()
    print("Now you want to transcribe the same video with:")
    print("  Model: large-v3")
    print("  Device: cuda")
    print()
    print("VoxGrep will detect this and prompt you:")
    print()
    print("  ⚠ Found existing transcript created with different settings:")
    print(f"    Existing: {existing_metadata['model']} on {existing_metadata['device']}")
    print("    Requested: large-v3 on cuda")
    print()
    print("  ? What would you like to do?")
    print("    ❯ Use existing transcript (faster)")
    print("      Regenerate with new settings (recommended for quality)")
    print("      Cancel")
    print()
    print("=" * 60)
    print()
    print("Files created in this demo:")
    print(f"  📄 {transcript_path.name} - The transcript data")
    print(f"  📋 {metadata_path.name} - Model metadata")
    print()
    print("Metadata contents:")
    print(json.dumps(existing_metadata, indent=2))
    print()
    print("=" * 60)
    print("Benefits:")
    print("  ✓ Never accidentally use low-quality transcripts")
    print("  ✓ Always know what model created your transcript")
    print("  ✓ Easy to upgrade quality when needed")
    print("  ✓ Saves time by reusing when appropriate")
    print("=" * 60)
