#!/usr/bin/env python3
"""
Python Comment Remover

This script removes comments and docstrings from Python files while preserving
the code structure and functionality.
"""

import os
import sys
import tokenize
import io
import argparse
from pathlib import Path


def is_docstring(tokens, index):
    """
    Check if a string token at the given index is likely a docstring.
    A docstring is typically the first statement in a module, class, or function.
    """
    if index == 0:
        return True
    
    # Look backwards to see if this string follows a def/class/module start
    for i in range(index - 1, -1, -1):
        token = tokens[i]
        if token.type == tokenize.NEWLINE:
            continue
        elif token.type == tokenize.INDENT:
            continue
        elif token.type == tokenize.NAME and token.string in ('def', 'class'):
            return True
        elif token.type == tokenize.OP and token.string == ':':
            continue
        else:
            break
    
    return False


def remove_comments_from_code(code_string):
    """
    Remove comments and docstrings from Python code string.
    
    Args:
        code_string (str): The Python code as a string
        
    Returns:
        str: The code with comments and docstrings removed
    """
    try:
        # Tokenize the code
        tokens = list(tokenize.generate_tokens(io.StringIO(code_string).readline))
        
        # Filter out comments and docstrings
        filtered_tokens = []
        for i, token in enumerate(tokens):
            # Skip comment tokens
            if token.type == tokenize.COMMENT:
                continue
            
            # Skip string tokens that are likely docstrings
            if (token.type == tokenize.STRING and 
                (token.string.startswith('"""') or token.string.startswith("'''")) and
                is_docstring(tokens, i)):
                continue
            
            filtered_tokens.append(token)
        
        # Reconstruct the code from filtered tokens
        return tokenize.untokenize(filtered_tokens)
    
    except tokenize.TokenError as e:
        print(f"Error tokenizing code: {e}")
        return code_string


def remove_comments_from_file(file_path, output_path=None, backup=True):
    """
    Remove comments from a Python file.
    
    Args:
        file_path (str): Path to the input Python file
        output_path (str, optional): Path for the output file. If None, overwrites the input file.
        backup (bool): Whether to create a backup of the original file
    """
    file_path = Path(file_path)
    
    # Validate input file
    if not file_path.exists():
        print(f"Error: File '{file_path}' does not exist.")
        return False
    
    if not file_path.suffix == '.py':
        print(f"Warning: '{file_path}' is not a Python file (.py)")
    
    try:
        # Read the original file
        with open(file_path, 'r', encoding='utf-8') as f:
            original_code = f.read()
        
        # Remove comments
        cleaned_code = remove_comments_from_code(original_code)
        
        # Determine output path
        if output_path is None:
            output_path = file_path
        else:
            output_path = Path(output_path)
        
        # Create backup if requested and we're overwriting the original
        if backup and output_path == file_path:
            backup_path = file_path.with_suffix('.py.bak')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_code)
            print(f"Backup created: {backup_path}")
        
        # Write the cleaned code
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_code)
        
        print(f"Comments removed from '{file_path}' -> '{output_path}'")
        return True
        
    except Exception as e:
        print(f"Error processing file '{file_path}': {e}")
        return False


def process_directory(directory_path, output_dir=None, backup=True, recursive=True):
    """
    Process all Python files in a directory.
    
    Args:
        directory_path (str): Path to the directory containing Python files
        output_dir (str, optional): Output directory. If None, files are processed in place.
        backup (bool): Whether to create backups
        recursive (bool): Whether to process subdirectories recursively
    """
    directory_path = Path(directory_path)
    
    if not directory_path.exists() or not directory_path.is_dir():
        print(f"Error: Directory '{directory_path}' does not exist.")
        return
    
    # Find all Python files
    pattern = "**/*.py" if recursive else "*.py"
    python_files = list(directory_path.glob(pattern))
    
    if not python_files:
        print(f"No Python files found in '{directory_path}'")
        return
    
    print(f"Found {len(python_files)} Python files to process...")
    
    success_count = 0
    for file_path in python_files:
        output_path = None
        if output_dir:
            # Maintain directory structure in output
            relative_path = file_path.relative_to(directory_path)
            output_path = Path(output_dir) / relative_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if remove_comments_from_file(file_path, output_path, backup):
            success_count += 1
    
    print(f"\nProcessed {success_count}/{len(python_files)} files successfully.")


def main():
    parser = argparse.ArgumentParser(
        description="Remove comments and docstrings from Python files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python comment_remover.py file.py                    # Remove comments from file.py (creates backup)
  python comment_remover.py file.py -o cleaned.py     # Save cleaned version as cleaned.py
  python comment_remover.py src/ -r                   # Process all .py files in src/ recursively
  python comment_remover.py src/ -o output/ -r        # Process src/ and save to output/ directory
        """
    )
    
    parser.add_argument('path', help='Python file or directory to process')
    parser.add_argument('-o', '--output', help='Output file or directory')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='Process directories recursively')
    parser.add_argument('--no-backup', action='store_true',
                        help='Do not create backup files')
    
    args = parser.parse_args()
    
    path = Path(args.path)
    
    if path.is_file():
        # Process single file
        remove_comments_from_file(args.path, args.output, not args.no_backup)
    elif path.is_dir():
        # Process directory
        process_directory(args.path, args.output, not args.no_backup, args.recursive)
    else:
        print(f"Error: '{args.path}' is not a valid file or directory.")
        sys.exit(1)


if __name__ == "__main__":
    main()