import os
import re
import readchar
import questionary
from colorama import init, Fore, Style, Back
from src.generate_data_flow import (
    draw_focused_data_flow,
    draw_complete_data_flow,
    parse_vql,
)
import glob
import itertools
import threading
import sys
import time
from rapidfuzz import process
from typing import List, Dict, Optional

# Constants
SQL_EXTENSIONS = [
    '.sql',     # Standard SQL files
    '.vql',     # Denodo VQL files
    '.ddl',     # Data Definition Language
    '.dml',     # Data Manipulation Language
    '.hql',     # Hive Query Language
    '.pls',     # PL/SQL files
    '.plsql',   # PL/SQL files
    '.proc',    # Stored Procedures
    '.psql',    # PostgreSQL files
    '.tsql',    # T-SQL files
    '.view'     # View definitions
]

# Initialize colorama and constants
init()

# Key bindings
BACK_KEY = 'b'
BACK_TOOLTIP = f"(press '{BACK_KEY}' to go back)"

def handle_back_key(key: str) -> bool:
    """Check if back navigation is requested

    Args:
        key (str): Key pressed by user

    Returns:
        bool: True if back navigation requested
    """

    return key.lower() == BACK_KEY

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
    return any(file_path.lower().endswith(ext) for ext in SQL_EXTENSIONS)

def handle_file_drop() -> Optional[str]:
    """
    Handle file drag and drop in terminal

    Returns:
        Optional[str]: Path to dropped file or None if cancelled
    """
    print(f"\n{Back.BLUE}{Fore.WHITE} Drop your SQL file here {Style.RESET_ALL}")
    print("(or type 'cancel' to exit)")
    
    file_path = input().strip().strip("'\"")  # Remove quotes that might be added by drag-and-drop
    
    if file_path.lower() == 'cancel':
        return None
        
    if not os.path.isfile(file_path):
        print(f"{Fore.RED}Error: Not a valid file path{Style.RESET_ALL}")
        return None
        
    if not is_sql_file(file_path):
        proceed = questionary.confirm(
            f"File {os.path.basename(file_path)} doesn't have a SQL extension. Continue anyway?",
            default=False
        ).ask()
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
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(1000)  # Read first 1000 chars for quick check
            # Look for common SQL keywords
            sql_patterns = [
                r'\b(CREATE|SELECT|FROM|JOIN|VIEW|TABLE)\b',
                r'\b(INSERT|UPDATE|DELETE|DROP|ALTER)\b'
            ]
            return any(re.search(pattern, content, re.I) for pattern in sql_patterns)
    except Exception:
        return False

def collect_sql_files() -> List[str]:
    """
    Collect all SQL files in current directory and subdirectories

    Returns:
        List[str]: List of paths to SQL files
    """
    files = []
    for ext in SQL_EXTENSIONS:
        files.extend(glob.glob(f"**/*{ext}", recursive=True))
    return sorted(list(set(files)))  # Remove duplicates and sort

def add_back_to_choices(choices: List[str]) -> List[str]:
    """Add back option to choices list

    Args:
        choices (List[str]): Original choices

    Returns:
        List[str]: Choices with back option added
    """
    return choices + ["← Go back"]

def select_metadata(allow_back: bool = False) -> Optional[str]:
    """
    Allows the user to select a metadata file using various methods.

    Returns:
        Optional[str]: The selected file path or None if selection was cancelled
    """
    base_choices = [
        "Browse SQL Files",
        "Drop/Upload File",    
        "Search in directory",
        "Specify file path",
    ]
    choices = add_back_to_choices(base_choices) if allow_back else base_choices
    
    choice = questionary.select(
        f"How would you like to select your file? {BACK_TOOLTIP if allow_back else ''}",
        choices=choices
    ).ask()

    if not choice or choice == "← Go back":
        return None
    
    if not choice:
        return None

    if choice == "Drop/Upload File":
        return handle_file_drop()
        
    elif choice == "Browse SQL Files":
        files = collect_sql_files()
        if not files:
            print(f"{Fore.YELLOW}No SQL files found in current directory{Style.RESET_ALL}")
            return None
        file_path = questionary.select(
            "Select a file:",
            choices=files
        ).ask()
    
    elif choice == "Specify file path":
        file_path = questionary.path(
            "Enter the path to your file:",
            validate=lambda path: os.path.exists(path) and os.path.isfile(path)
        ).ask()
    
    else:  # Search in directory
        files = collect_sql_files()
        if not files:
            print(f"{Fore.YELLOW}No SQL files found in current directory{Style.RESET_ALL}")
            return None
        file_path = questionary.autocomplete(
            "Search for file:",
            choices=files
        ).ask()

    if not file_path:
        return None

    # Validate selected file
    # Only validate content if it's not a recognized SQL file
    if not is_sql_file(file_path) and not validate_sql_content(file_path):
        proceed = questionary.confirm(
            "This file doesn't appear to contain SQL content. Continue anyway?",
            default=False
        ).ask()
        if not proceed:
            return select_metadata()  # Recursively try again
    if isinstance(file_path, str):
        return str(os.path.abspath(file_path))
    else:
        raise ValueError("Invalid Processing of pathlike str object in function dataflow.select_metadata.")

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
            input("Press Enter to return...")  # Pause to show the message
        elif key == "s":
            clear_screen()
            search_node(nodes)

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

    while True:
        clear_screen()
        print(
            instructions
        )
        print(f"Current search: {search_query}")

        matches = (
            process.extract(
                search_query,
                [node.name for node in nodes],
                limit=len(nodes),
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

def get_user_choice(prompt: str, options: List[str], default: int = 0, allow_back: bool = True) -> Optional[int]:
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
        prompt,
        choices=options,
        default=options[default-1] if default > 0 else None
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
        default=True
    ).ask()
    
    if ancestors_choice is None:  # User pressed 'b'
        return None

    descendants_choice = questionary.confirm(
        "Include descendants of focused nodes?",
        default=True
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
    Runs a function with a loading animation.

    Parameters:
    func (callable): The function to run.
    *args: Positional arguments for the function.
    **kwargs: Keyword arguments for the function.

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
    while True:  # Main application loop
        clear_screen()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # File selection loop
        metadata_file = select_metadata(allow_back=True)
        if not metadata_file:
            print("No file selected. Exiting.")
            return

        print(f"{Fore.BLUE}Parsing{Style.RESET_ALL} {os.path.relpath(metadata_file, script_dir)}...")
        edges, node_types, database_stats = run_with_loading(parse_vql, metadata_file)

        clear_screen()
        # Database selection loop
        while database_stats:
            sorted_dbs = sorted(database_stats.items(), key=lambda x: x[1], reverse=True)
            print("\nDetected database usage frequencies:")
            for db, count in sorted_dbs:
                print(f"{db}: {count} occurrences")

            db_options = [db[0] for db in sorted_dbs]
            db_options.append("None of the above")
            db_choice = get_user_choice(
                "Select the main database:",
                [f"{db} ({count} occurrences)" for db, count in sorted_dbs] + ["None of the above"]
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
                elif db and db != "" and db != main_db and main_db != "None of the above":
                    node_info["type"] = "other"
                elif not db or db == "" or node_info["type"] == "other":
                    node_info["type"] = "view" if node_key.startswith(("v_", "iv_", "rv_", "bv_", "wv_")) else "table"
            break  # Continue to diagram selection

        if not node_types:
            clear_screen()
            print(f"{Fore.RED}Metadata has no tables or views{Style.RESET_ALL}")
            input("Press Enter to quit...")
            return

        # Ensure output directory exists
        output_folder = os.path.join(os.getcwd(), "generated-image")
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Diagram type selection loop
        while True:
            diagram_type = get_user_choice(
                "What type of diagram would you like to create?",
                ["Complete flow diagram", "Focused flow diagram"],
                default=1
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
                    allow_back=True
                )
                
                if draw_edgeless is None:  # User pressed 'b'
                    continue  # Go back to diagram type selection

                clear_screen()
                print(f"{Fore.BLUE}Creating{Style.RESET_ALL} a complete flow diagram...")
                run_with_loading(
                    draw_complete_data_flow,
                    edges,
                    node_types,
                    output_folder,
                    os.path.basename(metadata_file).split(".")[0],
                    draw_edgeless=(True if draw_edgeless == 1 else False),
                )
            else:
                updated_nodes = toggle_nodes(node_types)
                if not updated_nodes:  # User might have pressed 'b'
                    continue  # Go back to diagram type selection
                    
                choices = select_focus_span()
                if choices is None:  # User pressed 'b'
                    continue  # Go back to diagram type selection

                clear_screen()
                print(f"{Fore.BLUE}Creating{Style.RESET_ALL} a focused flow diagram with the following nodes:")
                for node in updated_nodes:
                    print(f"- {node}")
                run_with_loading(
                    draw_focused_data_flow,
                    edges,
                    node_types,
                    focus_nodes=updated_nodes,
                    save_path=output_folder,
                    file_name=os.path.basename(metadata_file).split(".")[0],
                    see_ancestors=choices.get("Ancestors"),
                    see_descendants=choices.get("Descendants"),
                )

            print(f"Flow diagram created {Fore.GREEN}successfully!{Style.RESET_ALL}")
            print(f"The generated flow diagram can be found in the folder: {os.path.relpath(output_folder, os.getcwd())}")
            if input("Press 'c' to continue with other, all other presses exits program...") != "c":
                # Exit program
                sys.exit()
            break  # Return to main menu
        

if __name__ == "__main__":
    main()
