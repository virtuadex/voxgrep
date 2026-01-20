# VoxGrep Windows Installer
# One-command installation script for VoxGrep on Windows
# Usage: .\installvoxgrep.ps1

param(
    [switch]$SkipPython,
    [switch]$SkipBinaries,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-Step { Write-Host "`n▶ $args" -ForegroundColor Magenta }

# Banner
Write-Host @"

╔══════════════════════════════════════════════════════════╗
║                                                          ║
║  VoxGrep Installer for Windows                          ║
║  Automated installation of VoxGrep and dependencies     ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

# Check if running in correct directory
if (-not (Test-Path "pyproject.toml")) {
    Write-Error "Error: pyproject.toml not found!"
    Write-Error "Please run this script from the VoxGrep root directory."
    exit 1
}

# ============================================================================
# STEP 1: Check Python Version
# ============================================================================
Write-Step "Step 1/5: Checking Python installation..."

if (-not $SkipPython) {
    $validPythonFound = $false
    
    # Method 1: Check 'py' launcher (best for Windows)
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $pyList = py --list 2>&1
        if ($pyList -match " 3\.(10|11|12)") {
            Write-Success "✓ Compatible Python version found via py launcher"
            $validPythonFound = $true
        }
    }
    
    # Method 2: Check default 'python' command
    if (-not $validPythonFound) {
        try {
            $pythonVersion = python --version 2>&1
            if ($pythonVersion -match "Python 3\.(10|11|12)") {
                Write-Success "✓ Default Python version is compatible ($pythonVersion)"
                $validPythonFound = $true
            }
        } catch {}
    }

    if (-not $validPythonFound) {
        # Check if we are stuck with only 3.13+
        $hasNewer = $false
        try {
            if ((python --version 2>&1) -match "Python 3\.13") { $hasNewer = $true }
        } catch {}

        if ($hasNewer) {
            Write-Warning "⚠ Warning: Python 3.13 detected as default!"
            Write-Warning "  VoxGrep needs Python 3.10-3.12 for AI libraries."
            Write-Warning "  If you have them installed (e.g. via 'py'), we will try to use them."
            Write-Host ""
            if ($Host.UI.PromptForChoice) {
                $continue = Read-Host "Continue anyway? (y/N)"
                if ($continue -ne "y" -and $continue -ne "Y") { exit 1 }
            }
        } else {
            Write-Error "✗ No compatible Python version (3.10-3.12) found."
            Write-Error "  Please install Python 3.10 from: https://www.python.org/downloads/"
            exit 1
        }
    }
}

# ============================================================================
# STEP 2: Install Poetry
# ============================================================================
Write-Step "Step 2/5: Installing Poetry..."

try {
    $poetryVersion = poetry --version 2>&1
    Write-Success "✓ Poetry already installed: $poetryVersion"
}
catch {
    Write-Info "Poetry not found. Installing..."
    try {
        pip install poetry
        Write-Success "✓ Poetry installed successfully"
    }
    catch {
        Write-Error "✗ Failed to install Poetry"
        Write-Error "  Error: $_"
        exit 1
    }
}

# Configure Poetry to use correct Python version
Write-Info "Configuring Poetry environment..."
try {
    # Try to tell poetry to use 'py -3.10' etc if available, or fall back to 'python'
    $versions = @("3.10", "3.11", "3.12")
    $configured = $false
    
    foreach ($v in $versions) {
        if ((Get-Command py -ErrorAction SilentlyContinue) -and (py --list | Select-String " $v")) {
             # Explicitly point poetry to the py launcher version path would be ideal, 
             # but 'poetry env use 3.10' handles this if the version is on path.
        }
        
        try {
            poetry env use $v 2>&1 | Out-Null
            Write-Success "✓ Poetry configured to use Python $v"
            $configured = $true
            break
        } catch {}
    }
    
    if (-not $configured) {
        Write-Warning "⚠ Could not force specific Python version. Using default."
    }
}
catch {
    Write-Warning "⚠ Poetry configuration issue: $_"
}

# ============================================================================
# STEP 3: Download FFmpeg and mpv
# ============================================================================
Write-Step "Step 3/5: Checking system tools..."

if (-not $SkipBinaries) {
    # Helper to check if command exists in PATH
    function Test-Command ($cmd) {
        return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
    }

    $ffmpegReady = (Test-Path "ffmpeg.exe") -or (Test-Command "ffmpeg")
    $mpvReady = (Test-Path "mpv.exe") -or (Test-Command "mpv")
    
    if ($ffmpegReady -and $mpvReady) {
        Write-Success "✓ FFmpeg and mpv found (in PATH or local)"
    }
    else {
        Write-Info "Downloading missing tools..."
        
        # Download mpv
        if (-not $mpvReady) {
            Write-Info "  → Downloading mpv..."
            try {
                $mpvUrl = "https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20260120/mpv-x86_64-v3-20260120-git-b7e8fe9.7z"
                $mpvArchive = "mpv.7z"
                Invoke-WebRequest -Uri $mpvUrl -OutFile $mpvArchive -UseBasicParsing
                
                if (Get-Command 7z -ErrorAction SilentlyContinue) {
                    7z e $mpvArchive "mpv.exe" -y | Out-Null
                    del $mpvArchive
                    Write-Success "  ✓ mpv installed locally"
                } else {
                    Write-Warning "  ⚠ 7zip not found. Extract '$mpvArchive' manually here."
                }
            } catch {
                Write-Warning "  ⚠ mpv download failed: $_"
            }
        }

        # Download FFmpeg
        if (-not $ffmpegReady) {
            Write-Info "  → Downloading FFmpeg..."
            try {
                $ffmpegUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
                $ffmpegArchive = "ffmpeg.zip"
                Invoke-WebRequest -Uri $ffmpegUrl -OutFile $ffmpegArchive -UseBasicParsing
                
                Expand-Archive -Path $ffmpegArchive -DestinationPath "ffmpeg_temp" -Force
                $ffmpegExe = Get-ChildItem -Path "ffmpeg_temp" -Filter "ffmpeg.exe" -Recurse | Select-Object -First 1
                if ($ffmpegExe) {
                    Copy-Item $ffmpegExe.FullName -Destination "ffmpeg.exe"
                    Write-Success "  ✓ FFmpeg installed locally"
                }
                Remove-Item $ffmpegArchive -ErrorAction SilentlyContinue
                Remove-Item "ffmpeg_temp" -Recurse -Force -ErrorAction SilentlyContinue
            } catch {
                Write-Warning "  ⚠ FFmpeg download failed: $_"
            }
        }
    }
}
else {
    Write-Info "Skipping binary downloads (--SkipBinaries flag set)"
}

# ============================================================================
# STEP 4: Install Python Dependencies
# ============================================================================
Write-Step "Step 4/5: Installing Python dependencies..."

Write-Info "This will install VoxGrep with AI features (NLP, Diarization, OpenAI)"
Write-Info "Estimated time: 5-10 minutes (depending on your connection)"
Write-Host ""

try {
    # Install with extras, excluding Mac-only MLX
    poetry install --extras "nlp diarization openai"
    Write-Success "✓ Dependencies installed successfully"
}
catch {
    Write-Error "✗ Failed to install dependencies"
    Write-Error "  Error: $_"
    Write-Info ""
    Write-Info "You can try installing manually with:"
    Write-Info "  poetry install --extras 'nlp diarization openai'"
    exit 1
}

# ============================================================================
# STEP 5: Verify Installation
# ============================================================================
Write-Step "Step 5/5: Verifying installation..."

try {
    Write-Info "Running VoxGrep doctor..."
    poetry run voxgrep --doctor
    
    Write-Host ""
    Write-Success "╔══════════════════════════════════════════════════════════╗"
    Write-Success "║                                                          ║"
    Write-Success "║  ✓ Installation Complete!                               ║"
    Write-Success "║                                                          ║"
    Write-Success "╚══════════════════════════════════════════════════════════╝"
    Write-Host ""
    Write-Info "Quick Start:"
    Write-Info "  1. Start the backend:  poetry run python -m voxgrep.server.app"
    Write-Info "  2. Use the CLI:        poetry run voxgrep -i video.mp4 -s 'search term'"
    Write-Info "  3. Preview results:    poetry run voxgrep -i video.mp4 -s 'hello' --preview"
    Write-Host ""
    Write-Info "For more information, see: docs/GETTING_STARTED.md"
    Write-Host ""
}
catch {
    Write-Warning "⚠ Installation completed but verification failed"
    Write-Info "  You can manually verify by running: poetry run voxgrep --doctor"
}
