from voxgrep.core import engine
import os

video = "A_Magia_Perdida_do_Shareware_e_das_Demos_de_Videojogos.mp4"
transcript = engine.parse_transcript(video)

if transcript:
    print(f"Loaded {len(transcript)} segments")
    
    # Test 1: Substring search
    results = engine.search(video, "demo", search_type="sentence", exact_match=False)
    print(f"Substring search for 'demo': {len(results)} matches")
    for r in results[:5]:
        print(f"  {r['start']:.2f}s: {r['content']}")
        
    # Test 2: Exact search
    results_exact = engine.search(video, "demo", search_type="sentence", exact_match=True)
    print(f"Exact match search for 'demo': {len(results_exact)} matches")
    for r in results_exact[:5]:
        print(f"  {r['start']:.2f}s: {r['content']}")
else:
    print("Could not load transcript")
