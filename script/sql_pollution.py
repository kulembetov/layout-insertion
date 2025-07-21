import os
import sys
import glob
import psycopg2
import argparse
from configparser import ConfigParser


class ConfigManager:
    """Manages database configuration loading and creation."""

    def __init__(self, filename='database.ini', section='postgresql'):
        self.filename = filename if os.path.isabs(filename) else os.path.abspath(filename)
        self.section = section
        print(f"Looking for config file at: {self.filename}")

    def load_config(self):
        """Load database connection parameters from config file."""
        parser = ConfigParser()

        if not os.path.isfile(self.filename):
            print(f"Error: Config file '{self.filename}' not found.")
            self.create_sample_config()
            sys.exit(1)

        parser.read(self.filename)

        if parser.has_section(self.section):
            return {param[0]: param[1] for param in parser.items(self.section)}
        else:
            raise Exception(f"Section {self.section} not found in the {self.filename} file.")

    def create_sample_config(self):
        """Create a sample config file for the user."""
        with open(self.filename, 'w') as f:
            f.write("""[postgresql]
host=localhost
database=your_database
user=your_username
password=your_password
port=5432
""")
        print(f"A sample configuration file '{self.filename}' has been created.")
        print("Please update it with your database connection details and run the script again.")


class DatabaseManager:
    """Manages database connections and SQL execution."""

    def __init__(self, config_params):
        self.params = config_params
        self.conn = None

    def connect(self):
        """Connect to the PostgreSQL database."""
        try:
            print("Connecting to the PostgreSQL database...")
            self.conn = psycopg2.connect(**self.params)
            return self.conn
        except (Exception, psycopg2.DatabaseError) as error:
            print(f"Error: {error}")
            sys.exit(1)

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            print("\nDatabase connection closed.")

    def extract_sql_statements(self, sql_content):
        """
        Parse SQL content and extract actual SQL statements,
        ignoring comments.
        """
        # Remove SQL comments
        lines = []
        for line in sql_content.split('\n'):
            # Remove inline comments
            if '--' in line:
                line = line[:line.find('--')]
            # Add non-empty lines
            if line.strip():
                lines.append(line)

        # Join lines and split by semicolon
        clean_sql = '\n'.join(lines)
        statements = [stmt.strip() for stmt in clean_sql.split(';') if stmt.strip()]
        return statements


class SQLExecutor:
    """Executes SQL files from a directory."""

    def __init__(self, db_manager, sql_dir="./sql"):
        self.db_manager = db_manager
        self.sql_dir = sql_dir if os.path.isabs(sql_dir) else os.path.abspath(sql_dir)
        print(f"Looking for SQL files in: {self.sql_dir}")

    def find_sql_files(self):
        """Find all SQL files in the directory and subdirectories (recursively), with logging."""
        # Check if SQL directory exists
        if not os.path.isdir(self.sql_dir):
            print(f"Error: Directory '{self.sql_dir}' not found.")
            os.makedirs(self.sql_dir)
            print(f"Created empty directory '{self.sql_dir}'. Please add SQL files and run again.")
            return []

        # List all files in the directory for debugging
        print("All files in directory:")
        try:
            dir_contents = os.listdir(self.sql_dir)
            if not dir_contents:
                print("  [Directory is empty]")
            for item in dir_contents:
                item_path = os.path.join(self.sql_dir, item)
                if os.path.isfile(item_path):
                    print(f"  - {item} (file)")
                else:
                    print(f"  - {item} (directory)")
        except Exception as e:
            print(f"  [Error listing directory contents: {e}]")

        # Recursively find all .sql files (case-insensitive), with per-directory logging
        sql_files = []
        for root, dirs, files in os.walk(self.sql_dir):
            found_in_dir = [file for file in files if file.lower().endswith('.sql')]
            if found_in_dir:
                rel_root = os.path.relpath(root, self.sql_dir)
                dir_label = '.' if rel_root == '.' else rel_root
                print(f"Found {len(found_in_dir)} .sql files in {dir_label}")
                for file in found_in_dir:
                    sql_files.append(os.path.join(root, file))

        # Remove duplicates and sort
        sql_files = sorted(list(set(sql_files)))
        print(f"Found SQL files: {len(sql_files)}")

        return sql_files

    def confirm_execution(self, sql_files):
        """Ask user for confirmation before executing SQL files."""
        if not sql_files:
            return False

        print("\n" + "=" * 60)
        print("CONFIRMATION REQUIRED")
        print("=" * 60)
        print(f"Database: {self.db_manager.params.get('database', 'Unknown')}")
        print(f"Host: {self.db_manager.params.get('host', 'Unknown')}")
        print(f"User: {self.db_manager.params.get('user', 'Unknown')}")
        print(f"SQL Directory: {self.sql_dir}")
        print(f"Files to execute ({len(sql_files)}):")

        for i, file_path in enumerate(sql_files, 1):
            filename = os.path.basename(file_path)
            print(f"  {i:2}. {filename}")

        print("\nWARNING: This will execute SQL commands against your database!")
        print("   Make sure you have backups and understand what these scripts do.")
        print("=" * 60)

        while True:
            try:
                response = input("\nDo you want to proceed? (yes/no): ").strip().lower()
                if response in ['yes', 'y']:
                    return True
                elif response in ['no', 'n']:
                    print("Execution cancelled by user.")
                    return False
                else:
                    print("Please enter 'yes' or 'no'.")
            except KeyboardInterrupt:
                print("\n\nExecution cancelled by user.")
                return False

    def execute_files(self):
        """Execute all SQL files found in the directory."""
        conn = self.db_manager.conn
        cursor = conn.cursor()

        sql_files = self.find_sql_files()

        if not sql_files:
            print(f"No SQL files found in '{self.sql_dir}' directory.")
            cursor.close()
            return

        # Ask for confirmation before proceeding
        if not self.confirm_execution(sql_files):
            cursor.close()
            return

        total_files = len(sql_files)
        successful_files = 0

        print(f"\nStarting execution of {total_files} SQL files...")
        print("=" * 50)

        for file_path in sql_files:
            print(f"\nExecuting {os.path.basename(file_path)}:")
            try:
                with open(file_path, "r", encoding='utf-8') as file:
                    sql_content = file.read()
                    commands = self.db_manager.extract_sql_statements(sql_content)

                    file_success = True
                    for i, command in enumerate(commands, 1):
                        try:
                            cursor.execute(command + ';')
                            conn.commit()
                            print(f"  Command {i}: Success")
                        except psycopg2.Error as e:
                            conn.rollback()
                            print(f"  Command {i}: Failed")
                            print(f"    Error: {e}\n")
                            file_success = False

                    if file_success:
                        successful_files += 1
            except Exception as e:
                print(f"  Failed to open or process file: {e}")

        print("\n" + "=" * 50)
        print(f"Execution summary: {successful_files}/{total_files} files executed successfully.")
        print("=" * 50)

        cursor.close()


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description="Execute SQL files from a directory against a PostgreSQL database."
    )
    parser.add_argument('--input-dir', type=str, default='script/my_sql_output',
                        help='Directory containing SQL files to execute (default: script/my_sql_output)')
    parser.add_argument('--db-config', type=str, default='database.ini',
                        help='Database configuration file (default: database.ini)')
    
    args = parser.parse_args()
    
    print("SQL Files Execution Script")
    print("=" * 30)
    print(f"Current working directory: {os.getcwd()}")

    # Initialize and use the classes
    config_manager = ConfigManager(args.db_config)
    db_params = config_manager.load_config()

    db_manager = DatabaseManager(db_params)
    db_manager.connect()

    sql_executor = SQLExecutor(db_manager, args.input_dir)
    sql_executor.execute_files()

    db_manager.close()
    print("Script execution completed.")


if __name__ == "__main__":
    main()