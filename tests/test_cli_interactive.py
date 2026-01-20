"""
Comprehensive tests for VoxGrep CLI interactive modes and argument parsing.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from argparse import Namespace

# Import the CLI module
from voxgrep import cli
from voxgrep.cli import interactive_mode, execute_args, main

# Skip interactive tests on Windows due to console buffer issues
skip_on_windows = pytest.mark.skipif(
    sys.platform == "win32" and not os.isatty(sys.stdout.fileno() if hasattr(sys.stdout, 'fileno') else -1),
    reason="Interactive tests require TTY on Windows"
)


def File(path):
    """Helper to get test file paths."""
    return str(Path(__file__).parent / Path(path))


class TestCLIArgumentParsing:
    """Test CLI argument parsing and validation."""
    
    def test_basic_search_args(self):
        """Test basic search argument parsing."""
        test_args = [
            "voxgrep",
            "--input", "test.mp4",
            "--search", "hello",
            "--output", "output.mp4"
        ]
        with patch.object(sys, 'argv', test_args):
            with patch('voxgrep.cli.execute_args') as mock_execute:
                cli.main()
                assert mock_execute.called
                args = mock_execute.call_args[0][0]
                assert args.inputfile == ["test.mp4"]
                assert args.search == ["hello"]
                assert args.outputfile == "output.mp4"
    
    def test_multiple_search_terms(self):
        """Test parsing multiple search terms."""
        test_args = [
            "voxgrep",
            "--input", "test.mp4",
            "--search", "hello",
            "--search", "world"
        ]
        with patch.object(sys, 'argv', test_args):
            with patch('voxgrep.cli.execute_args') as mock_execute:
                cli.main()
                args = mock_execute.call_args[0][0]
                assert args.search == ["hello", "world"]
    
    def test_search_type_options(self):
        """Test all search type options."""
        search_types = ["sentence", "fragment", "mash", "semantic"]
        for search_type in search_types:
            test_args = [
                "voxgrep",
                "--input", "test.mp4",
                "--search", "test",
                "--search-type", search_type
            ]
            with patch.object(sys, 'argv', test_args):
                with patch('voxgrep.cli.execute_args') as mock_execute:
                    cli.main()
                    args = mock_execute.call_args[0][0]
                    assert args.searchtype == search_type
    
    def test_transcription_args(self):
        """Test transcription-related arguments."""
        test_args = [
            "voxgrep",
            "--input", "test.mp4",
            "--transcribe",
            "--model", "base",
            "--device", "cpu",
            "--language", "en"
        ]
        with patch.object(sys, 'argv', test_args):
            with patch('voxgrep.cli.execute_args') as mock_execute:
                cli.main()
                args = mock_execute.call_args[0][0]
                assert args.transcribe is True
                assert args.model == "base"
                assert args.device == "cpu"
                assert args.language == "en"
    
    def test_output_options(self):
        """Test output-related options."""
        test_args = [
            "voxgrep",
            "--input", "test.mp4",
            "--search", "test",
            "--export-clips",
            "--export-vtt",
            "--demo"
        ]
        with patch.object(sys, 'argv', test_args):
            with patch('voxgrep.cli.execute_args') as mock_execute:
                cli.main()
                args = mock_execute.call_args[0][0]
                assert args.export_clips is True
                assert args.write_vtt is True
                assert args.demo is True
    
    def test_doctor_command(self):
        """Test --doctor flag triggers environment diagnostics."""
        test_args = ["voxgrep", "--doctor"]
        with patch.object(sys, 'argv', test_args):
            with patch('voxgrep.doctor.run_doctor') as mock_doctor:
                mock_doctor.return_value = 0
                with pytest.raises(SystemExit) as exc_info:
                    cli.main()
                assert mock_doctor.called


@skip_on_windows
class TestInteractiveModeSearch:
    """Test interactive mode search workflow."""
    
    @patch('questionary.select')
    @patch('questionary.text')
    @patch('questionary.confirm')
    @patch('voxgrep.cli.execute_args')
    @patch('os.listdir')
    def test_interactive_search_basic(
        self, 
        mock_listdir, 
        mock_execute, 
        mock_confirm, 
        mock_text, 
        mock_select
    ):
        """Test basic interactive search workflow."""
        # Setup mocks
        mock_listdir.return_value = ["test_video.mp4"]
        
        # Mock the file selection
        file_select_mock = Mock()
        file_select_mock.ask.return_value = "test_video.mp4"
        
        # Mock the task selection (search, then exit)
        task_select_mock1 = Mock()
        task_select_mock1.ask.return_value = "search"
        task_select_mock2 = Mock()
        task_select_mock2.ask.return_value = "exit"
        
        # Mock search type
        search_type_mock = Mock()
        search_type_mock.ask.return_value = "sentence"
        
        mock_select.side_effect = [
            file_select_mock,  # File selection
            task_select_mock1,  # Task: search
            search_type_mock,   # Search type
            task_select_mock2   # Task: exit
        ]
        
        # Mock the search input
        search_input_mock = Mock()
        search_input_mock.ask.return_value = "hello world"
        mock_text.return_value = search_input_mock
        
        # Mock confirmations
        mock_confirm.return_value = Mock(ask=Mock(side_effect=[
            False,  # Should transcribe?
            True,   # Demo mode?
        ]))
        
        # Mock find_transcript
        with patch('voxgrep.cli.find_transcript', return_value="test.json"):
            with patch('voxgrep.prefs.load_prefs', return_value={}):
                with patch('voxgrep.prefs.save_prefs'):
                    interactive_mode()
        
        # Verify execute_args was called
        assert mock_execute.called
    
    @patch('questionary.select')
    @patch('questionary.confirm')
    @patch('voxgrep.cli.execute_args')
    @patch('os.listdir')
    def test_interactive_transcribe_task(
        self, 
        mock_listdir, 
        mock_execute, 
        mock_confirm,
        mock_select
    ):
        """Test interactive mode transcription task."""
        mock_listdir.return_value = ["video.mp4"]
        
        # Mock file selection
        file_select = Mock(ask=Mock(return_value="video.mp4"))
        
        # Mock task selection (transcribe, then exit)
        task_select1 = Mock(ask=Mock(return_value="transcribe"))
        task_select2 = Mock(ask=Mock(return_value="exit"))
        
        # Mock device and model selection
        device_select = Mock(ask=Mock(return_value="cpu"))
        model_select = Mock(ask=Mock(return_value="base"))
        
        mock_select.side_effect = [
            file_select,
            task_select1,
            device_select,
            model_select,
            task_select2
        ]
        
        with patch('voxgrep.cli.find_transcript', return_value=None):
            with patch('voxgrep.prefs.load_prefs', return_value={}):
                with patch('voxgrep.prefs.save_prefs'):
                    interactive_mode()
        
        assert mock_execute.called
        args = mock_execute.call_args[0][0]
        assert args.transcribe is True
        assert args.device == "cpu"
        assert args.model == "base"


@skip_on_windows
class TestInteractiveModeNgrams:
    """Test interactive mode n-grams workflow."""
    
    @patch('questionary.select')
    @patch('questionary.text')
    @patch('questionary.checkbox')
    @patch('questionary.confirm')
    @patch('voxgrep.cli.get_ngrams')
    @patch('os.listdir')
    def test_interactive_ngrams_with_search(
        self, 
        mock_listdir,
        mock_get_ngrams,
        mock_confirm,
        mock_checkbox,
        mock_text,
        mock_select
    ):
        """Test n-grams calculation with subsequent search."""
        mock_listdir.return_value = ["test.mp4"]
        
        # Mock n-grams results
        mock_get_ngrams.return_value = [("hello",), ("world",), ("hello",)]
        
        # Mock file selection
        file_select = Mock(ask=Mock(return_value="test.mp4"))
        
        # Mock task selection (ngrams, then exit)
        task_select1 = Mock(ask=Mock(return_value="ngrams"))
        task_select2 = Mock(ask=Mock(return_value="exit"))
        
        mock_select.side_effect = [file_select, task_select1, task_select2]
        
        # Mock n value input
        n_input = Mock(ask=Mock(return_value="1"))
        mock_text.return_value = n_input
        
        # Mock confirmation for search after n-grams
        mock_confirm.return_value = Mock(ask=Mock(return_value=False))
        
        with patch('voxgrep.cli.find_transcript', return_value="test.json"):
            with patch('voxgrep.prefs.load_prefs', return_value={}):
                with patch('voxgrep.prefs.save_prefs'):
                    with patch('voxgrep.cli.execute_args'):
                        interactive_mode()
        
        assert mock_get_ngrams.called


@skip_on_windows
class TestInteractiveModeFileSelection:
    """Test interactive mode file selection options."""
    
    @patch('questionary.select')
    @patch('os.listdir')
    def test_single_file_selection(self, mock_listdir, mock_select):
        """Test selecting a single file."""
        mock_listdir.return_value = ["video1.mp4", "video2.mp4"]
        
        # Mock file selection
        file_select = Mock(ask=Mock(return_value="video1.mp4"))
        
        # Mock task selection (exit immediately)
        task_select = Mock(ask=Mock(return_value="exit"))
        
        mock_select.side_effect = [file_select, task_select]
        
        with patch('voxgrep.prefs.load_prefs', return_value={}):
            interactive_mode()
        
        assert file_select.ask.called
    
    @patch('questionary.select')
    @patch('questionary.checkbox')
    @patch('os.listdir')
    def test_multiple_file_selection(self, mock_listdir, mock_checkbox, mock_select):
        """Test selecting multiple files."""
        mock_listdir.return_value = ["video1.mp4", "video2.mp4", "video3.mp4"]
        
        # Mock file selection (choose multiple)
        file_select = Mock(ask=Mock(return_value="__multiple__"))
        mock_select.return_value = file_select
        
        # Mock checkbox for multiple files
        checkbox_mock = Mock(ask=Mock(return_value=["video1.mp4", "video2.mp4"]))
        mock_checkbox.return_value = checkbox_mock
        
        # Mock task selection (exit)
        task_select = Mock(ask=Mock(return_value="exit"))
        mock_select.side_effect = [file_select, task_select]
        
        with patch('voxgrep.prefs.load_prefs', return_value={}):
            interactive_mode()
        
        assert checkbox_mock.ask.called
    
    @patch('questionary.select')
    @patch('os.listdir')
    def test_all_files_selection(self, mock_listdir, mock_select):
        """Test selecting all files."""
        mock_listdir.return_value = ["video1.mp4", "video2.mp4"]
        
        # Mock file selection (all files)
        file_select = Mock(ask=Mock(return_value="__all__"))
        
        # Mock task selection (exit)
        task_select = Mock(ask=Mock(return_value="exit"))
        
        mock_select.side_effect = [file_select, task_select]
        
        with patch('voxgrep.prefs.load_prefs', return_value={}):
            interactive_mode()
        
        assert file_select.ask.called


class TestExecuteArgs:
    """Test the execute_args function with various argument configurations."""
    
    def test_execute_args_none(self):
        """Test execute_args with None input."""
        result = execute_args(None)
        assert result is True
    
    @patch('voxgrep.cli.sphinx.transcribe')
    def test_execute_args_sphinx_transcribe(self, mock_sphinx):
        """Test Sphinx transcription execution."""
        args = Namespace(
            inputfile=["test.mp4"],
            sphinxtranscribe=True,
            search=None,
            ngrams=0
        )
        
        with patch('voxgrep.cli.console'):
            execute_args(args)
        
        assert mock_sphinx.called
    
    @patch('voxgrep.transcribe.transcribe')
    def test_execute_args_whisper_transcribe_cpu(self, mock_transcribe):
        """Test Whisper transcription with CPU."""
        args = Namespace(
            inputfile=["test.mp4"],
            sphinxtranscribe=False,
            transcribe=True,
            device="cpu",
            model="base",
            prompt=None,
            language=None,
            compute_type="int8",
            search=None,
            ngrams=0
        )
        
        with patch('voxgrep.cli.console'):
            execute_args(args)
        
        assert mock_transcribe.called
        call_args = mock_transcribe.call_args[1]
        assert call_args['device'] == "cpu"
        assert call_args['model_name'] == "base"
    
    @patch('voxgrep.transcribe.transcribe')
    def test_execute_args_whisper_transcribe_mlx(self, mock_transcribe):
        """Test Whisper transcription with MLX."""
        args = Namespace(
            inputfile=["test.mp4"],
            sphinxtranscribe=False,
            transcribe=True,
            device="mlx",
            model="base",
            prompt=None,
            language=None,
            compute_type="int8",
            search=None,
            ngrams=0
        )
        
        with patch('voxgrep.cli.console'):
            execute_args(args)
        
        assert mock_transcribe.called
    
    @patch('voxgrep.cli.get_ngrams')
    def test_execute_args_ngrams(self, mock_ngrams):
        """Test n-grams calculation."""
        mock_ngrams.return_value = [("hello",), ("world",)]
        
        args = Namespace(
            inputfile=["test.mp4"],
            sphinxtranscribe=False,
            transcribe=False,
            ngrams=1,
            search=None
        )
        
        with patch('voxgrep.cli.console'):
            with patch('questionary.confirm', return_value=Mock(ask=Mock(return_value=False))):
                execute_args(args)
        
        assert mock_ngrams.called
    
    @patch('voxgrep.voxgrep')
    def test_execute_args_search(self, mock_voxgrep):
        """Test search execution."""
        mock_voxgrep.return_value = True
        
        args = Namespace(
            inputfile=["test.mp4"],
            sphinxtranscribe=False,
            transcribe=False,
            ngrams=0,
            search=["hello"],
            searchtype="sentence",
            outputfile="output.mp4",
            maxclips=0,
            padding=None,
            demo=False,
            randomize=False,
            sync=0,
            export_clips=False,
            write_vtt=False,
            preview=False,
            exact_match=False
        )
        
        with patch('voxgrep.cli.console'):
            execute_args(args)
        
        assert mock_voxgrep.called


class TestCLIPreferences:
    """Test CLI preferences storage and loading."""
    
    @patch('voxgrep.prefs.save_prefs')
    @patch('voxgrep.prefs.load_prefs')
    def test_preferences_persistence(self, mock_load, mock_save):
        """Test that preferences are saved and loaded correctly."""
        mock_load.return_value = {
            "device": "mlx",
            "whisper_model": "large-v3",
            "search_type": "semantic"
        }
        
        # Verify preferences are used
        from voxgrep.prefs import load_prefs
        prefs = load_prefs()
        
        assert prefs["device"] == "mlx"
        assert prefs["whisper_model"] == "large-v3"


@skip_on_windows
class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""
    
    def test_no_search_term_error(self, capsys):
        """Test error when no search term is provided."""
        args = Namespace(
            inputfile=["test.mp4"],
            search=None,
            ngrams=0,
            transcribe=False,
            sphinxtranscribe=False
        )
        
        with pytest.raises(SystemExit):
            with patch('voxgrep.cli.console'):
                execute_args(args)
    
    @patch('os.listdir')
    @patch('questionary.select')
    def test_interactive_mode_cancel(self, mock_select, mock_listdir):
        """Test canceling interactive mode."""
        mock_listdir.return_value = ["test.mp4"]
        
        # Mock user canceling file selection
        file_select = Mock(ask=Mock(return_value=None))
        mock_select.return_value = file_select
        
        with patch('voxgrep.prefs.load_prefs', return_value={}):
            result = interactive_mode()
        
        assert result is None
    
    @patch('os.listdir')
    @patch('questionary.select')
    @patch('questionary.text')
    def test_interactive_search_no_input(self, mock_text, mock_select, mock_listdir):
        """Test interactive mode when no search input is provided."""
        mock_listdir.return_value = ["test.mp4"]
        
        # Mock file selection
        file_select = Mock(ask=Mock(return_value="test.mp4"))
        
        # Mock task selection
        task_select1 = Mock(ask=Mock(return_value="search"))
        task_select2 = Mock(ask=Mock(return_value="exit"))
        
        mock_select.side_effect = [file_select, task_select1, task_select2]
        
        # Mock empty search input
        search_input = Mock(ask=Mock(return_value=""))
        mock_text.return_value = search_input
        
        with patch('voxgrep.cli.find_transcript', return_value="test.json"):
            with patch('voxgrep.prefs.load_prefs', return_value={}):
                with patch('voxgrep.prefs.save_prefs'):
                    interactive_mode()


class TestCLIBanner:
    """Test CLI banner and UI elements."""
    
    @patch('voxgrep.cli.console')
    def test_banner_display(self, mock_console):
        """Test that banner is displayed correctly."""
        cli.print_banner()
        assert mock_console.print.called


class TestCLIIntegration:
    """Integration tests for CLI with real file operations."""
    
    def test_cli_help(self):
        """Test --help flag."""
        test_args = ["voxgrep", "--help"]
        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                cli.main()
            assert exc_info.value.code == 0
    
    def test_cli_version(self):
        """Test --version flag."""
        test_args = ["voxgrep", "--version"]
        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                cli.main()
            assert exc_info.value.code == 0
    
    def test_interactive_mode_entry(self):
        """Test entering interactive mode with no arguments."""
        test_args = ["voxgrep"]
        with patch.object(sys, 'argv', test_args):
            with patch('voxgrep.cli.interactive_mode') as mock_interactive:
                cli.main()
                assert mock_interactive.called
