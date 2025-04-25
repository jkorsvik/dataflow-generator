# Data Flow Visualization Tool

[![CI](https://img.shields.io/github/actions/workflow/status/jkorsvik/dataflow-generator/ci.yml?branch=main&label=CI)](https://github.com/jkorsvik/dataflow-generator/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/github/actions/workflow/status/jkorsvik/dataflow-generator/ci.yml?branch=main&label=Tests&job=test)](https://github.com/jkorsvik/dataflow-generator/actions/workflows/ci.yml)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![SQL](https://img.shields.io/badge/SQL-Supported-green.svg)](https://en.wikipedia.org/wiki/SQL)
[![JavaScript](https://img.shields.io/badge/JavaScript-ES6%2B-yellow.svg)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)


This tool generates visual representations of data flows based on Denodo metadata exported in a `.vql` file. It can produce both complete data flow diagrams and focused data flow diagrams for specified views and tables.
### Demonstration of the tool's capabilities
![Data Flow Generator Demo](https://github.com/jkorsvik/media_repo/raw/main/data-flow-generator/data-flow-generator-demo.avif)

> **Note:** The animation above demonstrates only some of the tool's features and workflow for brevity's sake.

## Installation

### Dependencies

- Python 3.10 or higher
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

1. **Install the Tool:**

   You can install the tool globally using UV:

   ```sh
   # Install globally with UV
   uv pip install . 
   ```

   Or install for your user only:

   ```sh
   # Install for current user
   uv pip install --user .
   ```

2. **Run the Tool:**

   After installation, you can run the tool from anywhere using:

   ```sh
   dataflow
   ```

   The tool provides multiple ways to select your SQL file:
   - Drop/Upload File: Simply drag and drop any SQL file into the terminal
   - Browse SQL Files: Shows a filtered list of SQL files in the directory
   - Specify file path: Enter or paste a file path directly
   - Search in directory: Search for SQL files by name

   Supported SQL file extensions:
   - `.sql` - Standard SQL files
   - `.vql` - Denodo VQL files
   - `.ddl` - Data Definition Language
   - `.dml` - Data Manipulation Language
   - `.hql` - Hive Query Language
   - `.pls`, `.plsql` - PL/SQL files
   - `.proc` - Stored Procedures
   - `.psql` - PostgreSQL files
   - `.tsql` - T-SQL files
   - `.view` - View definitions

   File Validation:
   - Automatically checks for valid SQL extensions
   - Validates file content for SQL keywords
   - Provides option to proceed with non-SQL files after confirmation

   The tool generates diagrams in the "generated-image" folder:
   - Complete flow diagram: Shows all dependencies
   - Focused flow diagram: Shows selected nodes and their relationships

   Outputs include:
   - PNG files for static visualization
   - Interactive HTML files for dynamic exploration

2. **Database Selection:**

   The tool now analyzes database names in your metadata and prompts you to select a main database. 
   Databases are presented in descending order by frequency, with the most common database listed first.

   - The main database will be displayed without a prefix in the visualization
   - Data Market objects are prefixed with "datamarket." (e.g., "datamarket.bv_datalake_d1300_currency_full")
   - All other database objects are prefixed with "other."

   This database differentiation is represented in the visualization legend with different colors.

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


