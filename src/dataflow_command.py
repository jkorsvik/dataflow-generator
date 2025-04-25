import argparse
import sys
from pathlib import Path
from . import path_utils  # Import the new utility module
from .generate_data_flow import (
    draw_focused_data_flow,
    draw_complete_data_flow,
    parse_dump,
)


def main():
    parser = argparse.ArgumentParser(
        description="Generate data flow diagrams from metadata files."
    )
    parser.add_argument(
        "-m", "--metadata", required=True, help="Path to the metadata (SQL/VQL) file."
    )
    parser.add_argument(
        "-t",
        "--type",
        choices=["complete", "focused"],
        default="complete",
        help="Type of diagram to generate (default: complete).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(path_utils.GENERATED_IMAGE_DIR),
        help=f"Output directory for generated images (default: {path_utils.GENERATED_IMAGE_DIR}).",
    )
    parser.add_argument(
        "--draw-edgeless",
        action="store_true",
        default=True,
        help="Draw nodes without dependencies (only for complete diagrams, default: True).",
    )
    parser.add_argument(
        "--no-draw-edgeless",
        dest="draw_edgeless",
        action="store_false",
        help="Do not draw nodes without dependencies.",
    )
    parser.add_argument(
        "--main-db", default=None, help="Specify the main database (optional)."
    )
    parser.add_argument(
        "--focus-nodes",
        nargs="*",
        default=None,
        help="List of node names to focus on (only for focused diagrams).",
    )
    parser.add_argument(
        "--no-ancestors",
        dest="see_ancestors",
        action="store_false",
        default=True,
        help="Do not include ancestors in focused diagram.",
    )
    parser.add_argument(
        "--no-descendants",
        dest="see_descendants",
        action="store_false",
        default=True,
        help="Do not include descendants in focused diagram.",
    )
    parser.add_argument(
        "--auto-open",
        action="store_true",
        default=False,
        help="Automatically open the diagram in the default browser (default: False).",
    )
    parser.add_argument(
        "--no-auto-open",
        dest="auto_open",
        action="store_false",
        help="Do not automatically open the diagram in the browser.",
    )
    args = parser.parse_args()

    # Parse metadata
    edges, node_types, database_stats = parse_dump(args.metadata)

    # Optionally adjust node types based on main_db
    if args.main_db:
        for node_key, node_info in node_types.items():
            db = node_info["database"]
            if node_info["type"] == "cte_view":
                continue
            elif db == "data_market":
                node_info["type"] = "datamarket"
            elif db and db != "" and db != args.main_db:
                node_info["type"] = "other"
            elif not db or db == "" or node_info["type"] == "other":
                node_info["type"] = (
                    "view"
                    if node_key.startswith(("v_", "iv_", "rv_", "bv_", "wv_"))
                    else "table"
                )

    # Use the path provided by the user or the default from path_utils
    output_folder = Path(args.output).resolve()
    # Ensure the specific output folder exists (it might be the default or user-specified)
    # path_utils.ensure_data_dirs_exist() is called on import, but we also need to ensure
    # the potentially user-specified output folder exists.
    output_folder.mkdir(parents=True, exist_ok=True)

    file_name = Path(args.metadata).stem

    if args.type == "complete":
        draw_complete_data_flow(
            edges,
            node_types,
            str(output_folder),  # Pass path as string
            file_name,
            auto_open=args.auto_open,
            draw_edgeless=args.draw_edgeless,
        )
        print(f"Complete flow diagram created successfully! Output: {output_folder}")
        print(f"Standard data directory: {path_utils.DATA_FLOW_BASE_DIR}")
    else:
        if not args.focus_nodes:
            print("Error: --focus-nodes is required for focused diagram.")
            sys.exit(1)
        draw_focused_data_flow(
            edges,
            node_types,
            focus_nodes=args.focus_nodes,
            save_path=str(output_folder),  # Pass path as string
            file_name=file_name,
            auto_open=args.auto_open,
            see_ancestors=args.see_ancestors,
            see_descendants=args.see_descendants,
        )
        print(f"Focused flow diagram created successfully! Output: {output_folder}")
        print(f"Standard data directory: {path_utils.DATA_FLOW_BASE_DIR}")


if __name__ == "__main__":
    main()
