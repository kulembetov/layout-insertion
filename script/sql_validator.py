import os
import sys
import time


class SQLValidator:
    """SQL file validator that checks for syntax issues."""

    def __init__(self, directory: str, output_file: str | None = None, verbose: bool = False):
        self.directory = directory
        self.output_file = output_file
        self.verbose = verbose

    def find_sql_files(self) -> list[str]:
        """Recursively find all SQL files in the given directory and subdirectories."""
        sql_files = []
        for root, _, files in os.walk(self.directory):
            for file in files:
                if file.endswith(".sql"):
                    sql_files.append(os.path.join(root, file))
        return sql_files

    def check_sql_file(self, file_path: str) -> dict[str, str | bool | list]:
        """Check a SQL file for trailing commas that cause syntax errors."""
        issues: dict[str, str | bool | list] = {"file_path": file_path, "has_issues": False, "issues": []}

        try:
            with open(file_path) as f:
                content = f.read()

            # Check for trailing commas line by line
            for i, line in enumerate(content.split("\n")):
                # Look for trailing comma followed by RETURNING or closing parenthesis
                if line.strip().endswith(","):
                    next_line_index = i + 1
                    if next_line_index < len(content.split("\n")):
                        next_line = content.split("\n")[next_line_index]
                        if "RETURNING" in next_line or next_line.strip().startswith(")"):
                            issues_list = issues.get("issues", [])
                            if isinstance(issues_list, list):
                                issues_list.append(
                                    {
                                        "line": i + 1,
                                        "content": line.strip(),
                                        "message": "Trailing comma at the end of a statement",
                                    }
                                )
                                issues["issues"] = issues_list

                # Check for comma at end of VALUES list before RETURNING
                if line.rstrip().endswith(",") and i + 1 < len(content.split("\n")):
                    next_line = content.split("\n")[i + 1]
                    if next_line.strip().startswith(")") and "RETURNING" in next_line:
                        issues_list = issues.get("issues", [])
                        if isinstance(issues_list, list):
                            issues_list.append(
                                {
                                    "line": i + 1,
                                    "content": line.strip(),
                                    "message": "Trailing comma at the end of VALUES list",
                                }
                            )
                            issues["issues"] = issues_list

            # Set overall issue flag
            issues["has_issues"] = bool(issues["issues"])

        except Exception as e:
            issues["has_issues"] = True
            issues["error"] = str(e)

        return issues

    def run(self):
        """Execute the validation process."""
        # Find all SQL files
        sql_files = self.find_sql_files()
        print(f"Found {len(sql_files)} SQL files to check")

        if not sql_files:
            print("No SQL files found. Exiting.")
            return

        # Check each file
        results = []
        files_with_issues = 0

        print("\nChecking SQL files...")
        for i, file_path in enumerate(sql_files):
            progress = f"[{i + 1}/{len(sql_files)}]"
            print(f"{progress} Checking {os.path.basename(file_path)}...", end="\r")

            issues = self.check_sql_file(file_path)
            results.append(issues)

            if issues["has_issues"]:
                files_with_issues += 1
                print(f"\n{progress} Issues found in {file_path}:")

                if "error" in issues:
                    print(f"  - Error processing file: {issues['error']}")

                for issue in issues["issues"]:
                    print(f"  - Line {issue['line']}: {issue['message']}")
                    if self.verbose:
                        print(f"    {issue['content']}")

        # Clear the progress line
        print(" " * 80, end="\r")

        # Summary
        if files_with_issues > 0:
            print(f"\nFound issues in {files_with_issues} out of {len(sql_files)} files")
        else:
            print(f"\nNo issues found in any of the {len(sql_files)} SQL files")

        # Write to output file if specified
        if self.output_file is not None and files_with_issues > 0:
            self._write_report(results, files_with_issues, len(sql_files))

    def _write_report(self, results: list[dict], files_with_issues: int, total_files: int):
        """Write validation results to the output file."""
        if self.output_file is None:
            return
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write("SQL Validation Results\n")
            f.write("====================\n\n")

            f.write(f"Checked {total_files} SQL files. Found issues in {files_with_issues} files.\n\n")

            for result in results:
                if result["has_issues"]:
                    f.write(f"Issues in {result['file_path']}:\n")

                    if "error" in result:
                        f.write(f"  - Error processing file: {result['error']}\n")

                    for issue in result["issues"]:
                        f.write(f"  - Line {issue['line']}: {issue['message']}\n")
                        f.write(f"    {issue['content']}\n")

                    f.write("\n")

        print(f"Results written to {self.output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sql_validator.py <directory> [output_file] [--verbose]")
        sys.exit(1)

    directory = sys.argv[1]
    output_file = None
    verbose = False

    for arg in sys.argv[2:]:
        if arg == "--verbose":
            verbose = True
        elif not output_file:
            output_file = arg

    # Start the validation
    start_time = time.time()
    validator = SQLValidator(directory, output_file, verbose)
    validator.run()
    elapsed_time = time.time() - start_time

    print(f"Validation completed in {elapsed_time:.2f} seconds")
