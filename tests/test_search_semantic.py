from unittest.mock import patch, MagicMock
import numpy as np
from voxgrep.core import engine as search_engine

@patch('voxgrep.core.engine.SentenceTransformer')
@patch('voxgrep.core.engine.util.cos_sim')
def test_semantic_search_mock(mock_cos_sim, mock_transformer, tmp_path):
    # Setup mock model
    mock_model = MagicMock()
    mock_transformer.return_value = mock_model
    
    # Mock model.encode for query and sentences
    # We'll just return dummy arrays
    mock_model.encode.side_effect = [
        np.array([[0.1, 0.2]]), # query embedding
        np.array([[0.1, 0.2], [0.9, 0.9]]) # sentence embeddings
    ]
    
    # Mock cos_sim results
    # Query 1 vs Sentence 1 & 2
    mock_cos_sim.return_value = np.array([[0.9, 0.1]])
    
    # Create dummy transcript and video
    testvid = str(tmp_path / "test.mp4")
    with open(testvid, "w") as f: f.write("dummy")
    
    transcript = [
        {"content": "Match this", "start": 0, "end": 1},
        {"content": "Not this", "start": 2, "end": 3}
    ]
    import json
    with open(str(tmp_path / "test.json"), "w") as f:
        json.dump(transcript, f)
        
    # We need to mock SEMANTIC_AVAILABLE
    with patch('voxgrep.core.engine.SEMANTIC_AVAILABLE', True):
        # We also need to mock get_embeddings to avoid actual encoding if we want, 
        # but let's test the flow.
        # Actually SemanticModel singleton will try to load.
        with patch('voxgrep.core.engine.SemanticModel.get_instance', return_value=mock_model):
            results = search_engine.search(testvid, "Query", search_type="semantic", threshold=0.5)
            
    assert len(results) == 1
    assert results[0]["content"] == "Match this"
    assert results[0]["score"] == 0.9

def test_mashup_punctuation_fix(tmp_path):
    # Test the punctuation fix I added earlier
    transcript = [{
        "content": "Hello world.",
        "start": 0,
        "end": 1,
        "words": [
            {"word": "Hello", "start": 0, "end": 0.5},
            {"word": "world.", "start": 0.5, "end": 1.0}
        ]
    }]
    import json
    testvid = str(tmp_path / "test_punc.mp4")
    with open(testvid, "w") as f: f.write("dummy")
    with open(str(tmp_path / "test_punc.json"), "w") as f:
        json.dump(transcript, f)
        
    results = search_engine.search(testvid, "world", search_type="mash")
    assert len(results) == 1
    assert results[0]["content"] == "world."
