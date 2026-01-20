"""
VoxGrep Environment Doctor - Diagnoses installation and environment issues.
"""

import sys
import os
import subprocess
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()

class EnvironmentDoctor:
    """Diagnoses VoxGrep installation and environment configuration."""
    
    def __init__(self):
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.successes: List[str] = []
        
    def check_python_version(self) -> Tuple[bool, str]:
        """Check if Python version meets requirements."""
        version = sys.version_info
        required_major, required_minor = 3, 10
        
        if version.major < required_major or (version.major == required_major and version.minor < required_minor):
            return False, f"Python {version.major}.{version.minor}.{version.micro} (requires 3.10+)"
        return True, f"Python {version.major}.{version.minor}.{version.micro}"
    
    def check_package_installed(self, package_name: str, import_name: Optional[str] = None) -> bool:
        """Check if a Python package is installed."""
        try:
            spec = importlib.util.find_spec(import_name or package_name)
            return spec is not None
        except (ImportError, ModuleNotFoundError):
            return False
    
    def check_command_available(self, command: str) -> bool:
        """Check if a system command is available."""
        # Method 1: Check if executable exists in PATH
        import shutil
        if shutil.which(command) is None:
            return False

        # Method 2: Try to execute it to ensure it works
        flag = "--version"
        # ffmpeg typically uses -version, not --version
        if "ffmpeg" in command:
            flag = "-version"
            
        try:
            result = subprocess.run(
                [command, flag],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            # If execution fails but shutil.which found it, it might just be a flag issue
            # or permission issue. We'll verify one last time with just help or no args
            try:
                # ffmpeg without args returns exit code 1, but prints version info to stderr
                subprocess.run(
                    [command],
                    capture_output=True,
                    timeout=2
                )
                return True
            except:
                return False
    
    def detect_environment_type(self) -> str:
        """Detect the type of Python environment being used."""
        # Check for Poetry
        if os.getenv("POETRY_ACTIVE") == "1" or Path("poetry.lock").exists():
            return "Poetry"
        
        # Check for virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            venv_type = os.path.basename(sys.prefix)
            return f"Virtual Environment ({venv_type})"
        
        # Check for Conda
        if "CONDA_DEFAULT_ENV" in os.environ:
            return f"Conda ({os.environ['CONDA_DEFAULT_ENV']})"
        
        return "System Python (⚠️  Not recommended)"
    
    def check_core_dependencies(self) -> Dict[str, bool]:
        """Check installation status of core dependencies."""
        deps = {
            "numpy": "numpy",
            "moviepy": "moviepy",
            "fastapi": "fastapi",
            "uvicorn": "uvicorn",
            "sqlmodel": "sqlmodel",
            "rich": "rich",
            "questionary": "questionary",
            "yt-dlp": "yt_dlp",
            "beautifulsoup4": "bs4",
        }
        
        results = {}
        for package, import_name in deps.items():
            results[package] = self.check_package_installed(package, import_name)
        
        return results
    
    def check_optional_dependencies(self) -> Dict[str, bool]:
        """Check installation status of optional dependencies."""
        optional_deps = {
            "faster-whisper": "faster_whisper",
            "mlx-whisper": "mlx_whisper",
            "sentence-transformers": "sentence_transformers",
            "torch": "torch",
            "spacy": "spacy",
            "pyannote.audio": "pyannote.audio",
            "openai": "openai",
        }
        
        results = {}
        for package, import_name in optional_deps.items():
            results[package] = self.check_package_installed(package, import_name)
        
        return results
    
    def check_system_commands(self) -> Dict[str, bool]:
        """Check availability of required system commands."""
        commands = {
            "ffmpeg": "Required for video processing",
            "mpv": "Optional - for preview functionality",
        }
        
        results = {}
        # FFmpeg check
        results["ffmpeg"] = self.check_command_available("ffmpeg")
        
        # MPV check using utility
        from ..utils import mpv_utils
        results["mpv"] = mpv_utils.check_mpv_available()
        
        return results
    
    def check_data_directory(self) -> Tuple[bool, str]:
        """Check if VoxGrep data directory is accessible."""
        try:
            from ..utils.config import get_data_dir
            data_dir = get_data_dir()
            
            # Try to create if it doesn't exist
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write access
            test_file = data_dir / ".voxgrep_test"
            test_file.write_text("test")
            test_file.unlink()
            
            return True, str(data_dir)
        except Exception as e:
            return False, f"Error: {e}"
    
    def get_installation_method(self) -> str:
        """Determine how VoxGrep was installed."""
        # Check if running from source
        voxgrep_file = Path(__file__).parent
        if (voxgrep_file.parent / "pyproject.toml").exists():
            return "Source (Development)"
        
        # Check if installed via pip
        try:
            import pkg_resources
            dist = pkg_resources.get_distribution("voxgrep")
            return f"pip ({dist.version})"
        except:
            pass
        
        return "Unknown"
    
    def run_diagnosis(self) -> bool:
        """Run full environment diagnosis and display results."""
        console.print("\n[bold cyan]🔍 VoxGrep Environment Doctor[/bold cyan]\n")
        console.print("Analyzing your installation...\n")
        
        # Environment Information
        env_table = Table(title="Environment Information", box=box.ROUNDED, show_header=True)
        env_table.add_column("Check", style="cyan")
        env_table.add_column("Status", style="white")
        
        # Python Version
        py_ok, py_info = self.check_python_version()
        env_table.add_row(
            "Python Version",
            f"[green]✓[/green] {py_info}" if py_ok else f"[red]✗[/red] {py_info}"
        )
        if not py_ok:
            self.issues.append("Python version too old. Please upgrade to Python 3.10 or later.")
        else:
            self.successes.append(f"Python version: {py_info}")
        
        # Environment Type
        env_type = self.detect_environment_type()
        env_table.add_row("Environment", env_type)
        if "System Python" in env_type:
            self.warnings.append("Using system Python. Consider using Poetry or a virtual environment.")
        
        # Installation Method
        install_method = self.get_installation_method()
        env_table.add_row("Installation Method", install_method)
        
        # Data Directory
        data_ok, data_path = self.check_data_directory()
        env_table.add_row(
            "Data Directory",
            f"[green]✓[/green] {data_path}" if data_ok else f"[red]✗[/red] {data_path}"
        )
        if not data_ok:
            self.issues.append(f"Cannot access data directory: {data_path}")
        
        console.print(env_table)
        console.print()
        
        # Core Dependencies
        deps_table = Table(title="Core Dependencies", box=box.ROUNDED, show_header=True)
        deps_table.add_column("Package", style="cyan")
        deps_table.add_column("Status", style="white")
        
        core_deps = self.check_core_dependencies()
        for package, installed in core_deps.items():
            deps_table.add_row(
                package,
                "[green]✓ Installed[/green]" if installed else "[red]✗ Missing[/red]"
            )
            if not installed:
                self.issues.append(f"Missing core dependency: {package}")
        
        console.print(deps_table)
        console.print()
        
        # Optional Dependencies
        opt_table = Table(title="Optional Dependencies (AI Features)", box=box.ROUNDED, show_header=True)
        opt_table.add_column("Package", style="cyan")
        opt_table.add_column("Status", style="white")
        opt_table.add_column("Feature", style="dim")
        
        optional_features = {
            "faster-whisper": "CPU/CUDA Transcription",
            "mlx-whisper": "MLX (Apple Silicon) Transcription",
            "sentence-transformers": "Semantic Search",
            "torch": "AI/ML (Required for Semantic Search)",
            "spacy": "NLP Features",
            "pyannote.audio": "Speaker Diarization",
            "openai": "OpenAI API Integration",
        }
        
        optional_deps = self.check_optional_dependencies()
        for package, installed in optional_deps.items():
            opt_table.add_row(
                package,
                "[green]✓ Installed[/green]" if installed else "[dim]- Not installed[/dim]",
                optional_features.get(package, "")
            )
        
        console.print(opt_table)
        console.print()
        
        # System Commands
        sys_table = Table(title="System Commands", box=box.ROUNDED, show_header=True)
        sys_table.add_column("Command", style="cyan")
        sys_table.add_column("Status", style="white")
        sys_table.add_column("Purpose", style="dim")
        
        system_commands = self.check_system_commands()
        command_purposes = {
            "ffmpeg": "Required for video processing",
            "mpv": "Optional - for preview functionality",
        }
        
        for command, available in system_commands.items():
            sys_table.add_row(
                command,
                "[green]✓ Available[/green]" if available else "[red]✗ Not found[/red]",
                command_purposes.get(command, "")
            )
            if command == "ffmpeg" and not available:
                self.issues.append("FFmpeg not found. Install it for video processing.")
            elif command == "mpv" and not available:
                self.warnings.append("MPV not found. Preview functionality will be unavailable.")
        
        console.print(sys_table)
        console.print()
        
        # Summary
        self._display_summary()
        
        return len(self.issues) == 0
    
    def _display_summary(self):
        """Display diagnosis summary."""
        from ..utils import mpv_utils
        
        if len(self.issues) == 0:
            panel = Panel(
                Text.assemble(
                    ("✓ All checks passed!\n\n", "bold green"),
                    ("Your VoxGrep installation is healthy and ready to use.", "white")
                ),
                title="Diagnosis Complete",
                border_style="green",
                box=box.ROUNDED
            )
            console.print(panel)
        else:
            summary_text = Text()
            
            if self.issues:
                summary_text.append("Critical Issues:\n", style="bold red")
                for issue in self.issues:
                    summary_text.append(f"  • {issue}\n", style="red")
                summary_text.append("\n")
            
            if self.warnings:
                summary_text.append("Warnings:\n", style="bold yellow")
                for warning in self.warnings:
                    summary_text.append(f"  • {warning}\n", style="yellow")
                summary_text.append("\n")
            
            # Add recommended fixes
            summary_text.append("Recommended Actions:\n", style="bold cyan")
            
            if any("Missing core dependency" in issue for issue in self.issues):
                summary_text.append("  1. Install missing dependencies:\n", style="cyan")
                summary_text.append("     pip install 'voxgrep[full]'\n", style="white")
                summary_text.append("     OR\n", style="dim")
                summary_text.append("     poetry install --extras full\n\n", style="white")
            
            if any("FFmpeg" in issue for issue in self.issues):
                summary_text.append("  2. Install FFmpeg:\n", style="cyan")
                summary_text.append("     macOS: brew install ffmpeg\n", style="white")
                summary_text.append("     Ubuntu: sudo apt install ffmpeg\n", style="white")
                summary_text.append("     Windows: https://ffmpeg.org/download.html\n\n", style="white")
            
            if any("MPV not found" in warning for warning in self.warnings):
                summary_text.append("  3. Install MPV (Optional but recommended for preview):\n", style="cyan")
                inst_lines = mpv_utils.get_mpv_install_instructions().split("\n")[1:] # Skip first line "MPV is not installed"
                for line in inst_lines:
                     summary_text.append(f"     {line.strip()}\n", style="white")
                summary_text.append("\n")
            
            if any("Python version" in issue for issue in self.issues):
                summary_text.append("  3. Upgrade Python to 3.10 or later\n\n", style="cyan")
            
            panel = Panel(
                summary_text,
                title="Diagnosis Results",
                border_style="yellow",
                box=box.ROUNDED
            )
            console.print(panel)


def run_doctor():
    """Entry point for the doctor command."""
    doctor = EnvironmentDoctor()
    success = doctor.run_diagnosis()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(run_doctor())
