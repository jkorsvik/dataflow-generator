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

$venvPath = ".\.venv"
$activateScriptPath = Join-Path $venvPath "Scripts\Activate.ps1"

# Remove existing virtual environment if it exists, to ensure a clean state
if (Test-Path $venvPath -PathType Container) {
    Write-Host "Removing existing virtual environment at '$venvPath'..."
    try {
        Remove-Item -Recurse -Force $venvPath -ErrorAction Stop
        Write-Host "Successfully removed existing virtual environment."
    }
    catch {
        Write-Error "Failed to remove existing virtual environment at '$venvPath'. Please remove it manually and try again. Error: $($_.Exception.Message)"
        exit 1
    }
}

# Create Python virtual environment
Write-Host "Creating Python virtual environment using 'python -m venv $venvPath'..."
python -m venv $venvPath
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create Python virtual environment. 'python -m venv $venvPath' exited with code $LASTEXITCODE."
    Write-Error "Please check any output from the command above. Ensure your Python installation is correct and the 'venv' module is functional."
    exit 1
}

# Verify virtual environment creation
if (-not (Test-Path $activateScriptPath -PathType Leaf)) {
    Write-Error "Python virtual environment creation seems to have failed. Activation script not found at '$activateScriptPath'."
    Write-Error "Please check the output from 'python -m venv $venvPath' and ensure your Python installation is correct."
    exit 1
}
Write-Host "Virtual environment created successfully at '$venvPath'."

# Activate the virtual environment
Write-Host "Activating virtual environment..."
try {
    & $activateScriptPath
    Write-Host "Virtual environment activated."
}
catch {
    Write-Error "Failed to activate the virtual environment using '$activateScriptPath'. Error: $($_.Exception.Message)"
    exit 1
}

# Check if uv is installed (now checking within the activated venv)
$uvInstalled = $null
Write-Host "Checking for 'uv' package manager in the virtual environment..."
try {
    $uvInstalled = Get-Command uv -ErrorAction SilentlyContinue
}
catch {
    # Expected if not installed, $uvInstalled remains $null
}

if (-not $uvInstalled) {
    Write-Host "Installing 'uv' package manager into the virtual environment using 'pip install uv'..."
    pip install uv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install 'uv' using pip. Please check pip output."
        exit 1
    }
    # Verify uv installation
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Error "Failed to install 'uv' package manager or it's not in PATH after installation."
        exit 1
    }
    Write-Host "'uv' installed successfully."
} else {
    Write-Host "'uv' is already installed in the virtual environment."
}

# Run uv sync to install dependencies
Write-Host "Installing dependencies using 'uv sync --dev'..."
uv sync --dev
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install dependencies using 'uv sync --dev'. Please check the output from uv."
    exit 1
}
Write-Host "Dependencies installed successfully."

Write-Host "Setup complete."
Write-Host "To activate the virtual environment in a new terminal, run: & '$activateScriptPath'"
Write-Host "To start the app (once activated), run 'data-flow-generator'."