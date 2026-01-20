import logging
import yt_dlp
import asyncio
import functools
import traceback
from tqdm import tqdm

logger = logging.getLogger(__name__)

def download_video(
    url: str, 
    output_template: str = "%(title)s.%(ext)s", 
    format_code: str = None,
    progress_hooks: list = None,
    restrict_filenames: bool = True,
    quiet: bool = True
) -> str:
    """
    Download a video (and subtitles) from a URL using yt-dlp.
    
    Args:
        url (str): The URL of the video to download.
        output_template (str): The output filename template. 
                               Default is "%(title)s.%(ext)s".
        format_code (str): The format code to use (optional). 
                           Defaults to robust logic.
        progress_hooks (list): Optional list of callback functions for progress updates.
        restrict_filenames (bool): Restrict filenames to ASCII characters (default: True).
        quiet (bool): Whether to suppress stdout output (default: True).
                               
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
        'ignoreerrors': True,  # Don't fail if subtitles can't be downloaded
        'quiet': quiet,
        'noprogress': True, # Always use our own progress bar or none
        'no_warnings': quiet,
        'restrictfilenames': restrict_filenames,
        # Ensure we merge into mp4 if possible for compatibility
        'merge_output_format': 'mp4', 
    }
    
    pbar = None
    
    def tqdm_hook(d):
        nonlocal pbar
        try:
            if d['status'] == 'downloading':
                if pbar is None:
                    total = d.get('total_bytes') or d.get('total_bytes_estimate')
                    # If total is unknown, we can still use tqdm but might need to be careful with arguments
                    pbar = tqdm(total=total, unit='B', unit_scale=True, unit_divisor=1024, desc="Downloading")
                
                downloaded = d.get('downloaded_bytes', 0)
                if pbar is not None:
                    pbar.update(downloaded - pbar.n)
            
            elif d['status'] == 'finished':
                if pbar is not None:
                    pbar.close()
                    pbar = None
        except Exception as pk_err:
            # If progress bar fails, just ignore it to not break the download
            logger.debug(f"Progress bar error: {pk_err}")

    if progress_hooks:
        ydl_opts['progress_hooks'] = progress_hooks
    elif not quiet:
        ydl_opts['progress_hooks'] = [tqdm_hook]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Extract info first to get the filename
            # We treat this as a single item download
            info = ydl.extract_info(url, download=True)
            
            if info is None:
                raise Exception("Failed to extract info (returned None)")

            # extract_info returns a dict for a single video, or 'entries' for a playlist
            # We assume single video for this helper, but handle basic playlist case by taking first
            if 'entries' in info:
                info = info['entries'][0]
                
            filename = ydl.prepare_filename(info)
            
            # If merged, the extension might change to mp4
            if info.get('requested_downloads'):
                for d in info['requested_downloads']:
                    if d.get('filepath'):
                        filename = d['filepath']
                        break
            
            logger.info(f"Successfully downloaded: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            logger.debug(traceback.format_exc())
            raise
        finally:
            if pbar is not None:
                pbar.close()

async def download_video_async(
    url: str, 
    output_template: str = "%(title)s.%(ext)s", 
    format_code: str = None,
    progress_hooks: list = None,
    restrict_filenames: bool = True,
    quiet: bool = True
) -> str:
    """
    Async wrapper for download_video. Runs the download in a thread pool.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, 
        functools.partial(
            download_video, 
            url, 
            output_template, 
            format_code, 
            progress_hooks, 
            restrict_filenames,
            quiet
        )
    )
