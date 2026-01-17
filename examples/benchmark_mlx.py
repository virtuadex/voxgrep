import time
import sys
import os
import shutil
from videogrep import transcribe
import logging

# Configure logging to show info
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def benchmark(filename, device="cpu", model="tiny"):
    print(f"\n--- Benchmarking {device.upper()} with model '{model}' ---")
    
    # Clean up previous transcript to force re-run
    json_path = os.path.splitext(filename)[0] + ".json"
    if os.path.exists(json_path):
        os.remove(json_path)
    
    start = time.time()
    try:
        if device == "mlx":
            # For MLX, ensuring we map basic names to likely HF repos if not fully specified
            # minimal map for testing
            if model == "tiny":
                model_name = "mlx-community/whisper-tiny-mlx"
            elif model == "base":
                model_name = "mlx-community/whisper-base-mlx"
            elif model == "small":
                model_name = "mlx-community/whisper-small-mlx" 
            else:
                model_name = model # assume full path or large-v3 default handling in transcribe.py
                
            transcribe.transcribe(filename, model_name=model_name, device="mlx")
        else:
            # faster-whisper handles simple names like "tiny", "base"
            transcribe.transcribe(filename, model_name=model, device="cpu")
            
    except Exception as e:
        print(f"Benchmark failed for {device}: {e}")
        return None
        
    end = time.time()
    duration = end - start
    print(f"Done in {duration:.4f} seconds")
    return duration

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python benchmark_mlx.py <video_file> [model_size]")
        print("Example: python benchmark_mlx.py tests/test_inputs/metallica.mp4 tiny")
        sys.exit(1)
        
    videofile = sys.argv[1]
    if not os.path.exists(videofile):
        print(f"File {videofile} not found.")
        sys.exit(1)

    model_size = "tiny"
    if len(sys.argv) > 2:
        model_size = sys.argv[2]
        
    print(f"Target File: {videofile}")
    
    # 1. CPU Benchmark
    cpu_time = benchmark(videofile, device="cpu", model=model_size)
    
    # 2. MLX Benchmark
    mlx_time = benchmark(videofile, device="mlx", model=model_size)
    
    print("\n--- Results ---")
    if cpu_time:
        print(f"CPU (faster-whisper): {cpu_time:.4f}s")
    if mlx_time:
        print(f"GPU (MLX):           {mlx_time:.4f}s")
        
    if cpu_time and mlx_time:
        speedup = cpu_time / mlx_time
        print(f"Speedup:             {speedup:.2f}x")
