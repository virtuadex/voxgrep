import logging
import yt_dlp

logger = logging.getLogger(__name__)

def download_video(url: str, output_template: str = "%(title)s.%(ext)s", format_code: str = None) -> str:
    """
    Download a video (and subtitles) from a URL using yt-dlp.
    
    Args:
        url (str): The URL of the video to download.
        output_template (str): The output filename template. 
                               Default is "%(title)s.%(ext)s".
        format_code (str): The format code to use (optional). 
                           Defaults to robust logic.
                               
    Returns:
        str: The filename of the downloaded video.
    """
    # Configure yt-dlp options
    ydl_opts = {
        'format': format_code if format_code else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en', 'pt'], # prioritize english and portuguese
        'quiet': False,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Extract info first to get the filename
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            logger.info(f"Successfully downloaded: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            raise
