import sys
import os
# Add the project root to the path so we can import voxgrep
sys.path.append(os.getcwd())

from voxgrep.modules.youtube import download_video

url = "https://youtu.be/7oxnxBdguwE?si=S_zDvdXZd6yBGNa9"
try:
    # Restrict filenames to avoid issues with special characters
    filename = download_video(url, restrict_filenames=True, quiet=False)
    print(f"DOWNLOAD_SUCCESS: {filename}")
except Exception as e:
    print(f"DOWNLOAD_ERROR: {e}")
    sys.exit(1)