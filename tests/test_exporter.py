import pytest
import os
from pathlib import Path
from videogrep import exporter

def test_get_file_type():
    assert exporter.get_file_type("test.mp4") == "video"
    assert exporter.get_file_type("test.mp3") == "audio"
    assert exporter.get_file_type("test.txt") == "text"
    assert exporter.get_file_type("unknown_file_type") == "unknown"

def test_plan_video_output():
    composition = [{"file": "video.mp4", "start": 0, "end": 1}]
    assert exporter.plan_video_output(composition, "output.mp4") is True
    assert exporter.plan_video_output(composition, "output.mp3") is False

def test_plan_audio_output():
    composition = [{"file": "video.mp4", "start": 0, "end": 1}]
    # Video input can produce audio output
    assert exporter.plan_audio_output(composition, "output.mp3") is True
    
    audio_composition = [{"file": "audio.mp3", "start": 0, "end": 1}]
    assert exporter.plan_audio_output(audio_composition, "output.mp3") is True
    assert exporter.plan_audio_output(audio_composition, "output.mp4") is True # Logic says True, but create_supercut will fail later

def test_export_m3u(tmp_path):
    composition = [
        {"file": "test1.mp4", "start": 10, "end": 20},
        {"file": "test2.mp4", "start": 30, "end": 40}
    ]
    output = tmp_path / "test.m3u"
    exporter.export_m3u(composition, str(output))
    
    content = output.read_text()
    assert "#EXTM3U" in content
    assert "test1.mp4" in content
    assert "start-time=10" in content

def test_export_mpv_edl(tmp_path):
    composition = [
        {"file": "test1.mp4", "start": 10, "end": 20}
    ]
    output = tmp_path / "test.edl"
    exporter.export_mpv_edl(composition, str(output))
    
    content = output.read_text()
    assert "# mpv EDL v0" in content
    # Format: path,start,duration
    assert "10,10" in content

def test_export_xml(tmp_path):
    test_video = str(Path(__file__).parent / "test_inputs" / "metallica.mp4")
    composition = [
        {"file": test_video, "start": 1.0, "end": 2.0, "content": "hello"}
    ]
    output = tmp_path / "test.xml"
    exporter.export_xml(composition, str(output))
    
    content = output.read_text()
    assert "<?xml" in content
    # fcpxml.py generates FCP XML 1.x which has <xmeml> or similar
    assert "xmeml" in content or "fcpxml" in content
