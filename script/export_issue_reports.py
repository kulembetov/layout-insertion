#!/usr/bin/env python3
"""
Script to export IssueReport table from database to Excel and append to Google Sheets.
"""

import os
import sys
import logging
import configparser
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Google API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Create directory for logs and exports
os.makedirs('issue_reports', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('issue_reports/issue_reports.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Suppress oauth2client file_cache warning
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

# Configuration
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CREDENTIALS_FILE = '../credentials.json'
TOKEN_FILE = '../token.json'
SPREADSHEET_ID = '1GGUznHFHmsjfH2bqCvEsbBm8rQWalcRa8dD7EQwq-KI'
SHEET_NAME = 'Reports'


@dataclass
class IssueReport:
    """Data class for IssueReport records."""
    id: str
    user_id: Optional[str]
    created_at: datetime
    name: str
    contact: str
    description: str


class IssueReportExporter:
    """Main class to handle the complete export process."""
    
    def __init__(self, host: str, database: str, user: str, password: str, port: int):
        self.db_config = {'host': host, 'database': database, 'user': user, 'password': password, 'port': port}
        self.connection = None
        self.sheets_service = None
        self.output_dir = "exports"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def connect_db(self) -> None:
        """Establish database connection."""
        try:
            self.connection = psycopg2.connect(**self.db_config)
            logger.info("Database connection established")
        except psycopg2.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def disconnect_db(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def fetch_issue_reports(self) -> List[IssueReport]:
        """Fetch all IssueReport records from database."""
        if not self.connection:
            raise RuntimeError("Database connection not established")
        
        query = """
        SELECT id, "userId" as user_id, "createdAt" as created_at, name, contact, description
        FROM "IssueReport" ORDER BY "createdAt" DESC
        """
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                
                issue_reports = []
                for row in rows:
                    issue_reports.append(IssueReport(
                        id=row['id'],
                        user_id=row['user_id'],
                        created_at=row['created_at'],
                        name=row['name'],
                        contact=row['contact'],
                        description=row['description']
                    ))
                
                logger.info(f"Fetched {len(issue_reports)} issue reports")
                return issue_reports
                
        except psycopg2.Error as e:
            logger.error(f"Failed to fetch issue reports: {e}")
            raise
    
    def authenticate_sheets(self) -> None:
        """Authenticate with Google Sheets API."""
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_FILE):
                    raise FileNotFoundError(f"Credentials file '{CREDENTIALS_FILE}' not found")
                
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        
        self.sheets_service = build('sheets', 'v4', credentials=creds)
        logger.info("Google Sheets API authenticated")
    
    def get_existing_ids(self) -> Set[str]:
        """Get existing record IDs from Google Sheets."""
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID, range=f'{SHEET_NAME}!A:F'
            ).execute()
            
            values = result.get('values', [])
            
            # If no data exists, create headers
            if not values:
                self._create_headers()
                return set()
            
            existing_ids = {row[0] for row in values[1:] if row}
            logger.info(f"Found {len(existing_ids)} existing records")
            return existing_ids
            
        except HttpError as error:
            logger.error(f"Failed to get existing records: {error}")
            return set()
    
    def export_to_excel(self, issue_reports: List[IssueReport]) -> str:
        """Export issue reports to Excel file."""
        os.makedirs('issue_reports', exist_ok=True)
        filepath = 'issue_reports/issue_reports.xlsx'
        
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Removed existing file: {filepath}")
        
        data = [{
            'ID': report.id,
            'User ID': report.user_id or 'N/A',
            'Created At': report.created_at,
            'Name': report.name,
            'Contact': report.contact,
            'Description': report.description
        } for report in issue_reports]
        
        df = pd.DataFrame(data)
        df.to_excel(filepath, sheet_name='Issue Reports', index=False)
        
        logger.info(f"Exported {len(issue_reports)} records to Excel: {filepath}")
        return filepath
    
    def append_to_sheets(self, issue_reports: List[IssueReport]) -> None:
        """Add issue reports to Google Sheets."""
        try:
            # Get existing IDs and filter duplicates
            existing_ids = self.get_existing_ids()
            new_reports = [r for r in issue_reports if r.id not in existing_ids]
            
            if not new_reports:
                logger.info("No new records to add")
                return
            
            # Sort by creation date and prepare data
            new_reports.sort(key=lambda x: x.created_at)
            values = [[
                report.id,
                report.user_id or 'N/A',
                report.created_at.strftime('%d.%m.%Y %H:%M:%S'),
                report.name,
                report.contact,
                report.description
            ] for report in new_reports]
            
            # Append data
            body = {'values': values}
            self.sheets_service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range=f'{SHEET_NAME}!A:F',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            if new_reports:
                self._apply_font_formatting(len(new_reports))
            
            logger.info(f"Added {len(new_reports)} new records to Google Sheets")
            
        except HttpError as error:
            logger.error(f"Failed to add data to Google Sheets: {error}")
            raise
    
    def _create_headers(self) -> None:
        """Create headers in the Google Sheets if they don't exist."""
        headers = ['ID', 'User ID', 'Created At', 'Name', 'Contact', 'Description']
        
        body = {'values': [headers]}
        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{SHEET_NAME}!A1:F1',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        # Apply header formatting
        self._apply_header_formatting()
        logger.info("Created headers in Google Sheets")
    
    def _apply_header_formatting(self) -> None:
        """Apply formatting to the header row."""
        try:
            sheet_id = self._get_sheet_id()
            
            requests = [
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 0,
                            'endRowIndex': 1,
                            'startColumnIndex': 0,
                            'endColumnIndex': 6
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'textFormat': {
                                    'fontSize': 12,
                                    'fontFamily': 'Open Sans',
                                    'bold': True
                                }
                            }
                        },
                        'fields': 'userEnteredFormat.textFormat'
                    }
                }
            ]
            
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={'requests': requests}
            ).execute()
            
            logger.info("Applied header formatting")
            
        except HttpError as error:
            logger.error(f"Failed to apply header formatting: {error}")
    
    def _get_sheet_id(self) -> int:
        """Get the sheet ID for the Reports sheet."""
        result = self.sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        for sheet in result.get('sheets', []):
            if sheet['properties']['title'] == SHEET_NAME:
                return sheet['properties']['sheetId']
        raise ValueError(f"Sheet '{SHEET_NAME}' not found")
    
    def _apply_font_formatting(self, new_rows_count: int) -> None:
        """Apply Open Sans font formatting to the newly added rows."""
        try:
            sheet_id = self._get_sheet_id()
            
            # Get the current row count to determine the range for new rows
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID, range=f'{SHEET_NAME}!A:F'
            ).execute()
            
            values = result.get('values', [])
            total_rows = len(values)
            
            if total_rows <= 1:  # Only header or no data
                return
            
            # Calculate the range for the newly added rows (last new_rows_count rows)
            start_row = total_rows - new_rows_count + 1  # +1 because sheets are 1-indexed
            
            requests = [
                # Apply Open Sans font to the newly added rows
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': start_row,
                            'endRowIndex': total_rows + 1,  # +1 because endRowIndex is exclusive
                            'startColumnIndex': 0,
                            'endColumnIndex': 6
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'textFormat': {
                                    'fontSize': 11,
                                    'fontFamily': 'Open Sans'
                                }
                            }
                        },
                        'fields': 'userEnteredFormat.textFormat'
                    }
                },
                # Add borders to the newly added rows
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': start_row,
                            'endRowIndex': total_rows + 1,  # +1 because endRowIndex is exclusive
                            'startColumnIndex': 0,
                            'endColumnIndex': 6
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'borders': {
                                    'top': {'style': 'SOLID', 'color': {'red': 0.8, 'green': 0.8, 'blue': 0.8}},
                                    'bottom': {'style': 'SOLID', 'color': {'red': 0.8, 'green': 0.8, 'blue': 0.8}},
                                    'left': {'style': 'SOLID', 'color': {'red': 0.8, 'green': 0.8, 'blue': 0.8}},
                                    'right': {'style': 'SOLID', 'color': {'red': 0.8, 'green': 0.8, 'blue': 0.8}}
                                }
                            }
                        },
                        'fields': 'userEnteredFormat.borders'
                    }
                }
            ]
            
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Applied Open Sans font formatting to {new_rows_count} new rows")
            
        except HttpError as error:
            logger.error(f"Failed to apply font formatting: {error}")
            # Don't raise the error to avoid breaking the main export process
    
    def run_export(self) -> Dict[str, Any]:
        """Run the complete export process."""
        try:
            self.connect_db()
            issue_reports = self.fetch_issue_reports()
            
            if not issue_reports:
                return {'success': True, 'message': 'No issue reports found', 'excel_file': None, 'sheets_updated': False, 'records_count': 0}
            
            excel_file = self.export_to_excel(issue_reports)
            
            sheets_updated = False
            try:
                self.authenticate_sheets()
                self.append_to_sheets(issue_reports)
                sheets_updated = True
            except Exception as e:
                logger.warning(f"Google Sheets update failed: {e}")
            
            return {
                'success': True,
                'message': 'Export completed successfully',
                'excel_file': excel_file,
                'sheets_updated': sheets_updated,
                'records_count': len(issue_reports)
            }
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return {'success': False, 'message': str(e), 'excel_file': None, 'sheets_updated': False, 'records_count': 0}
        finally:
            self.disconnect_db()


def load_database_config() -> Dict[str, Any]:
    """Load database configuration from database.ini file."""
    config = configparser.ConfigParser()
    if not os.path.exists('../database.ini'):
        raise FileNotFoundError("database.ini file not found")
    
    config.read('../database.ini')
    if 'postgresql' not in config:
        raise ValueError("postgresql section not found in database.ini")
    
    db_config = config['postgresql']
    return {
        'host': db_config.get('host'),
        'database': db_config.get('database'),
        'user': db_config.get('user'),
        'password': db_config.get('password'),
        'port': int(db_config.get('port', 5432))
    }


def get_user_confirmation() -> bool:
    """Get user confirmation before proceeding with export."""
    try:
        db_config = load_database_config()
        print("\nDatabase Configuration:")
        print("=" * 40)
        print(f"Host: {db_config['host']}")
        print(f"Database: {db_config['database']}")
        print(f"User: {db_config['user']}")
        print(f"Port: {db_config['port']}")
        print("=" * 40)
        print(f"\nGoogle Sheets:")
        print(f"Spreadsheet ID: {SPREADSHEET_ID}")
        print(f"Sheet: {SHEET_NAME}")
        print("=" * 40)
        print("\nThis script will:")
        print("1. Connect to database and fetch IssueReport records")
        print("2. Export data to Excel file in 'exports/' directory")
        print("3. Add data to Google Sheets as new rows (avoiding duplicates)")
        print("4. Log all operations to console and file")
        
        response = input("\nDo you want to proceed? (y/N): ").strip().lower()
        return response in ['y', 'yes']
        
    except Exception as e:
        print(f"Error loading database configuration: {e}")
        return False


def main():
    """Main function to run the export process."""
    load_dotenv()
    print("Issue Report Export Script")
    print("=" * 40)
    
    if not get_user_confirmation():
        print("Export cancelled by user.")
        sys.exit(0)
    
    try:
        db_config = load_database_config()
        exporter = IssueReportExporter(**db_config)
        
        print("\nStarting export process...")
        result = exporter.run_export()
        
        if result['success']:
            print(f"\nExport completed successfully!")
            print(f"Records exported: {result['records_count']}")
            if result['excel_file']:
                print(f"Excel file: {result['excel_file']}")
            if result['sheets_updated']:
                print(f"Google Sheets updated: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
            else:
                print("Google Sheets was not updated (authentication or access error)")
        else:
            print(f"\nExport failed: {result['message']}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 