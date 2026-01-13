import videogrep
from glob import glob
from glob import glob
from subprocess import run
import videogrep.modules.youtube


def auto_youtube_supercut(query, max_videos=1):
    """
    Search youtube for a query, download videos with yt-dlp,
    and then makes a supercut with that query
    """

    # Download video using the new module
    # We use a specific output format to match what videogrep expects (or what we want)
    # The new download_video function handles the details
    try:
        videogrep.modules.youtube.download_video(
            "https://www.youtube.com/results?search_query=" + query,
            output_template=query + "%(autonumber)s.%(ext)s"
        )
    except Exception as e:
        print(f"Error downloading videos: {e}")
        return

    # grab the videos we just downloaded
    files = glob(query + "*.mp4")

    # run videogrep
    videogrep.videogrep(files, query, search_type="fragment")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Create a supercut of youtube videos based on a search term"
    )

    parser.add_argument("--search", "-s", dest="search", help="search term")

    parser.add_argument(
        "--max",
        "-m",
        dest="max_videos",
        type=int,
        default=1,
        help="maximum number of videos to download",
    )

    args = parser.parse_args()

    auto_youtube_supercut(args.search, args.max_videos)
