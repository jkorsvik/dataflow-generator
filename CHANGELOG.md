## Changelog
### 0.2.3 (2025-05-16)
- Include all static assets (CSS, JS, images, etc.) in the `src` directory in the package distribution for correct Pyvis HTML rendering and asset availability after installation.
- Update MANIFEST.in to recursively include common static file types in `src/`.

### 0.2.2 (2025-05-15)
- Added MVP PostgreSQL parser for initial SQL dump support
- Added option to omit edits from console output (enables integration with web/desktop app, "dataflow-app")


### 0.2.0 (2025-04-25)
- Added automatic detection and optional installation of `fd`/`fdfind` for fast file search
- User is prompted to install `fd` if not found, with persistent opt-out stored in app data directory
- File search logic now respects user preference and falls back to Python search if declined
- Added persistent settings storage in `src/path_utils.py`
- Refactored `collect_sql_files` to use new fd installation logic

### 0.1.9 (2025-04-25)
- Fixed Python module import issues in the CLI tools
- Added fallback import mechanism to handle both installed package and source use cases
- Updated package structure in pyproject.toml for proper installation
- Improved test environment with conftest.py for better path handling

### 0.1.8 (2025-04-25)
- Add MANIFEST.in for improved packaging
- Update pyproject.toml for SPDX license and packaging improvements
- Initialize __init__.py for parsers module

### 0.1.5 (2025-04-25)
- Added browser auto-open feature for generated diagrams
- Made browser auto-open configurable via both CLI and command-line interface
- Added `--auto-open` and `--no-auto-open` flags to command-line interface
- Improved cross-platform compatibility for file path handling
- Enhanced back navigation with ESC and Ctrl+C support

### 0.1.4 (2025-04-24)
- Added command and path handling for files.

### 0.1.3 (2025-04-24)
- Minor changes and improvements.

### 0.1.2 (2025-04-24)
- Added dynamic CI and test status badges to the README using shields.io
- Improved README documentation for installation, usage, and development
- Enforced a minimum code coverage threshold in CI (coverage must be ≥40%)
- CI now generates and uploads coverage and test badges
- Updated test and lint workflows for better reliability and caching
- Minor documentation and metadata improvements

### 0.1.1 (2025-04-24)
- Bumped project version to 0.1.1
- Added keywords and long_description_content_type in pyproject.toml for PyPI
- Switched CI publish step to use Twine upload