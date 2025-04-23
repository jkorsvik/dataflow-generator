#!/bin/bash

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