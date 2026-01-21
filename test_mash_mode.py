from voxgrep.core import engine
import json

video = "A_Magia_Perdida_do_Shareware_e_das_Demos_de_Videojogos.mp4"
transcript = engine.parse_transcript(video)

if transcript and len(transcript) > 0:
    print(f"Loaded {len(transcript)} segments")
    
    # Check if word-level data exists
    first_segment = transcript[0]
    print(f"\nFirst segment keys: {first_segment.keys()}")
    print(f"Has 'words' key: {'words' in first_segment}")
    
    if 'words' in first_segment:
        print(f"Number of words in first segment: {len(first_segment['words'])}")
        print(f"Sample words: {first_segment['words'][:3]}")
    else:
        print("\n⚠️ NO WORD-LEVEL DATA FOUND!")
        print("This VTT file needs to be converted to JSON with word timestamps.")
        
    # Test mash search
    print("\n--- Testing MASH search ---")
    results = engine.search(video, "demo", search_type="mash", exact_match=True)
    print(f"Mash search results: {len(results)} matches")
    
    if results:
        for r in results[:3]:
            print(f"  {r['start']:.2f}s: {r['content']}")
else:
    print("Could not load transcript")
