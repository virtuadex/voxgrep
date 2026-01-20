import time
import os
import sys
import logging
from voxgrep.core.transcriber import transcribe

# Configure logging to show info
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def run_benchmark():
    input_file = os.path.abspath("anticomuna.mp4")
    transcript_file = os.path.splitext(input_file)[0] + ".json"
    
    # Clean up existing results to force fresh transcription
    if os.path.exists(transcript_file):
        print(f"Removing existing transcript: {transcript_file}")
        os.remove(transcript_file)
    
    print(f"\n{'='*60}")
    print(f"HIGH ACCURACY MODE BENCHMARK")
    print(f"{'='*60}")
    print(f"File: {input_file}")
    print(f"Model: large-v3")
    print(f"Settings: beam_size=10, best_of=10, vad_filter=True")
    print(f"Vocabulary: Andre Ventura, Chega, política portuguesa, parlamento")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    try:
        results = transcribe(
            videofile=input_file,
            model_name="large-v3",
            device="cuda",
            language="pt",
            prompt="Andre Ventura, Chega, política portuguesa, parlamento, comunismo",
            beam_size=10,
            best_of=10,
            vad_filter=True
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n{'='*60}")
        print(f"RESULTS")
        print(f"{'='*60}")
        print(f"Total Time: {duration:.2f} seconds")
        print(f"Segments: {len(results)}")
        if results:
            print(f"First Segment: {results[0]['content']}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\nERROR: {e}")

if __name__ == "__main__":
    run_benchmark()
