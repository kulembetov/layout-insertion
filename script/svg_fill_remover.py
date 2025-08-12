"""
SVG Fill Remover Script

This script scans a directory for SVG files and removes all 'fill' attributes
from SVG elements, making them inherit fill colors from CSS or parent elements.
"""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path


def remove_fill_attributes(svg_content):
    """
    Remove all fill attributes from SVG elements.

    Args:
        svg_content (str): The SVG file content as a string

    Returns:
        str: Modified SVG content with fill attributes removed
    """
    try:
        root = ET.fromstring(svg_content)

        for elem in root.iter():
            if "fill" in elem.attrib:
                del elem.attrib["fill"]

        modified_svg = ET.tostring(root, encoding="unicode", xml_declaration=False)

        modified_svg = modified_svg.replace("ns0:", "")
        modified_svg = modified_svg.replace(
            'xmlns:ns0="http://www.w3.org/2000/svg"',
            'xmlns="http://www.w3.org/2000/svg"',
        )

        if svg_content.strip().startswith("<?xml"):
            modified_svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + modified_svg

        return modified_svg

    except ET.ParseError as e:
        print(f"Error parsing SVG: {e}")
        return svg_content


def process_svg_file(file_path, backup=False):
    """
    Process a single SVG file to remove fill attributes.

    Args:
        file_path (str): Path to the SVG file
        backup (bool): Whether to create a backup of the original file
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            original_content = f.read()

        if backup:
            backup_path = file_path + ".backup"
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(original_content)
            print(f"Backup created: {backup_path}")

        modified_content = remove_fill_attributes(original_content)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(modified_content)

        print(f"Processed: {file_path}")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")


def scan_and_process_directory(directory_path, recursive=True, backup=False):
    """
    Scan directory for SVG files and process them.

    Args:
        directory_path (str): Path to the directory to scan
        recursive (bool): Whether to scan subdirectories
        backup (bool): Whether to create backups
    """
    dir_path = Path(directory_path)

    if not dir_path.exists():
        print(f"Error: Directory '{directory_path}' does not exist.")
        return

    if not dir_path.is_dir():
        print(f"Error: '{directory_path}' is not a directory.")
        return

    if recursive:
        svg_files = list(dir_path.rglob("*.svg"))
    else:
        svg_files = list(dir_path.glob("*.svg"))

    if not svg_files:
        print(f"No SVG files found in '{directory_path}'")
        return

    print(f"Found {len(svg_files)} SVG files to process...")

    for svg_file in svg_files:
        process_svg_file(str(svg_file), backup=backup)

    print(f"\nCompleted processing {len(svg_files)} SVG files.")


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Remove fill attributes from SVG files in a directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python svg_fill_remover.py ./icons
  python svg_fill_remover.py ./assets --no-recursive
  python svg_fill_remover.py /path/to/svg/files --backup
        """,
    )

    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to scan for SVG files (default: current directory)",
    )

    parser.add_argument("--no-recursive", action="store_true", help="Do not scan subdirectories")

    parser.add_argument("--backup", action="store_true", help="Create backup files (default: no backup)")

    args = parser.parse_args()

    scan_and_process_directory(
        directory_path=args.directory,
        recursive=not args.no_recursive,
        backup=args.backup,
    )


if __name__ == "__main__":
    main()
