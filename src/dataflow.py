import os
import re
import readchar
import questionary
from colorama import init, Fore, Style, Back
import shutil
import subprocess
import platform
import json
# Fall back to relative import (when running from source)
from .generate_data_flow import (
    draw_focused_data_flow,
    draw_complete_data_flow,
    parse_dump,
)
from . import path_utils
import glob
import itertools
import threading
import sys, webbrowser
import time
from pathlib import Path
from rapidfuzz import process
from typing import List, Dict, Optional, Set, Tuple

# Constants
SQL_EXTENSIONS = [
    ".sql",  # Standard SQL files
    ".vql",  # Denodo VQL files
    ".ddl",  # Data Definition Language
    ".dml",  # Data Manipulation Language
    ".hql",  # Hive Query Language
    ".pls",  # PL/SQL files
    ".plsql",  # PL/SQL files
    ".proc",  # Stored Procedures
    ".psql",  # PostgreSQL files
    ".tsql",  # T-SQL files
    ".view",  # View definitions
]

# Initialize colorama and constants
init()

# Key bindings for back navigation
# Key bindings
BACK_KEY = "b"
ESC_KEY = "\x1b"
CTRL_C_KEY = "\x03"
CTRL_D_KEY = "\x04"  # Add Ctrl+D as another way to cancel
BACK_TOOLTIP = f"(press '{BACK_KEY}', ESC, or Ctrl+C to go back)"


def handle_back_key(key: str) -> bool:
    """Check if back navigation is requested

    Handles multiple ways to go back:
    - 'b' key (case insensitive by default)
    - ESC key
    - Ctrl+C key
    - Ctrl+D key
    - KeyboardInterrupt exceptions

    Args:
        key (str): Key pressed by user

    Returns:
        bool: True if back navigation requested
    """

    # Check if key is the designated back key or special escape keys
    # Always convert to lowercase for case-insensitive comparison
    if isinstance(key, str):
        key = key.lower() if len(key) == 1 else key
    return key in [BACK_KEY, ESC_KEY, CTRL_C_KEY, CTRL_D_KEY]

def check_or_install_fd():
    """
    Check for fd/fdfind, prompt user to install if missing, and handle persistent opt-out.
    Returns the path to fd/fdfind if available, else None.
    """
    fd_path = shutil.which("fd") or shutil.which("fdfind")
    if fd_path:
        return fd_path

    # Check persistent settings
    settings = path_utils.read_settings()
    if settings.get("try_install_fd") is False:
        return None

    # Prompt user
    print(
        f"{Fore.YELLOW}The 'fd' (or 'fdfind') command-line tool is not installed. "
        "It can greatly speed up file searches in this application.{Style.RESET_ALL}"
    )
    answer = questionary.select(
        "Would you like to attempt to install 'fd' now?",
        choices=[
            "Yes, install it for me",
            "No, use slower search this time",
            "No, and don't ask again",
        ],
        default="Yes, install it for me",
    ).ask()

    if answer == "Yes, install it for me":
        os_name = platform.system()
        install_cmd = None
        if os_name == "Darwin":
            install_cmd = ["brew", "install", "fd"]
        elif os_name == "Linux":
            # Try apt (Debian/Ubuntu), fallback to yum/dnf for RHEL/Fedora
            if shutil.which("apt"):
                install_cmd = ["sudo", "apt", "update", "&&", "sudo", "apt", "install", "-y", "fd-find"]
            elif shutil.which("dnf"):
                install_cmd = ["sudo", "dnf", "install", "-y", "fd-find"]
            elif shutil.which("yum"):
                install_cmd = ["sudo", "yum", "install", "-y", "fd-find"]
        elif os_name == "Windows":
            install_cmd = ["choco", "install", "fd", "-y"]

        if install_cmd:
            print(f"{Fore.BLUE}Attempting to install fd: {' '.join(install_cmd)}{Style.RESET_ALL}")
            try:
                # If using apt, need to run two commands (update, then install)
                if os_name == "Linux" and shutil.which("apt"):
                    subprocess.run(["sudo", "apt", "update"], check=True)
                    subprocess.run(["sudo", "apt", "install", "-y", "fd-find"], check=True)
                else:
                    subprocess.run(install_cmd, check=True)
            except Exception as e:
                print(f"{Fore.RED}Installation failed: {e}{Style.RESET_ALL}")
                print("You may need to install fd manually.")
                return None

            # Check again
            fd_path = shutil.which("fd") or shutil.which("fdfind")
            if fd_path:
                print(f"{Fore.GREEN}fd installed successfully!{Style.RESET_ALL}")
                settings["try_install_fd"] = True
                path_utils.write_settings(settings)
                return fd_path
            else:
                print(f"{Fore.RED}fd installation did not succeed. Please install it manually if you want faster file search.{Style.RESET_ALL}")
                return None
        else:
            print(f"{Fore.RED}Automatic installation is not supported on your OS. Please install 'fd' manually.{Style.RESET_ALL}")
            return None

    elif answer == "No, and don't ask again":
        settings["try_install_fd"] = False
        path_utils.write_settings(settings)
        return None
    else:
        # Just use slower search this time
        return None

# --- END FD/FDFIND LOGIC ---

class Node:
    """
    Represents a node in the data flow graph.

    Attributes:
    name (str): The name of the node.
    node_type (str): The type of the node (e.g., 'table', 'view').
    enabled (bool): Indicates if the node is enabled for focus.
    """

    def __init__(self, node_type, name, enabled=False):
        self.name = name
        self.node_type = node_type
        self.enabled = enabled


def clear_screen():
    """
    Clears the terminal screen.
    """
    os.system("cls" if os.name == "nt" else "clear")


def is_sql_file(file_path: str) -> bool:
    """
    Check if file has a SQL-related extension

    Args:
        file_path (str): Path to the file to check

    Returns:
        bool: True if file has a SQL extension
    """
    return any(str(file_path).lower().endswith(ext) for ext in SQL_EXTENSIONS)


def normalize_file_path(raw_path: str) -> str:
    """
    Normalize a file path for cross-platform compatibility.

    Handles paths from drag-and-drop operations on different platforms.

    Args:
        raw_path (str): Raw file path string

    Returns:
        str: Normalized file path
    """
    # Strip quotes that might be added by drag-and-drop
    path = raw_path.strip().strip("'\"")

    # Convert potential URI format (common in drag-and-drop on some platforms)
    if path.startswith(("file://", "file:///", "file:")):
        # Remove the file:// or file:/// prefix
        path = re.sub(r"^file:/{2,3}", "", path)

        # On Windows, file:///C:/path becomes C:/path
        # On Unix-like systems, file:///path becomes /path

        # Handle URL encoding (%20 for spaces, etc.)
        import urllib.parse

        path = urllib.parse.unquote(path)

    # Convert to proper path object and resolve to absolute path
    path_obj = Path(path)
    try:
        return str(path_obj.resolve())
    except (OSError, RuntimeError):
        # If resolution fails, return the original
        return path


def normalize_path_for_platform(path_str: str) -> str:
    """
    Ensures a path is properly formatted for the current platform.

    Args:
        path_str (str): Path string that might need normalization

    Returns:
        str: Platform-appropriate path string
    """
    # First normalize using our standard function
    norm_path = normalize_file_path(path_str)

    # Handle Windows-specific path normalization
    if os.name == "nt":
        # Convert forward slashes to backslashes for Windows
        norm_path = norm_path.replace(r"/", "\\")

        # Handle escaped spaces in Windows paths
        norm_path = norm_path.replace(r"\ ", " ")
    else:
        # For Unix-like systems, ensure proper escaping if needed
        if (
            " " in norm_path
            and not norm_path.startswith('"')
            and not norm_path.startswith("'")
        ):
            norm_path = f'"{norm_path}"'

    return norm_path


def handle_file_drop(allow_back: bool = True) -> Optional[str]:
    """
    Handle file drag and drop in terminal in an OS-agnostic way.
    Supports file paths dragged into the terminal on Windows, macOS, and Linux.

    Returns:
        Optional[str]: Path to dropped file or None if cancelled
    """
    print(f"\n{Back.BLUE}{Fore.WHITE} Drop your SQL file here {Style.RESET_ALL}")
    print(f"(or type 'cancel' {BACK_TOOLTIP})")

    try:
        raw_input = input().strip()

        # Check for cancellation
        if raw_input.lower() == "cancel" or raw_input.lower() == BACK_KEY:
            return None

        # First normalize using platform-specific logic
        # Normalize the file path for cross-platform compatibility
        file_path = normalize_path_for_platform(raw_input)

    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return None

    if not os.path.isfile(file_path):
        print(f"{Fore.RED}Error: Not a valid file path: {file_path}{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return None

    if not is_sql_file(file_path):
        proceed = questionary.confirm(
            f"File {os.path.basename(file_path)} doesn't have a SQL extension. Continue anyway?",
            default=False,
        ).ask()

        # Handle None as back navigation
        if proceed is None:
            return None
        if not proceed:
            return None

    return file_path


def validate_sql_content(file_path: str) -> bool:
    """
    Validate if file contains SQL-like content

    Args:
        file_path (str): Path to the file to validate

    Returns:
        bool: True if file appears to contain SQL content
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read(1000)  # Read first 1000 chars for quick check
            # Look for common SQL keywords
            sql_patterns = [
                r"\b(CREATE|SELECT|FROM|JOIN|VIEW|TABLE)\b",
                r"\b(INSERT|UPDATE|DELETE|DROP|ALTER)\b",
            ]
            return any(re.search(pattern, content, re.I) for pattern in sql_patterns)
    except Exception:
        return False




def collect_sql_files(search_dirs: Optional[List[Path]] = None) -> List[str]:
    """
    Collect all SQL files recursively from specified base directories.

    If no directories are provided, defaults to CWD, User Downloads,
    User Documents, and the standard data directory.

    Uses the 'fd' command if available for fast file search, otherwise falls back to pure Python.

    Args:
        search_dirs (Optional[List[Path]]): List of base directories to search.

    Returns:
        List[str]: Sorted list of absolute paths to unique SQL files found.
    """
    if search_dirs is None:
        search_dirs = [
            Path.cwd(),
            Path.home() / "Downloads",
            Path.home() / "Documents",
            path_utils.DATA_FLOW_BASE_DIR,  # Add standard data dir
        ]

    found_files: Set[Path] = set()
    fd_path = shutil.which("fd") or shutil.which("fdfind")
    extensions = [ext.lstrip(".") for ext in SQL_EXTENSIONS]

    if fd_path:
        # Use fd for each search dir, collecting results
        for base_dir in search_dirs:
            if not base_dir.is_dir():
                continue
            try:
                # Build fd command: fd --type f --no-ignore --extension sql --extension vql ... .
                cmd = [fd_path, "--type", "f", "--no-ignore"]
                for ext in extensions:
                    cmd += ["--extension", ext]
                cmd.append(".")
                result = subprocess.run(
                    cmd,
                    cwd=str(base_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    check=False,
                )
                for line in result.stdout.splitlines():
                    try:
                        full_path = Path(base_dir, line).resolve()
                        found_files.add(full_path)
                    except Exception:
                        continue
            except Exception as e:
                print(
                    f"{Fore.YELLOW}Warning: Could not search {base_dir} with fd: {e}{Style.RESET_ALL}"
                )
    else:
        # Fallback to pure Python
        for base_dir in search_dirs:
            if not base_dir.is_dir():
                continue  # Skip if dir doesn't exist
            try:
                for root, dirs, files in os.walk(base_dir, topdown=True, onerror=lambda e: print(
                    f"{Fore.YELLOW}Warning: Could not access {getattr(e, 'filename', base_dir)}: {getattr(e, 'strerror', e)}{Style.RESET_ALL}"
                )):
                    for file in files:
                        if file.lower().endswith(tuple(SQL_EXTENSIONS)):
                            try:
                                full_path = Path(os.path.join(root, file)).resolve()
                                found_files.add(full_path)
                            except Exception:
                                continue
            except Exception as e:
                print(
                    f"{Fore.YELLOW}Warning: Could not search {base_dir}: {e}{Style.RESET_ALL}"
                )

    return sorted([str(f) for f in found_files])


def add_back_to_choices(choices: List[str]) -> List[str]:
    """Add back option to choices list

    Args:
        choices (List[str]): Original choices

    Returns:
        List[str]: Choices with back option added
    """
    return choices + ["← Go back"]


def safe_input(prompt: str) -> Optional[str]:
    """Safe input wrapper that handles keyboard interrupts"""
    try:
        return input(prompt)
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return None


def select_metadata(allow_back: bool = False) -> Optional[str]:
    """
    Allows the user to select a metadata file using various methods.

    Returns:
        Optional[str]: The selected file path or None if selection was cancelled
    """
    base_choices = [
        "Browse SQL Files in Current Directory",
        "Browse Files in Standard Locations",  # Add this option
        "Drop/Paste File Path",
        "Search in directory",
        "Specify file path",
    ]
    choices = add_back_to_choices(base_choices) if allow_back else base_choices

    choice = questionary.select(
        f"How would you like to select a SQL file? {BACK_TOOLTIP if allow_back else ''}",
        choices=choices,
        mouse_support=True,
        use_shortcuts=True,
    ).ask()

    # Handle None as back navigation or explicit back choice
    if choice is None or choice == "← Go back":
        return None

    if not choice:
        return None

    if choice == "Drop/Paste File Path":
        return handle_file_drop(allow_back=allow_back)

    elif choice == "Browse SQL Files in Current Directory":
        # Browse only in current directory
        files = run_with_loading(collect_sql_files, [Path.cwd()])

        # Handle no files found in CWD
        if not files:
            proceed = questionary.confirm(
                "No SQL files found in current directory. Would you like to search in standard locations?",
                default=True,
            ).ask()

            # Handle back navigation
            if proceed is None:
                return None

            # Search in standard locations if requested
            if proceed:
                print(f"\n{Fore.BLUE}Searching for SQL files in standard locations...{Style.RESET_ALL}")
                return select_metadata(allow_back=True)
            else:
                # User doesn't want to search elsewhere
                return None

        file_choices = files + ["← Browse in more locations"]
        file_choice = questionary.select(
            "Select a file from current directory:", choices=file_choices
        ).ask()

        # Handle selection
        if file_choice is None:
            return None
        elif file_choice == "← Browse in more locations":
            # Fall through to broader search
            return select_metadata(allow_back=True)
        else:
            file_path = file_choice

    elif choice == "Browse Files in Standard Locations":
        # Use expanded search with standard locations
        files = run_with_loading(collect_sql_files)
        if not files:
            print(
                f"{Fore.YELLOW}No SQL files found in standard locations.{Style.RESET_ALL}"
            )
            return None

        file_path = questionary.select(
            "Select a file from standard locations:", choices=files
        ).ask()

    elif choice == "Specify file path":
        file_path = questionary.path(
            "Enter the absolute path to your file:",  # Clarify prompt
        ).ask()

    else:  # Search in directory
        files = run_with_loading(collect_sql_files)  # Use all standard locations
        if not files:
            print(
                f"{Fore.YELLOW}No SQL files found in default search locations.{Style.RESET_ALL}"
            )
            return None
        file_path = questionary.autocomplete("Search for file:", choices=files).ask()

    # Handle None (back navigation)
    if file_path is None:
        return None

    # Convert to absolute path if needed
    try:
        path_obj = Path(file_path)
        if not path_obj.is_absolute():
            file_path = str(path_obj.resolve())
    except (OSError, RuntimeError) as e:
        print(f"{Fore.RED}Error normalizing path: {e}{Style.RESET_ALL}")

    # Check if the file exists
    if file_path and not os.path.exists(file_path):
        # Special case for Windows - try alternate slashes
        if os.name == "nt" and "/" in file_path:
            alt_path = file_path.replace("/", "\\")
            if os.path.exists(alt_path):
                file_path = alt_path

    # Validate file exists and appears to be SQL
    # Only validate content if it's not a recognized SQL file
    if not is_sql_file(file_path) and not validate_sql_content(file_path):
        proceed = questionary.confirm(
            "This file doesn't appear to contain SQL content. Continue anyway?",
            default=False,
        ).ask()
        if not proceed:
            return select_metadata(allow_back=allow_back)  # Recursively try again

    # Final check after all processing
    if not os.path.exists(file_path):
        if isinstance(file_path, str):
            file_path = str(os.path.abspath(file_path))
    if isinstance(file_path, str):
        return str(os.path.abspath(file_path))
    else:
        raise ValueError(
            "Invalid Processing of pathlike str object in function dataflow.select_metadata."
        )


def toggle_nodes(node_types: Dict[str, Dict[str, str]]) -> List[str]:
    """
    Allows the user to toggle nodes on and off.

    Parameters:
    node_types (Dict[str, str]): A dictionary with node types.

    Returns:
    List[str]: A list of enabled node names.
    """

    nodes = [
        Node(node_type=node_types[node]["type"], name=node)
        for node in sorted(node_types.keys())
    ]

    current_index = 0
    term_height = os.get_terminal_size().lines

    while True:
        clear_screen()
        print(
            f"Use arrow keys to navigate, Space to toggle, Enter to finish, 's' to search by name, 'e' to show enabled nodes {BACK_TOOLTIP}"
        )
        print("Current nodes status:")

        middle_index = (
            term_height // 2 - 2
        )  # Ensures terminal text moves when cursor in middle

        if current_index <= middle_index:
            start_index = 0
            end_index = min(len(nodes), term_height - 4)
        elif current_index >= len(nodes) - (term_height - middle_index - 4):
            start_index = max(0, len(nodes) - (term_height - 4))
            end_index = len(nodes)
        else:
            start_index = current_index - middle_index
            end_index = start_index + term_height - 4

        for i in range(start_index, end_index):
            node = nodes[i]
            status = (
                f"{Fore.GREEN}Enabled{Style.RESET_ALL}"
                if node.enabled
                else f"{Fore.RED}Disabled{Style.RESET_ALL}"
            )
            if i == current_index:
                full_info = f"{node_types[node.name]['full_name']}, {node.node_type}"
                print(f"> {full_info}: {status}")
            else:
                full_info = f"{node_types[node.name]['full_name']}, {node.node_type}"
                print(f"  {full_info}: {status}")

        key = readchar.readkey()

        if handle_back_key(key):
            return []  # Return empty list to indicate back navigation
        elif key == readchar.key.UP and current_index > 0:
            current_index -= 1
        elif key == readchar.key.DOWN and current_index < len(nodes) - 1:
            current_index += 1
        elif key == " ":
            nodes[current_index].enabled = not nodes[current_index].enabled
        elif key == readchar.key.ENTER:
            break
        elif key == "e":
            clear_screen()
            print("\nEnabled nodes:")
            enabled_nodes = [node.name for node in nodes if node.enabled]
            if enabled_nodes:
                for enabled_node in enabled_nodes:
                    print(f"{Fore.GREEN}{enabled_node}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}None{Style.RESET_ALL}")

            # Use safe_input to handle Ctrl+C
            result = safe_input("Press Enter to return or 'b' to go back...")

            # Also check if user pressed 'b' to go back completely
            if result is None or result.lower() == "b":
                return []
        elif key == "s":
            # Enter search mode
            result = search_node(nodes)
            if result is None:
                return []  # Back navigation from search - exit toggle_nodes
            clear_screen()

    return [node.name for node in nodes if node.enabled]


def search_node(nodes: List[Node]):
    """
    Allows the user to search and toggle nodes by name.

    Parameters:
    nodes (List[Node]): The list of nodes to search through.
    """
    # Instructions with back option
    instructions = (
        "Search for a node (type to search, use arrow keys to navigate, "
        f"Enter to toggle, TAB to finish search) {BACK_TOOLTIP}"
    )
    search_query = ""
    current_index = 0
    term_height = os.get_terminal_size().lines
    node_names = [node.name for node in nodes]
    max_results = min(100, term_height * 2)  # Limit fuzzy results for speed

    while True:
        clear_screen()
        print(instructions)
        print(f"Current search: {search_query}")

        matches: List[Tuple[str, float, int]] = (
            process.extract(
                search_query,
                node_names,
                limit=max_results,
            )
            if search_query
            else []
        )

        if not matches:
            print(f"{Fore.RED}No matches found.{Style.RESET_ALL}")
        else:
            middle_index = (
                term_height // 2 - 4
            )  # Ensures terminal text moves when cursor in middle

            if current_index <= middle_index:
                start_index = 0
                end_index = min(len(matches), term_height - 6)
            elif current_index >= len(matches) - (term_height - middle_index - 6):
                start_index = max(0, len(matches) - (term_height - 6))
                end_index = len(matches)
            else:
                start_index = current_index - middle_index
                end_index = start_index + term_height - 6
            for i in range(start_index, end_index):
                node_name, score, _index = matches[i]
                node = next(node for node in nodes if node.name == node_name)
                status = (
                    f"{Fore.GREEN}Enabled{Style.RESET_ALL}"
                    if node.enabled
                    else f"{Fore.RED}Disabled{Style.RESET_ALL}"
                )

                if i == current_index:
                    print(f"> {node_name} (Score: {score:.2f}): {status}")
                else:
                    print(f"  {node_name} (Score: {score:.2f}): {status}")

        key = readchar.readkey()

        print(key)
        if handle_back_key(key):
            return None  # Return None to indicate back navigation
        elif key == readchar.key.TAB:
            print("TAB pressed. Exiting loop.")
            break
        if key == readchar.key.UP and current_index > 0:
            current_index -= 1
        elif key == readchar.key.DOWN and matches and current_index < len(matches) - 1:
            current_index += 1
        elif key == readchar.key.ENTER and matches:
            selected_node = next(
                node for node in nodes if node.name == matches[current_index][0]
            )
            selected_node.enabled = not selected_node.enabled
        elif key == readchar.key.BACKSPACE:
            search_query = search_query[:-1]
            current_index = 0
        elif len(key) == 1 and key.isprintable():
            search_query += key
            current_index = 0


def get_user_choice(
    prompt: str, options: List[str], default: int = 0, allow_back: bool = True
) -> Optional[int]:
    """
    Prompts the user to select an option using questionary.

    Parameters:
    prompt (str): The prompt message.
    options (List[str]): A list of options to choose from.
    default (int): Default option index.

    Returns:
    int: The index of the selected option.
    """
    if allow_back:
        prompt = f"{prompt} {BACK_TOOLTIP}"
        options = add_back_to_choices(options)

    answer = questionary.select(
        prompt, choices=options, default=options[default - 1] if default > 0 else None
    ).ask()

    if not answer or answer == "← Go back":
        return None

    return options.index(answer) + 1 if answer != "← Go back" else None


def select_focus_span() -> Optional[Dict[str, bool]]:
    """
    Allows the user to select focus span options for ancestors and descendants.

    Returns:
    Dict[str, bool]: A dictionary with the focus span options.
    """
    print(f"\nFocus Span Options {BACK_TOOLTIP}")

    ancestors_choice = questionary.confirm(
        "Include ancestors of focused nodes?",
        default=True,
    ).ask()

    if ancestors_choice is None:  # User pressed 'b'
        return None

    descendants_choice = questionary.confirm(
        "Include descendants of focused nodes?", default=True
    ).ask()

    if descendants_choice is None:  # User pressed 'b'
        return None

    return {"Ancestors": ancestors_choice, "Descendants": descendants_choice}


def loading_animation():
    """
    Displays a loading animation in the terminal.
    """
    animation = itertools.cycle(["|", "/", "-", "\\"])
    while not done:
        sys.stdout.write("\r" + next(animation))
        sys.stdout.flush()
        time.sleep(0.1)


def run_with_loading(func, *args, **kwargs):
    """
    Runs a function with a loading animation spinner.

    This creates a background thread that displays a spinner animation
    while the main function executes, providing visual feedback
    that the application is working.

    Parameters:
    ----------
    func : callable
        The function to run with the loading animation.
    *args: Variable length argument list to pass to the function.
    **kwargs: Arbitrary keyword arguments to pass to the function.

    Returns:
    The result of the function call.
    """
    global done
    done = False
    loading_thread = threading.Thread(target=loading_animation)
    loading_thread.daemon = True
    loading_thread.start()
    result = func(*args, **kwargs)
    done = True
    loading_thread.join()
    return result


def main():
    """
    Main function to run the Flow Diagram Creator CLI.
    """
    # Print welcome message
    clear_screen()
    print(f"{Fore.GREEN}Welcome to the Data Flow Diagram Generator{Style.RESET_ALL}")
    print("This tool helps you visualize SQL data dependencies")
    print(
        f"Press {Fore.CYAN}{BACK_KEY}{Style.RESET_ALL}, {Fore.CYAN}ESC{Style.RESET_ALL}, or {Fore.CYAN}Ctrl+C{Style.RESET_ALL} at any time to go back or exit\n"
    )
    input("Press Enter to continue...")

    while True:  # Main application loop
        clear_screen()
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # File selection loop
        metadata_file = select_metadata(allow_back=True)
        if not metadata_file:
            print("No file selected. Exiting.")
            return

        print(
            f"{Fore.BLUE}Parsing{Style.RESET_ALL} {os.path.relpath(metadata_file, script_dir)}..."
        )
        edges, node_types, database_stats = run_with_loading(parse_dump, metadata_file)

        clear_screen()
        # Database selection loop
        while database_stats:
            sorted_dbs = sorted(
                database_stats.items(), key=lambda x: x[1], reverse=True
            )
            print("\nDetected database usage frequencies:")
            for db, count in sorted_dbs:
                print(f"{db}: {count} occurrences")

            db_options = [db[0] for db in sorted_dbs]
            db_options.append("None of the above")
            db_choice = get_user_choice(
                "Select the main database:",
                [f"{db} ({count} occurrences)" for db, count in sorted_dbs]
                + ["None of the above"],
            )
            clear_screen()
            if db_choice is None:  # User pressed 'b'
                break  # Go back to file selection

            main_db = db_options[db_choice - 1]

            # Process database selection
            for node_key, node_info in node_types.items():
                db = node_info["database"]
                if node_info["type"] == "cte_view":
                    continue  # Skip CTE views
                elif db == "data_market":
                    node_info["type"] = "datamarket"
                elif (
                    db and db != "" and db != main_db and main_db != "None of the above"
                ):
                    node_info["type"] = "other"
                elif not db or db == "" or node_info["type"] == "other":
                    # Determine node type based on naming convention
                    is_view = node_key.startswith(("v_", "iv_", "rv_", "bv_", "wv_"))
                    node_info["type"] = "view" if is_view else "table"

            # Handle the case where user pressed the back key or ESC during database selection
            if db_choice is None:
                clear_screen()
                proceed = questionary.confirm(
                    "Do you want to select a different file?",
                    default=True,
                ).ask()
                if proceed:
                    break  # Go back to file selection
                else:
                    return  # Exit program
            break  # Continue to diagram selection

        if not node_types:
            clear_screen()
            print(f"{Fore.RED}Metadata has no tables or views{Style.RESET_ALL}")
            input("Press Enter to quit...")
        # Use the standard generated image directory from path_utils
        # path_utils ensures the directory exists on import
        output_folder = path_utils.GENERATED_IMAGE_DIR

        # Diagram type selection loop
        while True:
            diagram_type = get_user_choice(
                "What type of diagram would you like to create?",
                ["Complete flow diagram", "Focused flow diagram"],
                default=1,
            )

            if diagram_type is None:  # User pressed 'b'
                if database_stats:
                    break  # Go back to database selection
                else:
                    return  # Exit if no database stats

            if diagram_type == 1:
                clear_screen()
                draw_edgeless = get_user_choice(
                    "Would you like to draw the nodes that dont have any dependencies?",
                    ["Draw", "Don't draw"],
                    default=1,
                    allow_back=True,
                )

                # Add option to auto-open in browser
                auto_open = get_user_choice(
                    "Automatically open the diagram in your browser?",
                    ["Yes", "No"],
                    default=1,
                    allow_back=True,
                )

                if draw_edgeless is None:  # User pressed 'b'
                    continue  # Go back to diagram type selection

                # Both auto_open and draw_edgeless are None if user went back
                if auto_open is None:  # User pressed 'b'
                    continue  # Go back to diagram type selection

                # Convert choices to boolean values
                draw_edgeless = draw_edgeless == 1
                auto_open = auto_open == 1

                clear_screen()
                print(
                    f"{Fore.BLUE}Creating{Style.RESET_ALL} a complete flow diagram..."
                )
                run_with_loading(
                    draw_complete_data_flow,
                    edges,
                    node_types,
                    str(output_folder),  # Pass path as string
                    Path(metadata_file).stem,  # Use Pathlib for consistency
                    draw_edgeless=draw_edgeless,
                    auto_open=auto_open,  # Convert to boolean
                )
            else:
                updated_nodes = toggle_nodes(node_types)
                if not updated_nodes:  # User might have pressed 'b'
                    continue  # Go back to diagram type selection

                choices = select_focus_span()
                if choices is None:  # User pressed 'b'
                    continue  # Go back to diagram type selection

                # Add option to auto-open in browser for focused view too
                auto_open = get_user_choice(
                    "Automatically open the diagram in your browser?",
                    ["Yes", "No"],
                    default=1,
                    allow_back=True,
                )

                if auto_open is None:  # User pressed 'b'
                    continue  # Go back to diagram type selection

                clear_screen()
                print(
                    f"{Fore.BLUE}Creating{Style.RESET_ALL} a focused flow diagram with the following nodes:"
                )
                for node in updated_nodes:
                    print(f"- {node}")
                run_with_loading(
                    draw_focused_data_flow,
                    edges,
                    node_types,
                    focus_nodes=updated_nodes,
                    save_path=str(output_folder),  # Pass path as string
                    file_name=Path(metadata_file).stem,  # Use Pathlib for consistency
                    see_ancestors=choices.get("Ancestors"),
                    see_descendants=choices.get("Descendants"),
                    auto_open=auto_open,  # Convert to boolean
                )

            print(f"Flow diagram created {Fore.GREEN}successfully!{Style.RESET_ALL}")
            # Use the absolute path from path_utils
            print(
                f"The generated flow diagram can be found in the folder: {output_folder}"
            )
            print(f"Standard data directory: {path_utils.DATA_FLOW_BASE_DIR}")

            # Ask if user wants to continue or exit
            result = safe_input(
                f"Press 'c' to continue with another diagram, {BACK_TOOLTIP}, all other keys to exit..."
            )

            # Handle the response
            if result is None or result.lower() not in ["c", "continue"]:
                # Use safe_input to handle KeyboardInterrupt
                try:
                    # Ask one more time if the user wants to exit
                    exit_choice = questionary.confirm(
                        "Would you like to create another diagram?",
                        # Default to No on exit confirmation
                        default=False,
                    ).ask()

                    # If None (back navigation) or False (no), exit
                    if exit_choice is None:
                        sys.exit()  # Exit on back navigation
                    elif exit_choice:
                        # User confirmed they want another diagram
                        break  # Return to main menu
                except KeyboardInterrupt:
                    sys.exit()  # Exit on KeyboardInterrupt
                except Exception as e:
                    print(f"{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
            break  # Return to main menu


if __name__ == "__main__":
    main()
