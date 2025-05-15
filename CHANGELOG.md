## Changelog
### 0.2.2 (2025-05-15)
- **Enhanced Pyvis Node Interaction:**
    - Successfully implemented robust node deletion, including handling for nodes with and without connections, and providing an "Undo Delete Mark" feature before committing.
    - Resolved UI update issues related to the "Delete Node" action, ensuring the "Commit Changes" button, "Undo Delete Mark" button text, and warning messages now appear correctly and consistently for all nodes.
    - Stabilized the persistent tooltip's drag functionality and event handling within the tooltip to prevent unintended actions.
    - Confirmed SQL definition content is correctly passed to and displayed within the persistent (on-click) node tooltip.
    - Ensured Prism.js correctly highlights SQL syntax within the persistent tooltip's definition view.
- Refactor key bindings for navigation and update user prompts; enhance draw_pyvis_html function to return status
- Implement feature X to enhance user experience and fix bug Y in module Z
- Enhance node edit UI with improved commit button and warning area; remove deleted node styling in CSS
- Refactor code structure for improved readability and maintainability
- Add section for edits and drop script generation in wishes.md
- Add 'dist/' to .gitignore to exclude distribution files
- Update Python version requirement to 3.12 and enhance keywords in pyproject.toml; add missing __init__.py file
- return None or html str in draw_pyvis_html function to prevent unintended behavior

### 0.2.1 (2025-05-06)
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