import platformdirs
from pathlib import Path
import json

APP_NAME = "DataFlowGenerator"
APP_AUTHOR = "jkorsvik"  # Use author name or organization

# Base directory for application data
APP_DATA_DIR = Path(platformdirs.user_data_dir(APP_NAME, APP_AUTHOR))
DATA_FLOW_BASE_DIR = APP_DATA_DIR / "data-flow-data"

# Settings file for persistent user preferences
SETTINGS_FILE = APP_DATA_DIR / "settings.json"

# Specific subdirectories
METADATA_DIR = DATA_FLOW_BASE_DIR / "metadata"
JSON_STRUCTURE_DIR = DATA_FLOW_BASE_DIR / "json_structure"
GENERATED_IMAGE_DIR = DATA_FLOW_BASE_DIR / "generated-image"

# List of all directories managed by this utility
MANAGED_DIRS = [
    DATA_FLOW_BASE_DIR,
    METADATA_DIR,
    JSON_STRUCTURE_DIR,
    GENERATED_IMAGE_DIR,
]

def ensure_data_dirs_exist():
    """Creates all necessary application data directories if they don't exist."""
    for dir_path in MANAGED_DIRS:
        dir_path.mkdir(parents=True, exist_ok=True)

def read_settings():
    """Read persistent settings from the settings file."""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def write_settings(settings: dict):
    """Write persistent settings to the settings file."""
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not write settings file: {e}")

# Ensure directories exist upon module import
ensure_data_dirs_exist()

if __name__ == "__main__":
    # Example usage/test: Print the paths
    print(f"User Data Directory: {APP_DATA_DIR}")
    print(f"Data Flow Base Directory: {DATA_FLOW_BASE_DIR}")
    print(f"Metadata Directory: {METADATA_DIR}")
    print(f"JSON Structure Directory: {JSON_STRUCTURE_DIR}")
    print(f"Generated Image Directory: {GENERATED_IMAGE_DIR}")
    print(f"Settings File: {SETTINGS_FILE}")
    print("\nEnsured all directories exist.")
