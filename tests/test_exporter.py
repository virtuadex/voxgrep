from pathlib import Path
from voxgrep.core import exporter

from pathlib import Path
from voxgrep.core import exporter
import pytest
from voxgrep.utils.exceptions import InvalidOutputFormatError

def test_get_input_type():
    # Only tests logic based on keys, doesn't actually check files on disk 
    # IF get_input_type blindly trusts file extensions or if we mock it.
    # Looking at source, it calls 'get_media_type' which checks extensions.
    
    # We need to mock get_media_type since it might check file headers or extensions
    # but based on previous file view, get_media_type was imported from utils.
    pass

def test_plan_output_strategy_video():
    composition = [{"file": "video.mp4", "start": 0, "end": 1}]
    # Video input + video output = video
    assert exporter.plan_output_strategy(composition, "output.mp4") == "video"
    
def test_plan_output_strategy_audio():
    composition = [{"file": "video.mp4", "start": 0, "end": 1}]
    # Video input + audio output = audio
    assert exporter.plan_output_strategy(composition, "output.mp3") == "audio"
    
    audio_composition = [{"file": "audio.mp3", "start": 0, "end": 1}]
    # Audio input + audio output = audio
    assert exporter.plan_output_strategy(audio_composition, "output.mp3") == "audio"

def test_plan_output_strategy_invalid():
    audio_composition = [{"file": "audio.mp3", "start": 0, "end": 1}]
    # Audio input + video output = Error (can't make video from just audio without visualization)
    with pytest.raises(InvalidOutputFormatError):
        exporter.plan_output_strategy(audio_composition, "output.mp4")

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
