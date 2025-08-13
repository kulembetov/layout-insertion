"""
Script to remove single-line comments from figma.py while preserving docstrings.
"""

import re
import sys


def remove_single_line_comments(content):
    """
    Remove single-line comments while preserving docstrings and functionality.

    - Removes lines that are purely comments (starting with # after whitespace)
    - Removes inline comments (# and everything after on lines with code)
    - Preserves triple-quoted docstrings
    - Preserves string literals that contain #
    """
    lines = content.splitlines()
    result_lines = []
    in_triple_quote = False
    triple_quote_char = None

    for line in lines:
        original_line = line
        stripped = line.strip()

        quote_matches = re.finditer(r'("""|\'\'\')|(#)', line)
        quotes_positions = []
        hash_positions = []

        for match in quote_matches:
            if match.group(1):
                quotes_positions.append((match.start(1), match.group(1)))
            elif match.group(2):
                hash_positions.append(match.start(2))

        for pos, quote_type in quotes_positions:
            if not in_triple_quote:
                in_triple_quote = True
                triple_quote_char = quote_type
            elif quote_type == triple_quote_char:
                in_triple_quote = False
                triple_quote_char = None

        if in_triple_quote:
            result_lines.append(original_line)
            continue

        if stripped.startswith("#"):
            continue

        processed_line = line

        in_string = False
        string_char = None
        escaped = False
        i = 0

        while i < len(processed_line):
            char = processed_line[i]

            if escaped:
                escaped = False
                i += 1
                continue

            if char == "\\":
                escaped = True
                i += 1
                continue

            if not in_string and char in ['"', "'"]:
                in_string = True
                string_char = char
            elif in_string and char == string_char:
                in_string = False
                string_char = None
            elif not in_string and char == "#":
                processed_line = processed_line[:i].rstrip()
                break

            i += 1

        if processed_line.strip() or not original_line.strip():
            result_lines.append(processed_line)

    return "\n".join(result_lines)


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "figma.py"

    try:
        with open(input_file, encoding="utf-8") as f:
            content = f.read()

        cleaned_content = remove_single_line_comments(content)

        with open(input_file, "w", encoding="utf-8") as f:
            f.write(cleaned_content)

        print(f"Successfully removed comments from {input_file}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
