#!/usr/bin/env python3
"""
Script to export IssueReport table from database to Excel and append to Google Sheets.

This module provides a comprehensive issue report export system with:
- Database connectivity and data fetching
- Excel export capabilities
- Google Sheets integration with duplicate prevention
- Configurable formatting and styling
- Professional logging and error handling

Design Patterns Used:
- Strategy Pattern: Different export strategies
- Factory Pattern: Creating export components
- Builder Pattern: Building complex spreadsheet configurations
- Dependency Injection: Configurable services
"""

import configparser
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

# Google API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from psycopg2.extras import RealDictCursor

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================


class ExportConfig:
    """Configuration class for export settings."""

    # Directory settings
    OUTPUT_DIR = Path("issue_reports")
    LOG_FILE = OUTPUT_DIR / "issue_reports.log"

    # Google Sheets settings
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    CREDENTIALS_FILE = Path("../credentials.json")
    TOKEN_FILE = Path("../token.json")
    SPREADSHEET_ID = "1GGUznHFHmsjfH2bqCvEsbBm8rQWalcRa8dD7EQwq-KI"
    SHEET_NAME = "Reports"

    # Column configurations
    COLUMN_WIDTHS = {
        "A": 280,  # ID
        "B": 300,  # ID пользователя
        "C": 200,  # Дата создания
        "D": 200,  # Имя
        "E": 250,  # Контакт
        "F": 400,  # Описание
    }

    # Border settings
    BORDER_COLOR = {"red": 0.4, "green": 0.4, "blue": 0.4}
    BORDER_STYLE = "SOLID"

    # Font settings
    FONT_FAMILY = "Open Sans"
    HEADER_FONT_SIZE = 12
    DATA_FONT_SIZE = 11


# Create output directory
ExportConfig.OUTPUT_DIR.mkdir(exist_ok=True)

# Configure logging with fresh log file (mode='w' automatically truncates)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(ExportConfig.LOG_FILE, encoding="utf-8", mode="w"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Suppress oauth2client file_cache warning
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class IssueReport:
    """Data class for IssueReport records."""

    id: str
    user_id: str | None
    created_at: datetime
    name: str
    contact: str
    description: str


@dataclass
class ExportResult:
    """Data class for export operation result."""

    success: bool
    message: str
    excel_file: str | None
    sheets_updated: bool
    records_count: int
    new_records_count: int


# =============================================================================
# DATABASE SERVICE
# =============================================================================


class DatabaseService:
    """Service for database operations."""

    def __init__(self, host: str, database: str, user: str, password: str, port: int):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.conn = None

    def connect(self) -> None:
        """Connect to the database."""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port,
            )
            logger.info("Database connection established successfully")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from the database."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def fetch_issue_reports(self) -> list[IssueReport]:
        """Fetch all IssueReport records from database."""
        if not self.conn:
            raise RuntimeError("Database not connected")

        query = """
        SELECT
            id,
            "userId" as user_id,
            "createdAt" as created_at,
            name,
            contact,
            description
        FROM "IssueReport"
        ORDER BY "createdAt" DESC
        """

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

                issue_reports = []
                for row in rows:
                    issue_reports.append(
                        IssueReport(
                            id=row["id"],
                            user_id=row["user_id"],
                            created_at=row["created_at"],
                            name=row["name"],
                            contact=row["contact"],
                            description=row["description"],
                        )
                    )

                # Double-check sorting to ensure newest first
                issue_reports.sort(key=lambda x: x.created_at, reverse=True)

                logger.info(f"Fetched and sorted {len(issue_reports)} issue reports by createdAt DESC")
                return issue_reports

        except psycopg2.Error as e:
            logger.error(f"Failed to fetch issue reports: {e}")
            raise


# =============================================================================
# EXCEL EXPORT SERVICE
# =============================================================================


class ExcelExportService:
    """Service for exporting data to Excel format."""

    def export(self, issue_reports: list[IssueReport]) -> str:
        """Export issue reports to Excel file."""
        filepath = ExportConfig.OUTPUT_DIR / "issue_reports.xlsx"

        # Remove existing file if it exists
        if filepath.exists():
            filepath.unlink()
            logger.info(f"Removed existing file: {filepath}")

        # Prepare data with Russian headers
        data = [
            {
                "ID": report.id,
                "ID пользователя": report.user_id or "N/A",
                "Дата создания": report.created_at.strftime("%d.%m.%Y %H:%M:%S"),
                "Имя": report.name,
                "Контакт": report.contact,
                "Описание": report.description,
            }
            for report in issue_reports
        ]

        # Create DataFrame and export
        df = pd.DataFrame(data)
        df.to_excel(filepath, sheet_name="Issue Reports", index=False)

        logger.info(f"Exported {len(issue_reports)} records to Excel: {filepath}")
        return str(filepath)


# =============================================================================
# GOOGLE SHEETS SERVICE
# =============================================================================


class GoogleSheetsService:
    """Service for Google Sheets operations."""

    def __init__(self):
        self.sheets_service = None
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Google Sheets API."""
        creds = None
        if ExportConfig.TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(ExportConfig.TOKEN_FILE), ExportConfig.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not ExportConfig.CREDENTIALS_FILE.exists():
                    raise FileNotFoundError(f"Credentials file '{ExportConfig.CREDENTIALS_FILE}' not found")

                flow = InstalledAppFlow.from_client_secrets_file(str(ExportConfig.CREDENTIALS_FILE), ExportConfig.SCOPES)
                creds = flow.run_local_server(port=0)

            with open(ExportConfig.TOKEN_FILE, "w") as token:
                token.write(creds.to_json())

        self.sheets_service = build("sheets", "v4", credentials=creds)
        logger.info("Google Sheets authentication successful")

    def get_existing_ids(self) -> set[str]:
        """Get existing record IDs from Google Sheets."""
        try:
            # First, ensure the sheet exists
            self._create_or_get_sheet()

            result = (
                self.sheets_service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=ExportConfig.SPREADSHEET_ID,
                    range=f"{ExportConfig.SHEET_NAME}!A:F",
                )
                .execute()
            )

            values = result.get("values", [])

            # If no data exists, create headers
            if not values:
                self._create_headers()
                return set()

            # Extract IDs from first column (skip header)
            existing_ids = {row[0] for row in values[1:] if row and len(row) > 0}
            logger.info(f"Found {len(existing_ids)} existing records in Google Sheets")
            return existing_ids

        except HttpError as error:
            logger.error(f"Failed to get existing records: {error}")
            return set()

    def _create_or_get_sheet(self) -> int:
        """Create or get existing Reports sheet."""
        try:
            # Try to get existing sheet
            result = self.sheets_service.spreadsheets().get(spreadsheetId=ExportConfig.SPREADSHEET_ID).execute()

            existing_sheets = result.get("sheets", [])
            for sheet in existing_sheets:
                if sheet["properties"]["title"] == ExportConfig.SHEET_NAME:
                    return sheet["properties"]["sheetId"]

            # Create new sheet if it doesn't exist
            request = {"addSheet": {"properties": {"title": ExportConfig.SHEET_NAME}}}

            result = (
                self.sheets_service.spreadsheets()
                .batchUpdate(
                    spreadsheetId=ExportConfig.SPREADSHEET_ID,
                    body={"requests": [request]},
                )
                .execute()
            )

            sheet_id = result["replies"][0]["addSheet"]["properties"]["sheetId"]
            logger.info(f"Created new sheet '{ExportConfig.SHEET_NAME}' with ID: {sheet_id}")
            return sheet_id

        except Exception as e:
            logger.error(f"Failed to create/get sheet: {e}")
            raise

    def append_reports(self, issue_reports: list[IssueReport]) -> int:
        """Add issue reports to Google Sheets, avoiding duplicates and maintaining sort order."""
        try:
            # Get existing IDs and filter out duplicates
            existing_ids = self.get_existing_ids()
            new_reports = [r for r in issue_reports if r.id not in existing_ids]

            # Always re-sort existing data, even if no new records
            if not new_reports:
                logger.info("No new records to add, but will re-sort existing data")

            # Sort by creation date (newest first - descending order)
            new_reports.sort(key=lambda x: x.created_at, reverse=True)

            # Get all existing data to re-sort everything
            existing_data = self._get_all_existing_data()

            # Combine existing data with new data and sort everything
            all_reports = existing_data + new_reports

            # Sort by creation date (newest first - descending order)
            all_reports.sort(key=lambda x: x.created_at, reverse=True)

            # Verify sorting is correct
            is_sorted = all(all_reports[i].created_at >= all_reports[i + 1].created_at for i in range(len(all_reports) - 1))

            if not is_sorted:
                logger.warning("Sorting verification failed - data may not be properly sorted!")
            else:
                logger.info(f"Sorted {len(all_reports)} total records by createdAt in descending order")

            # Clear existing data and re-insert everything in correct order
            self._clear_existing_data()

            # Prepare data for sheets (skip header row)
            values = [
                [
                    report.id,
                    report.user_id or "N/A",
                    report.created_at.strftime("%d.%m.%Y %H:%M:%S"),
                    report.name,
                    report.contact,
                    report.description,
                ]
                for report in all_reports
            ]

            # Insert all data at once
            body = {"values": values}
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=ExportConfig.SPREADSHEET_ID,
                range=f"{ExportConfig.SHEET_NAME}!A2:F{len(values) + 1}",
                valueInputOption="RAW",
                body=body,
            ).execute()

            # Apply formatting to all rows
            if all_reports:
                self._apply_formatting(len(all_reports))

            if new_reports:
                logger.info(f"Added {len(new_reports)} new records and re-sorted {len(all_reports)} total records in Google Sheets")
            else:
                logger.info(f"Re-sorted {len(all_reports)} existing records in Google Sheets")
            return len(new_reports)

        except HttpError as error:
            logger.error(f"Failed to add data to Google Sheets: {error}")
            raise

    def _create_headers(self) -> None:
        """Create headers in Google Sheets if they don't exist."""
        headers = [
            "ID",
            "ID пользователя",
            "Дата создания",
            "Имя",
            "Контакт",
            "Описание",
        ]

        body = {"values": [headers]}
        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=ExportConfig.SPREADSHEET_ID,
            range=f"{ExportConfig.SHEET_NAME}!A1:F1",
            valueInputOption="RAW",
            body=body,
        ).execute()

        # Apply formatting
        self._apply_header_formatting()
        self._apply_column_widths()

        logger.info("Created Russian headers in Google Sheets")

    def _get_sheet_id(self) -> int:
        """Get the sheet ID for the Reports sheet."""
        return self._create_or_get_sheet()

    def _apply_header_formatting(self) -> None:
        """Apply formatting to the header row."""
        try:
            sheet_id = self._get_sheet_id()

            requests = [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 6,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "textFormat": {
                                    "fontSize": ExportConfig.HEADER_FONT_SIZE,
                                    "fontFamily": ExportConfig.FONT_FAMILY,
                                    "bold": True,
                                },
                                "horizontalAlignment": "CENTER",
                                "verticalAlignment": "MIDDLE",
                                "wrapStrategy": "WRAP",
                                "borders": {
                                    "top": {
                                        "style": ExportConfig.BORDER_STYLE,
                                        "color": ExportConfig.BORDER_COLOR,
                                    },
                                    "bottom": {
                                        "style": ExportConfig.BORDER_STYLE,
                                        "color": ExportConfig.BORDER_COLOR,
                                    },
                                    "left": {
                                        "style": ExportConfig.BORDER_STYLE,
                                        "color": ExportConfig.BORDER_COLOR,
                                    },
                                    "right": {
                                        "style": ExportConfig.BORDER_STYLE,
                                        "color": ExportConfig.BORDER_COLOR,
                                    },
                                },
                            }
                        },
                        "fields": "userEnteredFormat",
                    }
                }
            ]

            self.sheets_service.spreadsheets().batchUpdate(spreadsheetId=ExportConfig.SPREADSHEET_ID, body={"requests": requests}).execute()

            logger.info("Applied header formatting")

        except HttpError as error:
            logger.error(f"Failed to apply header formatting: {error}")

    def _apply_column_widths(self) -> None:
        """Apply column width formatting."""
        try:
            sheet_id = self._get_sheet_id()
            requests = []

            for col, width in ExportConfig.COLUMN_WIDTHS.items():
                col_index = ord(col) - ord("A")
                requests.append(
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": col_index,
                                "endIndex": col_index + 1,
                            },
                            "properties": {"pixelSize": width},
                            "fields": "pixelSize",
                        }
                    }
                )

            if requests:
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=ExportConfig.SPREADSHEET_ID,
                    body={"requests": requests},
                ).execute()

                logger.info("Applied column width formatting")

        except HttpError as error:
            logger.error(f"Failed to apply column width formatting: {error}")

    def _get_all_existing_data(self) -> list[IssueReport]:
        """Get all existing data from Google Sheets as IssueReport objects."""
        try:
            result = (
                self.sheets_service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=ExportConfig.SPREADSHEET_ID,
                    range=f"{ExportConfig.SHEET_NAME}!A:F",
                )
                .execute()
            )

            values = result.get("values", [])

            # Skip header row and empty rows
            existing_reports = []
            for row in values[1:]:  # Skip header
                if len(row) >= 6:  # Ensure we have all required columns
                    try:
                        # Parse the date string back to datetime
                        created_at_str = row[2]  # Date column

                        # Handle different possible date formats
                        try:
                            created_at = datetime.strptime(created_at_str, "%d.%m.%Y %H:%M:%S")
                        except ValueError:
                            # Try alternative format if the first one fails
                            created_at = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")

                        existing_reports.append(
                            IssueReport(
                                id=row[0],
                                user_id=row[1] if row[1] != "N/A" else None,
                                created_at=created_at,
                                name=row[3],
                                contact=row[4],
                                description=row[5],
                            )
                        )
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Skipping malformed row: {row}, error: {e}")
                        continue

            # Sort existing reports by creation date (newest first)
            existing_reports.sort(key=lambda x: x.created_at, reverse=True)

            logger.info(f"Retrieved and sorted {len(existing_reports)} existing records from Google Sheets")
            return existing_reports

        except HttpError as error:
            logger.error(f"Failed to get existing data: {error}")
            return []

    def _clear_existing_data(self) -> None:
        """Clear all existing data rows (keep header)."""
        try:
            # Get current data to determine range
            result = (
                self.sheets_service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=ExportConfig.SPREADSHEET_ID,
                    range=f"{ExportConfig.SHEET_NAME}!A:F",
                )
                .execute()
            )

            values = result.get("values", [])

            if len(values) <= 1:  # Only header or no data
                return

            # Clear all data rows (keep header)
            range_to_clear = f"{ExportConfig.SHEET_NAME}!A2:F{len(values)}"
            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=ExportConfig.SPREADSHEET_ID,
                range=range_to_clear,
            ).execute()

            logger.info(f"Cleared {len(values) - 1} existing data rows")

        except HttpError as error:
            logger.error(f"Failed to clear existing data: {error}")

    def _apply_formatting(self, total_rows_count: int) -> None:
        """Apply formatting to all data rows."""
        try:
            sheet_id = self._get_sheet_id()

            if total_rows_count <= 0:
                return

            # Calculate range for all data rows (skip header)
            start_row = 1  # Start after header
            end_row = total_rows_count + 1  # +1 because we're after header

            requests = [
                # Apply font formatting to all data rows
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row,
                            "endRowIndex": end_row,
                            "startColumnIndex": 0,
                            "endColumnIndex": 6,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "textFormat": {
                                    "fontSize": ExportConfig.DATA_FONT_SIZE,
                                    "fontFamily": ExportConfig.FONT_FAMILY,
                                },
                                "verticalAlignment": "TOP",
                                "wrapStrategy": "WRAP",
                                "borders": {
                                    "top": {
                                        "style": ExportConfig.BORDER_STYLE,
                                        "color": ExportConfig.BORDER_COLOR,
                                    },
                                    "bottom": {
                                        "style": ExportConfig.BORDER_STYLE,
                                        "color": ExportConfig.BORDER_COLOR,
                                    },
                                    "left": {
                                        "style": ExportConfig.BORDER_STYLE,
                                        "color": ExportConfig.BORDER_COLOR,
                                    },
                                    "right": {
                                        "style": ExportConfig.BORDER_STYLE,
                                        "color": ExportConfig.BORDER_COLOR,
                                    },
                                },
                            }
                        },
                        "fields": "userEnteredFormat",
                    }
                }
            ]

            self.sheets_service.spreadsheets().batchUpdate(spreadsheetId=ExportConfig.SPREADSHEET_ID, body={"requests": requests}).execute()

            logger.info(f"Applied formatting to {total_rows_count} data rows")

        except HttpError as error:
            logger.error(f"Failed to apply formatting to data rows: {error}")
            # Don't raise to avoid breaking the main export process


# =============================================================================
# MAIN EXPORTER CLASS
# =============================================================================


class IssueReportExporter:
    """Main orchestrator class for issue report export operations."""

    def __init__(
        self,
        db_service: DatabaseService,
        excel_service: ExcelExportService,
        sheets_service: GoogleSheetsService,
    ):
        self.db_service = db_service
        self.excel_service = excel_service
        self.sheets_service = sheets_service

    def run_export(self) -> ExportResult:
        """Run the complete export process."""
        try:
            # Connect to database and fetch data
            self.db_service.connect()
            issue_reports = self.db_service.fetch_issue_reports()

            if not issue_reports:
                return ExportResult(
                    success=True,
                    message="No issue reports found",
                    excel_file=None,
                    sheets_updated=False,
                    records_count=0,
                    new_records_count=0,
                )

            # Export to Excel
            excel_file = self.excel_service.export(issue_reports)

            # Update Google Sheets
            new_records_count = 0
            sheets_updated = False
            try:
                new_records_count = self.sheets_service.append_reports(issue_reports)
                sheets_updated = True
            except Exception as e:
                logger.warning(f"Google Sheets update failed: {e}")

            return ExportResult(
                success=True,
                message="Export completed successfully",
                excel_file=excel_file,
                sheets_updated=sheets_updated,
                records_count=len(issue_reports),
                new_records_count=new_records_count,
            )

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return ExportResult(
                success=False,
                message=str(e),
                excel_file=None,
                sheets_updated=False,
                records_count=0,
                new_records_count=0,
            )
        finally:
            self.db_service.disconnect()


# =============================================================================
# FACTORY AND APPLICATION CLASSES
# =============================================================================


class IssueReportExportFactory:
    """Factory for creating export components."""

    @staticmethod
    def create_database_service(config: dict[str, str | int]) -> DatabaseService:
        """Create database service instance."""
        # Ensure all config values are of the correct types
        host = config.get("host", "")
        database = config.get("database", "")
        user = config.get("user", "")
        password = config.get("password", "")
        port_raw = config.get("port", 5432)

        # Convert to proper types
        host_str = str(host) if host is not None else ""
        database_str = str(database) if database is not None else ""
        user_str = str(user) if user is not None else ""
        password_str = str(password) if password is not None else ""
        port_int = int(port_raw) if port_raw is not None else 5432

        return DatabaseService(
            host=host_str,
            database=database_str,
            user=user_str,
            password=password_str,
            port=port_int,
        )

    @staticmethod
    def create_excel_service() -> ExcelExportService:
        """Create Excel export service."""
        return ExcelExportService()

    @staticmethod
    def create_sheets_service() -> GoogleSheetsService:
        """Create Google Sheets service."""
        return GoogleSheetsService()

    @staticmethod
    def create_exporter(
        db_service: DatabaseService,
        excel_service: ExcelExportService,
        sheets_service: GoogleSheetsService,
    ) -> IssueReportExporter:
        """Create main exporter with all services."""
        return IssueReportExporter(db_service, excel_service, sheets_service)


class IssueReportExportApplication:
    """Main application class for issue report export."""

    def __init__(self):
        self.config = self._load_config()
        self.factory = IssueReportExportFactory()

    def _load_config(self) -> dict[str, str | int]:
        """Load database configuration."""
        config = configparser.ConfigParser()
        config_path = Path("../database.ini")

        if not config_path.exists():
            raise FileNotFoundError("database.ini file not found")

        config.read(config_path)
        if "postgresql" not in config:
            raise ValueError("postgresql section not found in database.ini")

        db_config = config["postgresql"]
        return {
            "host": db_config.get("host"),
            "database": db_config.get("database"),
            "user": db_config.get("user"),
            "password": db_config.get("password"),
            "port": int(db_config.get("port", "5432")),
        }

    def _get_user_confirmation(self) -> bool:
        """Get user confirmation before proceeding with export."""
        print("\nIssue Report Export Script")
        print("=" * 40)
        print("\nDatabase Configuration:")
        print("=" * 40)
        print(f"Host: {self.config['host']}")
        print(f"Database: {self.config['database']}")
        print(f"User: {self.config['user']}")
        print(f"Port: {self.config['port']}")
        print("=" * 40)
        print("\nGoogle Sheets:")
        print(f"Spreadsheet ID: {ExportConfig.SPREADSHEET_ID}")
        print(f"Sheet: {ExportConfig.SHEET_NAME}")
        print("=" * 40)
        print("\nThis script will:")
        print("1. Connect to database and fetch IssueReport records")
        print("2. Export data to Excel file in 'issue_reports/' directory")
        print("3. Create 'Reports' sheet in Google Sheets if it doesn't exist")
        print("4. Add new data to Google Sheets with Russian headers (avoiding duplicates)")
        print("5. Apply professional formatting with Open Sans font")
        print("6. Log all operations to console and file")

        response = input("\nDo you want to proceed? (y/N): ").strip().lower()
        return response in ["y", "yes"]

    def run(self) -> None:
        """Run the issue report export application."""
        try:
            if not self._get_user_confirmation():
                print("Export cancelled by user.")
                return

            # Create services
            db_service = self.factory.create_database_service(self.config)
            excel_service = self.factory.create_excel_service()
            sheets_service = self.factory.create_sheets_service()
            exporter = self.factory.create_exporter(db_service, excel_service, sheets_service)

            # Run export
            print("\nStarting export process...")
            result = exporter.run_export()

            # Display results
            self._display_results(result)

        except Exception as e:
            print(f"Error: {e}")
            logger.error(f"Application error: {e}")

    def _display_results(self, result: ExportResult) -> None:
        """Display export results."""
        print("\nExport Results:")
        print("=" * 50)

        if result.success:
            print("Status: Success")
            print(f"Total Records: {result.records_count}")
            print(f"New Records Added: {result.new_records_count}")
            if result.excel_file:
                print(f"Excel File: {result.excel_file}")
            if result.sheets_updated:
                print("Google Sheets: Updated")
                print(f"URL: https://docs.google.com/spreadsheets/d/{ExportConfig.SPREADSHEET_ID}")
            else:
                print("Google Sheets: Not updated (authentication or access error)")
        else:
            print(f"Status: Error - {result.message}")


def main():
    """Main function to run the export process."""
    load_dotenv()

    app = IssueReportExportApplication()
    app.run()


if __name__ == "__main__":
    main()
