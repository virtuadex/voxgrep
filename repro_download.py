
import os
import sys
# Ensure we can import videogrep
sys.path.append(os.getcwd())
from videogrep.modules import youtube

def test_download():
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw" # Me at the zoo
    output_dir = "test_downloads"
    
    print(f"Testing download to {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Mimic desktop_api.py logic
        template = os.path.join(output_dir, "%(title)s.%(ext)s")
        print(f"Template: {template}")
        
        filename = youtube.download_video(url, output_template=template)
        print(f"Success! Downloaded to: {filename}")
        
        if os.path.exists(filename):
            print("File exists on disk.")
        else:
            print("File DOES NOT exist on disk!")
            
    except Exception as e:
        print(f"FAILED with error: {e}")

if __name__ == "__main__":
    test_download()
