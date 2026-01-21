"""
Stream processing handler for live transcription from URL.
Handles concurrent downloading and real-time transcription using piping.
"""
import subprocess
import threading
import time
import numpy as np
import logging
import os
from queue import Queue, Empty
from typing import Callable, Optional

from ..server.multi_model import TranscriptionBackend, get_model_manager

logger = logging.getLogger(__name__)

class StreamHandler:
    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize StreamHandler.
        
        Args:
            callback: Function called with new segments list when a chunk is processed.
        """
        self.callback = callback
        self.running = False
        self.process_ytdlp = None
        self.process_ffmpeg = None
        
        self.model_mgr = get_model_manager()
        
        # Audio settings for Whisper (16kHz mono)
        self.SAMPLE_RATE = 16000
        self.BUFFER_DURATION = 30.0 # Process 30s chunks
        # 16-bit audio = 2 bytes per sample
        self.CHUNK_SIZE = int(self.SAMPLE_RATE * self.BUFFER_DURATION * 2) 
        
    def start_processing(
        self, 
        url: str, 
        output_path: str, 
        device: str = "cpu",
        model: str = "base",
        compute_type: str = "int8"
    ):
        """
        Start concurrent download and transcription.
        
        Args:
            url: The URL to download (YouTube, etc.)
            output_path: Local path to save the full recording.
            device: Device to use (cpu, cuda, mlx).
            model: Whisper model name.
            compute_type: Compute type (int8, float16, etc).
        """
        if self.running:
            logger.warning("StreamHandler already running.")
            return

        self.running = True
        self.device = device
        self.model = model
        self.compute_type = compute_type
        
        # Start IO thread (Download -> File + FFmpeg)
        self.io_thread = threading.Thread(
            target=self._io_loop, 
            args=(url, output_path),
            name="StreamIO"
        )
        self.io_thread.daemon = True
        self.io_thread.start()
        
        # Start Transcribe thread (FFmpeg -> Whisper)
        self.transcribe_thread = threading.Thread(
            target=self._transcribe_loop,
            name="StreamTranscribe"
        )
        self.transcribe_thread.daemon = True
        self.transcribe_thread.start()

    def stop(self):
        """Stop processing and cleanup."""
        self.running = False
        if self.process_ytdlp:
            self.process_ytdlp.terminate()
        if self.process_ffmpeg:
            self.process_ffmpeg.terminate()
            
    def _io_loop(self, url, output_path):
        logger.info(f"Starting stream download: {url} -> {output_path}")
        
        # 1. yt-dlp to stdout
        ytdlp_cmd = [
            "yt-dlp",
            url,
            "-o", "-",      # Output to stdout
            "--quiet", "--no-warnings",
            "-f", "bestvideo+bestaudio/best"  # Ensure we get a stream
        ]
        
        # 2. ffmpeg to decode stdin to PCM s16le stdout
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", "pipe:0",     # Input from stdin
            "-f", "s16le",      # PCM signed 16-bit little-endian
            "-ac", "1",         # Mono
            "-ar", "16000",     # 16kHz
            "pipe:1"            # Output to stdout
        ]
        
        try:
            # shell=False is safer and works better for signal handling
            self.process_ytdlp = subprocess.Popen(
                ytdlp_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            
            self.process_ffmpeg = subprocess.Popen(
                ffmpeg_cmd, 
                stdin=subprocess.PIPE, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            
            with open(output_path, "wb") as f_out:
                while self.running:
                    # Read chunk from yt-dlp
                    # Use a reasonable buffer size (e.g. 64KB)
                    chunk = self.process_ytdlp.stdout.read(65536)
                    
                    if not chunk:
                        # Check if process ended
                        if self.process_ytdlp.poll() is not None:
                            logger.info("yt-dlp download finished.")
                            # Check for errors
                            stderr_out = self.process_ytdlp.stderr.read()
                            if stderr_out:
                                logger.warning(f"yt-dlp stderr: {stderr_out.decode('utf-8', errors='ignore')}")
                            self.running = False
                            break
                        # No data yet, wait briefly
                        time.sleep(0.1)
                        continue
                        
                    # Write to file for persistence
                    f_out.write(chunk)
                    
                    # Write to ffmpeg for processing
                    try:
                        self.process_ffmpeg.stdin.write(chunk)
                        self.process_ffmpeg.stdin.flush()
                    except (BrokenPipeError, OSError):
                        logger.warning("FFmpeg stdin broken/closed.")
                        break
                        
        except Exception as e:
            logger.error(f"Stream IO Error: {e}")
        finally:
            self.running = False
            # Clean up
            if self.process_ffmpeg:
                self.process_ffmpeg.terminate()
            if self.process_ytdlp:
                self.process_ytdlp.terminate()

    def _transcribe_loop(self):
        buffer = bytearray()
        offset_seconds = 0.0
        
        logger.info("Transcribe loop started.")
        
        while self.running:
            if not self.process_ffmpeg:
                time.sleep(0.5)
                continue
                
            try:
                # Read from ffmpeg stdout
                # Non-blocking read would be ideal, but standard read is blocking.
                # Since we are in a thread, blocking is okay as long as bytes arrive.
                chunk = self.process_ffmpeg.stdout.read(4096)
                
                if not chunk:
                    if self.process_ffmpeg.poll() is not None:
                        break
                    time.sleep(0.01)
                    continue
                
                buffer.extend(chunk)
                
                # Check for full chunk
                while len(buffer) >= self.CHUNK_SIZE:
                    # Extract one chunk duration
                    pcm_bytes = buffer[:self.CHUNK_SIZE]
                    buffer = buffer[self.CHUNK_SIZE:]
                    
                    self._transcribe_chunk(pcm_bytes, offset_seconds)
                    offset_seconds += self.BUFFER_DURATION
                    
            except Exception as e:
                logger.error(f"Transcribe loop error: {e}")
                time.sleep(1)
        
        # Process remaining buffer
        if len(buffer) > 0:
             logger.info(f"Processing final partial chunk ({len(buffer)} bytes)")
             # Pad with zeros to match CHUNK_SIZE if needed, or just process as is?
             # faster-whisper handles variable lengths usually, but our _transcribe_chunk assumes normalized to float
             # Let's just process what we have
             self._transcribe_chunk(buffer, offset_seconds)

    def _transcribe_chunk(self, pcm_bytes, offset):
        # normalize int16 to float32 (-1.0 to 1.0)
        audio_data = np.frombuffer(pcm_bytes, dtype=np.int16).flatten().astype(np.float32) / 32768.0
        
        try:
            # Transcribe numpy array
            # Use faster-whisper as it reliably supports numpy input
            res = self.model_mgr.transcribe(
                audio_data, 
                backend=TranscriptionBackend.FASTER_WHISPER,
                device=self.device,
                model=self.model,
                compute_type=self.compute_type
            )
            
            # Adjust timestamps to absolute time
            for segment in res.segments:
                segment['start'] += offset
                segment['end'] += offset
                if 'words' in segment:
                    for w in segment['words']:
                        w['start'] += offset
                        w['end'] += offset
            
            if self.callback:
                self.callback(res.segments)
                
            logger.info(f"Stream: Chunk {offset:.1f}s processed. {len(res.segments)} segments.")
            
        except Exception as e:
            logger.error(f"Stream transcription error: {e}")

