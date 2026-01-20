
import os
import sys
import shutil
import tempfile
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Override Data Dir for isolation
temp_dir = tempfile.mkdtemp()
os.environ["VOXGREP_DATA_DIR"] = temp_dir
# Also set logs to not pollute
os.environ["VOXGREP_LOG_LEVEL"] = "WARNING"

print(f"Using temp dir: {temp_dir}")

from voxgrep.server.db import create_db_and_tables, engine, get_session
from voxgrep.server.models import Video
from voxgrep.server.vector_store import get_vector_store
from voxgrep.server.subtitles import burn_subtitles_on_segments, SubtitleStyle
from voxgrep.server.transitions import concatenate_with_transitions, TransitionType
from voxgrep import search_engine
from sqlmodel import Session, select

def test_everything():
    print("=== voxgrep Feature Test ===")
    
    # 1. Setup DB
    print("\n1. Setting up Database...")
    create_db_and_tables()
    
    # Prepare input file
    input_source = project_root / "tests/test_inputs/metallica.mp4"
    if not input_source.exists():
        print(f"Error: {input_source} not found")
        return

    # Copy to temp dir to act as "Library"
    # This simulates scanning a directory or downloading a video
    library_dir = Path(temp_dir) / "library"
    library_dir.mkdir()
    target_file = library_dir / "metallica.mp4"
    shutil.copy(input_source, target_file)
    print(f"   [Upload] Copied video to library: {target_file}")
    
    # 2. Simulate "Upload/Scan"
    print("\n2. Scanning Library...")
    with Session(engine) as session:
        # In a real app, _scan_path does this. We do it manually to avoid path issues with temp dirs in tests
        stats = os.stat(target_file)
        video = Video(
            path=str(target_file),
            filename=target_file.name,
            size_bytes=stats.st_size,
            created_at=stats.st_mtime,
            has_transcript=False
        )
        session.add(video)
        session.commit()
        session.refresh(video)
        video_id = video.id
        print(f"   [Scan] Added video to DB with ID: {video_id}")

    # 3. Simulate "Transcribe"
    print("\n3. Transcribing...")
    # We use the pre-calculated transcript to avoid downloading large models during this test
    # This simulates the result of a successful transcription
    pre_calculated_json = project_root / "tests/test_inputs/metallica.json"
    transcript_path = library_dir / "metallica.json"
    shutil.copy(pre_calculated_json, transcript_path)
    
    with Session(engine) as session:
        video = session.get(Video, video_id)
        video.has_transcript = True
        video.transcript_path = str(transcript_path)
        session.add(video)
        session.commit()
    print("   [Transcribe] Transcription completed (used cached result).")

    # 4. Simulate "Index"
    print("\n4. Indexing for Semantic Search...")
    # This might download a small BERT model
    try:
        with Session(engine) as session:
            transcript = search_engine.parse_transcript(str(target_file))
            vector_store = get_vector_store()
            count = vector_store.index_video(video_id, transcript, session)
            print(f"   [Index] Successfully indexed {count} segments.")
    except Exception as e:
        print(f"   [Index] Failed (this requires internet for model download): {e}")

    # 5. Simulate "Search"
    print("\n5. Searching...")
    results = []
    with Session(engine) as session:
        vector_store = get_vector_store()
        # Search for "concert" which appears in the text as "concerto"
        # Using a very low threshold to ensure matches
        results_raw = vector_store.search("concerto", session, threshold=0.2)
        print(f"   [Search] Found {len(results_raw)} results for 'concerto'")
        
        for r in results_raw[:3]:
            print(f"      - {r['content']} ({r['score']:.2f})")
            results.append(r)

    if not results:
        print("   [Search] No results found, cannot proceed with export.")
        return

    # 6. Simulate "Export"
    print("\n6. Exporting Supercuts...")
    
    # Common composition data
    composition = results
    
    # A. With Transitions
    output_trans = library_dir / "supercut_transitions.mp4"
    print(f"   [Export A] Creating supercut with CROSSFADE transitions...")
    try:
        concatenate_with_transitions(
            composition, 
            str(output_trans), 
            transition_type=TransitionType.CROSSFADE,
            transition_duration=0.5
        )
        print(f"      Success: {output_trans}")
    except ImportError:
         print("      Skipped: MoviePy not installed or working")
    except Exception as e:
         print(f"      Failed: {e}")

    # B. With Subtitles
    output_subs = library_dir / "supercut_subs.mp4"
    print(f"   [Export B] Creating supercut with BURNED SUBTITLES (Netflix style - Modified for Test)...")
    try:
        style = SubtitleStyle.preset_netflix()
        style.font = "Arial" # Force available font
        burn_subtitles_on_segments(
            composition, 
            str(output_subs), 
            style=style
        )
        print(f"      Success: {output_subs}")
    except ImportError:
         print("      Skipped: MoviePy not installed or working")
    except Exception as e:
         print(f"      Failed: {e}")

    print("\n=== Test Complete ===")
    print(f"All artifacts are in {library_dir}")

if __name__ == "__main__":
    test_everything()
