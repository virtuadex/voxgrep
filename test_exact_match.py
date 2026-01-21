from voxgrep.core import engine
import re

video = "A_Magia_Perdida_do_Shareware_e_das_Demos_de_Videojogos.mp4"

# Test exact match in fragment mode
print("=== Fragment Mode with Exact Match ===")
results = engine.search(video, "demo", search_type="fragment", exact_match=True)
print(f"Found {len(results)} matches\n")

for r in results[:10]:
    content = r['content']
    # Highlight the match
    pattern = r'\b' + re.escape("demo") + r'\b'
    highlighted = re.sub(pattern, lambda m: f"[{m.group()}]", content, flags=re.IGNORECASE)
    print(f"{r['start']:.2f}s: {highlighted}")

print("\n=== Checking word-level data ===")
transcript = engine.parse_transcript(video)
if transcript and 'words' in transcript[0]:
    # Find all words that match
    all_words = []
    for segment in transcript:
        if 'words' in segment:
            all_words.extend(segment['words'])
    
    # Check for exact "demo" matches
    demo_words = [w for w in all_words if re.match(r'^demo$', w['word'], re.IGNORECASE)]
    print(f"Exact 'demo' words found: {len(demo_words)}")
    for w in demo_words[:5]:
        print(f"  {w['start']:.2f}s: '{w['word']}'")
    
    # Check for words containing "demo"
    demo_substring = [w for w in all_words if 'demo' in w['word'].lower()]
    print(f"\nWords containing 'demo': {len(demo_substring)}")
    unique_words = set(w['word'] for w in demo_substring)
    print(f"Unique words: {sorted(unique_words)}")
