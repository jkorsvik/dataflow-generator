## Changelog

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