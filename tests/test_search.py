import pytest
from pathlib import Path
import voxgrep.core.engine as search_mod

def File(path):
    return str(Path(__file__).parent / Path("test_inputs") / Path(path))

def test_find_transcript_basic():
    testvid = File("metallica.mp4")
    # Should find metallica.json by default because it's first in SUB_EXTS
    found = search_mod.find_transcript(testvid)
    assert found.endswith("metallica.json")

def test_find_transcript_prefer():
    testvid = File("metallica.mp4")
    found = search_mod.find_transcript(testvid, prefer=".srt")
    assert found.endswith("metallica.srt")

def test_parse_transcript_srt():
    testvid = File("metallica.mp4")
    transcript = search_mod.parse_transcript(testvid, prefer=".srt")
    assert len(transcript) > 0
    assert "Prometo ser" in transcript[0]["content"]

def test_search_sentence():
    testvid = File("metallica.mp4")
    # Search for "concerto" in the SRT
    results = search_mod.search(testvid, "concerto", search_type="sentence", prefer=".srt")
    assert len(results) == 1
    assert "concerto" in results[0]["content"]

def test_search_fragment():
    testvid = File("metallica.mp4")
    # "Prometo ser" is a fragment in the JSON/SRT if word timestamps exist
    # metallica.json has word timestamps
    results = search_mod.search(testvid, "Prometo ser", search_type="fragment", prefer=".json")
    assert len(results) == 1
    assert results[0]["content"] == "Prometo ser"
    assert results[0]["start"] == 0.0
    # "ser" ends at 0.56 in metallica.json
    assert results[0]["end"] == pytest.approx(0.56)

def test_search_mash():
    testvid = File("metallica.mp4")
    # "concerto" appears once in metallica.json
    results = search_mod.search(testvid, "concerto", search_type="mash", prefer=".json")
    assert len(results) == 1
    assert results[0]["content"] == "concerto"

def test_get_ngrams():
    testvid = File("metallica.mp4")
    ngrams = list(search_mod.get_ngrams(testvid, n=2))
    # Should have pairs of words
    assert len(ngrams) > 0
    assert len(ngrams[0]) == 2
