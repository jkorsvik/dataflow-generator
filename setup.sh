#!/bin/bash
# Check for fd or fdfind and recommend installation if missing

if ! command -v fd >/dev/null 2>&1 && ! command -v fdfind >/dev/null 2>&1; then
  echo ""
  echo "Optional: For much faster file search, install 'fd' (https://github.com/sharkdp/fd):"
  if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "  brew install fd"
  elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "  sudo apt install fd-find"
    echo "  (You may need to use 'fdfind' instead of 'fd')"
  elif [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]]; then
    echo "  choco install fd"
  else
    echo "  See https://github.com/sharkdp/fd for installation instructions."
  fi
  echo ""
fi



# For Linux, create venv and install uv via pip
if [[ "$(uname)" == "Linux" ]]; then
    # Create Python venv
    python3 -m venv .venv

    # Activate the venv
    source .venv/bin/activate

    # Install uv inside the venv using pip
    pip install uv

elif [[ "$(uname)" == "Darwin" ]]; then
    # For macOS, install uv system-wide using the install script
    if ! command -v uv &> /dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi

    # Create virtual environment using uv
    uv venv .venv

    # Activate the virtual environment
    source .venv/bin/activate
fi

# Install the required packages using uv
uv sync

echo "Setup complete. To activate the virtual environment, run 'source .venv/bin/activate'. To start the app, run 'dataflow'."