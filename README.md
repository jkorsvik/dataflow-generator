# Data Flow Visualization Tool

[![CI](https://img.shields.io/github/actions/workflow/status/jkorsvik/dataflow-generator/ci.yml?branch=main&label=CI)](https://github.com/jkorsvik/dataflow-generator/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/github/actions/workflow/status/jkorsvik/dataflow-generator/ci.yml?branch=main&label=Tests&job=test)](https://github.com/jkorsvik/dataflow-generator/actions/workflows/ci.yml)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![SQL](https://img.shields.io/badge/SQL-Supported-green.svg)](https://en.wikipedia.org/wiki/SQL)
[![JavaScript](https://img.shields.io/badge/JavaScript-ES6%2B-yellow.svg)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)



This tool generates interactive visual representations of data flows from SQL/VQL metadata. It supports various SQL dialects (initially focusing on PostgreSQL and Denodo VQL) and can produce both complete data flow diagrams and focused views for specified tables or views.

### Demonstration of the tool's capabilities
![Data Flow Generator Demo](https://github.com/jkorsvik/media_repo/raw/main/data-flow-generator/data-flow-generator-demo.avif)

> **Note:** The animation above demonstrates some of the tool's features and workflow. The interactive HTML allows for node editing, search, and dynamic exploration.

## Features

*   **Multi-Dialect SQL Parsing:** Supports PostgreSQL, Denodo VQL, with a pluggable architecture for adding more dialects (e.g., MySQL, SQL Server, Oracle, Snowflake, SQLite).
*   **Interactive Visualizations:** Generates HTML diagrams using Pyvis, enhanced with custom JavaScript for:
    *   **Persistent Tooltips:** Click on a node to see detailed information, including its SQL definition with syntax highlighting (via Prism.js).
    *   **Node Editing:** Interactively mark nodes for deletion, add/remove parent/child relationships, and commit these changes (logged to console for now, enabling backend integration).
    *   **Search Functionality:** Fuzzy search for nodes within the graph.
    *   **Customizable Layout:** Control panel to adjust physics, layout, and interaction settings.
    *   **Export Options:** Export full graph or selected regions as SVG or PNG.
*   **Diagram Types:**
    *   **Complete Flow:** Visualizes all identified objects and their relationships.
    *   **Focused Flow:** Shows a specific set of nodes along with their optional ancestors and descendants.
*   **User Interfaces:**
    *   **Interactive TUI:** A terminal-based user interface for guided file selection, database specification, and diagram options.
    *   **Command-Line Interface (CLI):** For batch processing and integration into automated workflows.
*   **Performance:** Optional integration with `fd`/`fdfind` for significantly faster SQL file discovery in large projects.
*   **Database Context:** Differentiates nodes based on their source database, aiding in understanding cross-database lineage.
*   **Extensible Parser System:** Easily add support for new SQL dialects.

## Installation

### Dependencies

- Python 3.12 or higher
- UV package manager

### Setup

#### Linux/macOS
```sh
source setup.sh
```

#### Windows
For PowerShell:
```powershell
.\setup.ps1
```

For Command Prompt:
```cmd
setup.bat
```

To reset the environment:

Linux/macOS:
```sh
rm -rf .venv && source setup.sh
```

Windows (PowerShell):
```powershell
Remove-Item -Recurse -Force .venv; .\setup.ps1
```

Windows (Command Prompt):
```cmd
rmdir /s /q .venv && setup.bat
```

## Optional: Speed up file search with `fd`

For large projects, file discovery is much faster if the [`fd`](https://github.com/sharkdp/fd) command-line tool is installed.  
If `fd` is not available, the tool will fall back to a pure Python implementation (which is slower for large directory trees).

**Install `fd` for your platform:**

- **macOS:**  
  `brew install fd`
- **Debian/Ubuntu:**  
  `sudo apt install fd-find`  
  (You may need to use `fdfind` instead of `fd`.)
- **Windows (with Chocolatey):**  
  `choco install fd`

If you do not install `fd`, everything will still work, but file search may be slower.



## Usage

### Interactive TUI Mode
Simply run the command after installation or from within the activated virtual environment (if developing):
```sh
dataflow
```
The TUI will guide you through:
1.  **File Selection:** Browse, drop/paste, search, or specify the path to your SQL/VQL metadata file.
    *   Supports extensions: `.sql`, `.vql`, `.ddl`, `.dml`, `.hql`, `.pls`, `.plsql`, `.proc`, `.psql`, `.tsql`, `.view`.
2.  **Main Database Selection:** If multiple databases are detected, you'll be prompted to choose a main database to normalize naming in the visualization.
3.  **Diagram Type:**
    *   **Complete:** Shows the entire data flow. Options to include/exclude edgeless nodes.
    *   **Focused:** Select specific nodes to focus on. Options to include their ancestors and/or descendants.
4.  **Auto-Open:** Choose whether to automatically open the generated HTML diagram in your browser.

Generated diagrams are saved in the `generated-image` folder within your application data directory (path displayed upon completion).

### Command-Line Interface (CLI) Mode
For non-interactive use and scripting:
```sh
dataflow-command --metadata /path/to/your/file.sql --type complete --output /path/to/output_dir --auto-open
```
Or for a focused view:
```sh
dataflow-command --metadata /path/to/your/file.vql --type focused --focus-nodes nodeA nodeB --no-ancestors --output /path/to/output_dir
```
Run `dataflow-command --help` for a full list of options.

## Development

For contributors, it's recommended to install the tool in editable mode. This allows you to modify the code and see changes immediately without reinstalling.

### Editable Installation

Activate your virtual environment and run:

```sh
uv pip install -e ".[dev]"
```

This installs the package in editable mode, making it easier to test changes during development.

### Tips for Local Development

- Ensure your virtual environment is activated before running any commands.
- Use `pytest` to continuously run tests as you make changes.
- Consider setting up linting and format checking to maintain code quality.


## Testing

The project uses pytest for testing with separate unit and integration tests. The testing setup ensures high code quality and proper functionality:

### Running Tests

With your virtual environment activated:

```sh
# Run all tests (unit + integration)
pytest

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with coverage report
pytest --cov=src --cov-report=term

# Run specific test file
pytest tests/unit/test_graph_generation.py
```

### Test Structure

1. Unit Tests (`tests/unit/`):
   - VQL parsing and graph generation
   - Node type inference and database detection
   - CLI core functionality
   - Visualization output validation
   - Error handling and edge cases

2. Integration Tests (`tests/integration/`):
   - End-to-end workflow testing
   - File generation and validation
   - Complex graph scenarios

### Coverage Requirements

A minimum of 80% code coverage is maintained across all modules. The CI pipeline enforces this requirement and generates coverage badges automatically.

## Script Overview

### Parsing `.vql` File

The script reads and parses the `.vql` file to extract metadata about views and tables. It uses regular expressions to find:
- **Views**: Matched by the pattern `CREATE OR REPLACE (INTERFACE) VIEW`.
- **Tables**: Matched by the pattern `CREATE OR REPLACE TABLE`.

Dependencies between views and tables are identified using the `FROM` and `JOIN` keywords within the view's and table's definitions.

### Database Identification

The tool now identifies database prefixes in object names (e.g., "data_market.table_name") and processes them as follows:
- Objects from the main database (selected by the user) are displayed without a prefix
- Objects from "data_market" are displayed with the prefix "datamarket."
- Objects from all other databases are displayed with the prefix "other."

This helps you quickly identify objects that come from different databases in your visualization.

### Handling Files Without Database Prefixes

If the tool does not detect any database prefixes in your VQL file, it will:
1. Use the filename as the default database name (with special characters removed)
2. Allow you to select this as the main database
3. Process all objects as if they belong to this main database

### Functions

1. **find_script_dependencies(vql_script)**:
   - Finds all the table names a `vql_script` is dependent on using the `FROM` and `JOIN` keywords.
   - Returns a list of names (dependencies in the given `vql_script`).

2. **parse_vql(file_path)**:
   - Parses the `.vql` file to extract views, tables, and their dependencies.
   - Returns a list of edges (dependencies), a dictionary of node types, and database counts.

3. **standardize_database_names(edges, node_types, main_db)**:
   - Standardizes database names based on the selected main database.
   - Formats node names to include database prefixes where appropriate.

4. **create_pyvis_figure(graph, node_types, focus_nodes=[], shake_towards_root=False)**:
   - Creates interactive Pyvis figures for the data flow diagrams.
   - Returns an interactive figure.

5. **draw_complete_data_flow(edges, node_types, save_path=None, file_name=None)**:
   - Generates and displays a complete data flow diagram.
   - Adjusts the figure size based on the number of nodes.
   - Saves the figure as `complete_data_flow_pyvis_metadata_file_name.html`.

6. **draw_focused_data_flow(edges, node_types, focus_nodes, save_path=None, file_name=None, see_ancestors=True, see_descendants=True)**:
   - Generates and displays a focused data flow diagram for the specified nodes.
   - Includes the specified nodes, their ancestors, and descendants in the subgraph if enabled.
   - Adjusts the figure size based on the number of nodes.
   - Saves the figure as `focused_data_flow_pyvis_metadata_file_name.html`.

### Main Script Execution

- Reads the `.vql` file in the metadata folder selected using the CLI-tool
- Parses the file to extract metadata (views, tables, and their dependencies).
- Prompts the user to select the main database from a list ordered by frequency.
- Standardizes node names based on database information.
- Generates and saves the complete data flow diagram if selected in the CLI-tool.
- Generates and saves the focused data flow diagram if selected in the CLI-tool.

## Project Structure

```
/data-flow-generator
    |-- pyproject.toml          # Project configuration and dependencies
    
    |-- requirements.txt        # Legacy requirements file
    |-- uv.lock                # UV lock file
    |-- src/
    |   |-- __init__.py
    |   |-- dataflow.py         # Command line interface
    |   |-- generate_data_flow.py
    |   |-- pyvis_mod.py
    |-- tests/
    |   |-- generate_data_flow_test.py
    |   |-- test_database_functions.py
    |-- metadata/              # VQL file directory
    |   |-- denodo_metadata1.vql
    |   |-- denodo_metadata2.vql
    |-- generated-image/       # Output directory
        |-- complete_data_flow_*.html
        |-- focused_data_flow_*.html
```

## Troubleshooting

- **File Not Found Error**:
  - Ensure the `.vql` file is in the metadata folder within the same directory as the script.

- **Overlapping Titles in Diagram**:
  - Increase the `SCALING_CONSTANT` value in `generate_data_flow.py` file to widen the figure.

- **Legend overlaps nodes in diagram**:
  - As the generation of the diagram is not deterministic, rerun the generation untill a desired output is achieved


If you encounter any issues or need further assistance, feel free to ask us at Insight Factory, Emerging Business Technology!


