# PowerShell script for Windows setup

# Check for fd and recommend installation if missing
$fd = Get-Command fd -ErrorAction SilentlyContinue
if (-not $fd) {
    Write-Host ""
    Write-Host "Optional: For much faster file search, install 'fd' (https://github.com/sharkdp/fd):"
    Write-Host "  winget install sharkdp.fd"
    Write-Host "  (or) choco install fd"
    Write-Host "  (or) scoop install fd"
    Write-Host ""
}

# Check if Python is installed
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not found. Please install Python 3.10 or newer."
    exit 1
}

# Create Python virtual environment
Write-Host "Creating Python virtual environment..."
python -m venv .venv

# Activate the virtual environment
Write-Host "Activating virtual environment..."
& .\.venv\Scripts\Activate.ps1

# Check if uv is installed
$uvInstalled = $null
try {
    $uvInstalled = Get-Command uv -ErrorAction SilentlyContinue
}
catch {
    # Do nothing, we'll install uv
}

if (-not $uvInstalled) {
    Write-Host "Installing uv package manager..."
    # Install uv using pip first
    pip install uv
}

# Run uv sync to install dependencies
Write-Host "Installing dependencies using uv..."
uv sync

Write-Host "Setup complete. To activate the virtual environment, run '.\venv\Scripts\Activate.ps1'. To start the app, run 'data-flow-generator'."
