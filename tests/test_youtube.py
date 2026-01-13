import unittest
from unittest.mock import patch, MagicMock
from videogrep.modules import youtube

class TestYoutubeModule(unittest.TestCase):
    
    @patch('videogrep.modules.youtube.yt_dlp.YoutubeDL')
    def test_download_video_success(self, mock_ydl):
        # Setup mock
        mock_instance = mock_ydl.return_value
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.extract_info.return_value = {'title': 'Test Video', 'ext': 'mp4'}
        mock_instance.prepare_filename.return_value = 'Test Video.mp4'
        
        # Run function
        filename = youtube.download_video('http://fake.url')
        
        # Verify
        self.assertEqual(filename, 'Test Video.mp4')
        mock_instance.extract_info.assert_called_once()
        
    @patch('videogrep.modules.youtube.yt_dlp.YoutubeDL')
    def test_download_video_failure(self, mock_ydl):
        # Setup mock to raise exception
        mock_instance = mock_ydl.return_value
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.extract_info.side_effect = Exception("Download failed")
        
        # Run function and expect exception
        with self.assertRaises(Exception):
            youtube.download_video('http://fake.url')

if __name__ == '__main__':
    unittest.main()
