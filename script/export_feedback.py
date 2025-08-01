#!/usr/bin/env python3
"""
Script to export PresentationFeedback data to Google Sheets with daily statistics and comments.

This module provides a comprehensive feedback export system with:
- Database connectivity and data fetching
- Statistics calculation
- Google Sheets integration
- Excel export capabilities
- Configurable formatting and styling

Design Patterns Used:
- Strategy Pattern: Different export strategies (Excel, Sheets)
- Factory Pattern: Creating different data processors
- Builder Pattern: Building complex spreadsheet configurations
- Observer Pattern: Logging and progress tracking
- Dependency Injection: Configurable services
"""

import os
import sys
import logging
import configparser
from datetime import datetime, date
from typing import List, Dict, Optional, Union, Protocol, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from pathlib import Path

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

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

class ExportConfig:
    """Configuration class for export settings."""
    
    # Directory settings
    OUTPUT_DIR = Path("feedback_reports")
    LOG_FILE = OUTPUT_DIR / "feedback_export.log"
    
    # Google Sheets settings
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    CREDENTIALS_FILE = Path("../credentials.json")
    TOKEN_FILE = Path("../token.json")
    SPREADSHEET_ID = "1GGUznHFHmsjfH2bqCvEsbBm8rQWalcRa8dD7EQwq-KI"
    
    # Column configurations
    COLUMN_WIDTHS = {
        'A': 230,  # Statistics column A
        'B': 230,  # Statistics column B  
        'C': 230,  # Statistics column C
        'D': 300,  # Тема презентации
        'E': 280,  # ID презентации
        'F': 150,  # Оценка
        'G': 400,  # Комментарий
        'H': 350,  # Использование регенераций
        'I': 300,  # Язык презентации
        'J': 350,  # Стиль изображений
        'K': 300,  # Настройки презентации
    }
    
    # Border settings
    BORDER_COLOR = {"red": 0.4, "green": 0.4, "blue": 0.4}
    BORDER_STYLE = "SOLID"
    
    # Font settings
    FONT_FAMILY = "Open Sans"
    HEADER_FONT_SIZE = 12
    DATA_FONT_SIZE = 10

# Create output directory
ExportConfig.OUTPUT_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(ExportConfig.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Suppress oauth2client file_cache warning
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)


# =============================================================================
# DATA MODELS AND ENUMS
# =============================================================================

class PresentationRating(Enum):
    """Enum for presentation ratings."""
    LIKE = "like"
    NEUTRAL = "neutral"
    DISLIKE = "dislike"


@dataclass
class FeedbackRecord:
    """Data class for PresentationFeedback records."""
    id: str
    rating: PresentationRating
    comment: Optional[str]
    presentation_id: str
    presentation_name: Optional[str]
    created_at: Optional[datetime]
    theme: Optional[str]
    lang: Optional[str]
    presentation_source: Optional[str]
    text_amount: Optional[str]
    text_tone: Optional[str]
    audience: Optional[str]
    text_change: Optional[str]
    color: Optional[str]
    font: Optional[str]
    use_web_search: Optional[bool]
    image_style_type: Optional[str]
    slides_count: Optional[int]
    slides_titles: Optional[str]
    user_context: Optional[str]
    file_context: Optional[str]
    user_created_at: Optional[datetime]
    user_presentations_count: Optional[int]
    user_role: Optional[str]
    user_contact: Optional[str]
    presentation_status: Optional[str]
    symbols_used: Optional[int]
    regenerations_left: Optional[int]
    is_archived: Optional[bool]
    generation_error: Optional[str]
    retry_count: Optional[int]
    images_in_process: Optional[int]
    text_regenerations_left: Optional[int]
    image_regenerations_left: Optional[int]
    infographics_generated_left: Optional[int]
    slide_changes_left: Optional[int]
    download_count: Optional[int]
    download_format: Optional[str]


@dataclass
class Statistics:
    """Data class for feedback statistics."""
    likes: int
    neutral: int
    dislikes: int
    likes_percent: float
    neutral_percent: float
    dislikes_percent: float
    total: int
    presentations_count: int
    avg_symbols: int
    avg_text_regenerations: int
    avg_image_regenerations: int
    avg_infographics: int
    avg_slide_changes: int
    avg_user_presentations: int
    download_rate: float
    error_rate: float


@dataclass
class ExportResult:
    """Data class for export operation result."""
    success: bool
    message: str
    excel_file: Optional[str]
    sheets_updated: bool
    records_count: int
    statistics: Optional[Statistics]
    presentations_count: int


# =============================================================================
# SERVICE INTERFACES (Protocols)
# =============================================================================

class DatabaseService(Protocol):
    """Protocol for database operations."""
    
    def connect(self) -> None:
        """Connect to the database."""
        ...
    
    def disconnect(self) -> None:
        """Disconnect from the database."""
        ...
    
    def fetch_feedback_data(self, start_date: date, end_date: Optional[date] = None) -> List[FeedbackRecord]:
        """Fetch feedback data from database."""
        ...


class ExportStrategy(Protocol):
    """Protocol for export strategies."""
    
    def export(self, feedback_records: List[FeedbackRecord], stats: Statistics, 
               start_date: date, end_date: Optional[date] = None) -> ExportResult:
        """Export data using this strategy."""
        ...


class DataProcessor(Protocol):
    """Protocol for data processing operations."""
    
    def process_records(self, records: List[FeedbackRecord]) -> List[FeedbackRecord]:
        """Process and transform records."""
        ...
    
    def calculate_statistics(self, records: List[FeedbackRecord]) -> Statistics:
        """Calculate statistics from records."""
        ...


# =============================================================================
# CONCRETE IMPLEMENTATIONS
# =============================================================================

class DatabaseServiceImpl:
    """Concrete implementation of database service."""
    
    def __init__(self, host: str, database: str, user: str, password: str, port: int):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.conn = None
        self.cursor = None

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
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            logger.info("Database connection established successfully")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self) -> None:
        """Disconnect from the database."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def fetch_feedback_data(self, start_date: date, end_date: Optional[date] = None) -> List[FeedbackRecord]:
        """Fetch feedback data from database."""
        if not self.conn:
            raise RuntimeError("Database not connected")
            
        # If end_date is not provided, use start_date for single day
        if end_date is None:
            end_date = start_date

        query = """
        SELECT 
            pf.id,
            pf.rating,
            pf.comment,
            pf."presentationId" as presentation_id,
            ps.title as presentation_name,
            p."createdAt" as created_at,
            ps.theme,
            ps.lang,
            ps."presentationSource" as presentation_source,
            ps."textAmount" as text_amount,
            ps."textTone" as text_tone,
            ps.audience,
            ps."textChange" as text_change,
            ps.color,
            ps.font,
            ps."useWebSearch" as use_web_search,
            ps."imageStyleType" as image_style_type,
            ps."slidesCount" as slides_count,
            ps."slidesTitles" as slides_titles,
            ps."userContext" as user_context,
            ps."fileContext" as file_context,
            u."createdAt" as user_created_at,
            u."presentationsCount" as user_presentations_count,
            u.role as user_role,
            auth_info.contact_info,
            p.status as presentation_status,
            p.symbols as symbols_used,
            p."textRegenerationsLeft" as regenerations_left,
            p."isArchived" as is_archived,
            gc.error as generation_error,
            gc."retryCount" as retry_count,
            gc."imagesInProcess" as images_in_process,
            pl."textRegeneration" as text_regenerations_left,
            pl."imageOptionRegeneration" as image_regenerations_left,
            pl."infographikGeneration" as infographics_generated_left,
            pl."slideChange" as slide_changes_left,
            COALESCE(download_stats.download_count, 0) as download_count,
            download_stats.download_format
        FROM "PresentationFeedback" pf
        LEFT JOIN "Presentation" p ON pf."presentationId" = p.id
        LEFT JOIN "PresentationSettings" ps ON p.id = ps."presentationId"
        LEFT JOIN "User" u ON p."userId" = u.id
        LEFT JOIN (
            SELECT 
                "userId",
                STRING_AGG(
                    CASE 
                        WHEN provider = 'google' THEN key
                        WHEN provider = 'telegram' THEN key
                        WHEN provider = 'yandex' THEN key
                        WHEN provider = 'vkontakte' THEN key
                        ELSE NULL
                    END, 
                    ', '
                ) as contact_info
            FROM "Auth"
            WHERE provider IN ('google', 'telegram', 'yandex', 'vkontakte')
            GROUP BY "userId"
        ) auth_info ON u.id = auth_info."userId"
        LEFT JOIN "GenerationContext" gc ON p.id = gc."presentationId"
        LEFT JOIN "PresentationLimits" pl ON p.id = pl."presentationId"
        LEFT JOIN (
            SELECT 
                "presentationId",
                COUNT(*) as download_count,
                STRING_AGG(DISTINCT "downloadFormat"::text, ', ') as download_format
            FROM "PresentationDownload"
            GROUP BY "presentationId"
        ) download_stats ON p.id = download_stats."presentationId"
        WHERE DATE(p."createdAt") BETWEEN %s AND %s
        ORDER BY pf."presentationId", p."createdAt" DESC
        """

        try:
            self.cursor.execute(query, (start_date, end_date))
            rows = self.cursor.fetchall()

            feedback_records = []
            for row in rows:
                feedback_records.append(
                    FeedbackRecord(
                        id=row["id"],
                        rating=PresentationRating(row["rating"]),
                        comment=row["comment"],
                        presentation_id=row["presentation_id"],
                        presentation_name=row["presentation_name"],
                        created_at=row["created_at"],
                        theme=row["theme"],
                        lang=row["lang"],
                        presentation_source=row["presentation_source"],
                        text_amount=row["text_amount"],
                        text_tone=row["text_tone"],
                        audience=row["audience"],
                        text_change=row["text_change"],
                        color=row["color"],
                        font=row["font"],
                        use_web_search=row["use_web_search"],
                        image_style_type=row["image_style_type"],
                        slides_count=row["slides_count"],
                        slides_titles=row["slides_titles"],
                        user_context=row["user_context"],
                        file_context=row["file_context"],
                        user_created_at=row["user_created_at"],
                        user_presentations_count=row["user_presentations_count"],
                        user_role=row["user_role"],
                        user_contact=row["contact_info"],
                        presentation_status=row["presentation_status"],
                        symbols_used=row["symbols_used"],
                        regenerations_left=row["regenerations_left"],
                        is_archived=row["is_archived"],
                        generation_error=row["generation_error"],
                        retry_count=row["retry_count"],
                        images_in_process=row["images_in_process"],
                        text_regenerations_left=row["text_regenerations_left"],
                        image_regenerations_left=row["image_regenerations_left"],
                        infographics_generated_left=row["infographics_generated_left"],
                        slide_changes_left=row["slide_changes_left"],
                        download_count=row["download_count"],
                        download_format=row["download_format"],
                    )
                )

            date_range_str = (
                f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
                if start_date != end_date
                else start_date.strftime("%d.%m.%Y")
            )
            logger.info(f"Fetched {len(feedback_records)} feedback records for {date_range_str}")
            return feedback_records

        except psycopg2.Error as e:
            logger.error(f"Failed to fetch feedback records: {e}")
            raise


class DataProcessorImpl:
    """Concrete implementation of data processor."""
    
    def process_records(self, records: List[FeedbackRecord]) -> List[FeedbackRecord]:
        """Process and transform records."""
        # Filter records with comments and sort by date
        records_with_comments = [record for record in records if record.comment]
        sorted_records = sorted(
            records_with_comments,
            key=lambda x: x.created_at if x.created_at else datetime.min,
            reverse=True
        )
        return sorted_records
    
    def calculate_statistics(self, records: List[FeedbackRecord]) -> Statistics:
        """Calculate statistics from records."""
        if not records:
            return Statistics(
                likes=0, neutral=0, dislikes=0,
                likes_percent=0.0, neutral_percent=0.0, dislikes_percent=0.0,
                total=0, presentations_count=0,
                avg_symbols=0, avg_text_regenerations=0, avg_image_regenerations=0,
                avg_infographics=0, avg_slide_changes=0, avg_user_presentations=0,
                download_rate=0.0, error_rate=0.0
            )
        
        total = len(records)
        likes = sum(1 for record in records if record.rating == PresentationRating.LIKE)
        neutral = sum(1 for record in records if record.rating == PresentationRating.NEUTRAL)
        dislikes = sum(1 for record in records if record.rating == PresentationRating.DISLIKE)

        # Count unique presentations
        unique_presentations = len(set(record.presentation_id for record in records))

        # Calculate additional metrics
        symbols_used = [r.symbols_used for r in records if r.symbols_used is not None]
        avg_symbols = sum(symbols_used) / len(symbols_used) if symbols_used else 0

        text_regenerations = [r.text_regenerations_left for r in records if r.text_regenerations_left is not None]
        avg_text_regenerations = sum(text_regenerations) / len(text_regenerations) if text_regenerations else 0

        image_regenerations = [r.image_regenerations_left for r in records if r.image_regenerations_left is not None]
        avg_image_regenerations = sum(image_regenerations) / len(image_regenerations) if image_regenerations else 0

        infographics = [r.infographics_generated_left for r in records if r.infographics_generated_left is not None]
        avg_infographics = sum(infographics) / len(infographics) if infographics else 0

        slide_changes = [r.slide_changes_left for r in records if r.slide_changes_left is not None]
        avg_slide_changes = sum(slide_changes) / len(slide_changes) if slide_changes else 0

        user_presentations = [r.user_presentations_count for r in records if r.user_presentations_count is not None]
        avg_user_presentations = sum(user_presentations) / len(user_presentations) if user_presentations else 0

        downloads = [r.download_count for r in records if r.download_count is not None]
        download_rate = sum(downloads) / len(downloads) if downloads else 0

        errors = [r for r in records if r.generation_error and r.generation_error != ""]
        error_rate = len(errors) / total if total > 0 else 0

        return Statistics(
            likes=likes,
            neutral=neutral,
            dislikes=dislikes,
            likes_percent=round((likes / total) * 100, 1) if total > 0 else 0.0,
            neutral_percent=round((neutral / total) * 100, 1) if total > 0 else 0.0,
            dislikes_percent=round((dislikes / total) * 100, 1) if total > 0 else 0.0,
            total=total,
            presentations_count=unique_presentations,
            avg_symbols=int(round(avg_symbols, 0)),
            avg_text_regenerations=int(round(avg_text_regenerations, 0)),
            avg_image_regenerations=int(round(avg_image_regenerations, 0)),
            avg_infographics=int(round(avg_infographics, 0)),
            avg_slide_changes=int(round(avg_slide_changes, 0)),
            avg_user_presentations=int(round(avg_user_presentations, 0)),
            download_rate=round(download_rate, 1),
            error_rate=round(error_rate * 100, 1),
        )


# =============================================================================
# EXPORT STRATEGIES
# =============================================================================

class ExcelExportStrategy:
    """Strategy for exporting data to Excel format."""
    
    def export(self, feedback_records: List[FeedbackRecord], stats: Statistics, 
               start_date: date, end_date: Optional[date] = None) -> ExportResult:
        """Export data to Excel file."""
        try:
            # Create DataFrame for detailed data
            data_rows = []
            for record in feedback_records:
                if record.comment:
                    created_info = (
                        f" ({record.created_at.strftime('%d.%m.%Y')})"
                        if record.created_at
                        else ""
                    )
                    
                    data_rows.append({
                        "Тема презентации": record.presentation_name or "Неизвестно",
                        "ID презентации": record.presentation_id,
                        "Оценка": {
                            "like": "ЛАЙК",
                            "dislike": "ДИЗЛАЙК",
                            "neutral": "НЕЙТРАЛЬНО",
                        }.get(record.rating.value, "НЕИЗВЕСТНО"),
                        "Комментарий": f"{record.comment}{created_info}",
                        "Использование регенераций": f"Регенераций текста: {record.text_regenerations_left or 0}, Регенераций изображений: {record.image_regenerations_left or 0}, Регенераций инфографика: {record.infographics_generated_left or 0}, Регенераций слайдов: {record.slide_changes_left or 0}, Скачиваний: {record.download_count or 0}",
                        "Язык презентации": f"Язык: {record.lang or 'N/A'}",
                        "Стиль изображений и количество слайдов": f"Стиль изображений: {record.image_style_type or 'N/A'}, Слайдов: {record.slides_count or 'N/A'}",
                        "Настройки презентации": f"Аудитория: {record.audience or 'N/A'}, Текст: {record.text_change or 'N/A'}/{record.text_amount or 'N/A'}/{record.text_tone or 'N/A'}, Источник: {record.presentation_source or 'N/A'}, Тема: {record.theme or 'N/A'}"
                    })
            
            df = pd.DataFrame(data_rows)
            
            # Generate filename
            if end_date is None or start_date == end_date:
                filename = f"feedback_export_{start_date.strftime('%Y%m%d')}.xlsx"
            else:
                filename = f"feedback_export_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
            
            filepath = ExportConfig.OUTPUT_DIR / filename
            
            # Write to Excel with multiple sheets
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Statistics sheet
                stats_data = {
                    "Метрика": ["Лайки", "Нейтрально", "Дизлайки", "Всего", "Презентаций"],
                    "Количество": [stats.likes, stats.neutral, stats.dislikes, stats.total, stats.presentations_count],
                    "Процент": [f"{stats.likes_percent:.1f}%", f"{stats.neutral_percent:.1f}%", f"{stats.dislikes_percent:.1f}%", "", ""]
                }
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, sheet_name='Статистика', index=False)
                
                # Detailed data sheet
                if not df.empty:
                    df.to_excel(writer, sheet_name='Детальные данные', index=False)
            
            logger.info(f"Excel export completed: {filepath}")
            return ExportResult(
                success=True,
                message="Excel export completed successfully",
                excel_file=str(filepath),
                sheets_updated=False,
                records_count=len(feedback_records),
                statistics=stats,
                presentations_count=stats.presentations_count
            )
            
        except Exception as e:
            logger.error(f"Excel export failed: {e}")
            return ExportResult(
                success=False,
                message=f"Excel export failed: {e}",
                excel_file=None,
                sheets_updated=False,
                records_count=0,
                statistics=None,
                presentations_count=0
            )


class GoogleSheetsExportStrategy:
    """Strategy for exporting data to Google Sheets."""
    
    def __init__(self):
        self.sheets_service = None
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Authenticate with Google Sheets API."""
        creds = None
        if ExportConfig.TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(
                str(ExportConfig.TOKEN_FILE), ExportConfig.SCOPES
            )
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not ExportConfig.CREDENTIALS_FILE.exists():
                    raise FileNotFoundError(f"Credentials file '{ExportConfig.CREDENTIALS_FILE}' not found")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(ExportConfig.CREDENTIALS_FILE), ExportConfig.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            with open(ExportConfig.TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        
        self.sheets_service = build('sheets', 'v4', credentials=creds)
        logger.info("Google Sheets authentication successful")
    
    def export(self, feedback_records: List[FeedbackRecord], stats: Statistics, 
               start_date: date, end_date: Optional[date] = None) -> ExportResult:
        """Export data to Google Sheets."""
        try:
            # Create sheet name
            if end_date is None or start_date == end_date:
                sheet_name = start_date.strftime("%d.%m.%Y")
            else:
                sheet_name = f"{start_date.strftime('%d.%m.%Y')}-{end_date.strftime('%d.%m.%Y')}"
            
            sheet_id = self._create_or_get_sheet(sheet_name)
            
            # Prepare data
            stats_data = self._prepare_statistics_data(sheet_name, stats)
            detailed_data = self._prepare_detailed_data(feedback_records)
            
            # Update sheets
            self._update_sheets_data(sheet_name, stats_data, detailed_data)
            
            # Apply formatting
            self._apply_formatting(sheet_id, stats, len(detailed_data))
            
            logger.info(f"Google Sheets export completed for {sheet_name}")
            return ExportResult(
                success=True,
                message="Google Sheets export completed successfully",
                excel_file=None,
                sheets_updated=True,
                records_count=len(feedback_records),
                statistics=stats,
                presentations_count=stats.presentations_count
            )
            
        except Exception as e:
            logger.error(f"Google Sheets export failed: {e}")
            return ExportResult(
                success=False,
                message=f"Google Sheets export failed: {e}",
                excel_file=None,
                sheets_updated=False,
                records_count=0,
                statistics=None,
                presentations_count=0
            )
    
    def _create_or_get_sheet(self, sheet_name: str) -> int:
        """Create or get existing sheet."""
        try:
            # Try to get existing sheet
            result = self.sheets_service.spreadsheets().get(
                spreadsheetId=ExportConfig.SPREADSHEET_ID
            ).execute()
            
            existing_sheets = result.get('sheets', [])
            for sheet in existing_sheets:
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            
            # Create new sheet
            request = {
                'addSheet': {
                    'properties': {
                        'title': sheet_name
                    }
                }
            }
            
            result = self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=ExportConfig.SPREADSHEET_ID,
                body={'requests': [request]}
            ).execute()
            
            return result['replies'][0]['addSheet']['properties']['sheetId']
            
        except Exception as e:
            logger.error(f"Failed to create/get sheet: {e}")
            raise
    
    def _prepare_statistics_data(self, sheet_name: str, stats: Statistics) -> List[List]:
        """Prepare statistics data for sheets."""
        return [
            [f"Статистика - {sheet_name}"],
            ["Лайки", "Нейтрально", "Дизлайки"],
            [stats.likes, stats.neutral, stats.dislikes],
            [f"{stats.likes_percent}%", f"{stats.neutral_percent}%", f"{stats.dislikes_percent}%"],
            [f"Всего: {stats.total} | Презентаций: {stats.presentations_count}"],
            [f"Ср. символов: {stats.avg_symbols} | Текст: {stats.avg_text_regenerations} | Изображения: {stats.avg_image_regenerations} | Инфографика: {stats.avg_infographics} | Слайды: {stats.avg_slide_changes} | Скачиваний: {stats.download_rate}"]
        ]
    
    def _prepare_detailed_data(self, feedback_records: List[FeedbackRecord]) -> List[List]:
        """Prepare detailed data for sheets."""
        headers = [
            "Тема презентации", "ID презентации", "Оценка", "Комментарий",
            "Использование регенераций", "Язык презентации", 
            "Стиль изображений и количество слайдов", "Настройки презентации"
        ]
        
        data = [headers]
        
        for record in feedback_records:
            if record.comment:
                created_info = (
                    f" ({record.created_at.strftime('%d.%m.%Y')})"
                    if record.created_at
                    else ""
                )
                
                data.append([
                    record.presentation_name or "Неизвестно",
                    record.presentation_id,
                    {
                        "like": "ЛАЙК",
                        "dislike": "ДИЗЛАЙК",
                        "neutral": "НЕЙТРАЛЬНО",
                    }.get(record.rating.value, "НЕИЗВЕСТНО"),
                    f"{record.comment}{created_info}",
                    f"Регенераций текста: {record.text_regenerations_left or 0}, Регенераций изображений: {record.image_regenerations_left or 0}, Регенераций инфографика: {record.infographics_generated_left or 0}, Регенераций слайдов: {record.slide_changes_left or 0}, Скачиваний: {record.download_count or 0}",
                    f"Язык: {record.lang or 'N/A'}",
                    f"Стиль изображений: {record.image_style_type or 'N/A'}, Слайдов: {record.slides_count or 'N/A'}",
                    f"Аудитория: {record.audience or 'N/A'}, Текст: {record.text_change or 'N/A'}/{record.text_amount or 'N/A'}/{record.text_tone or 'N/A'}, Источник: {record.presentation_source or 'N/A'}, Тема: {record.theme or 'N/A'}"
                ])
        
        return data
    
    def _update_sheets_data(self, sheet_name: str, stats_data: List[List], detailed_data: List[List]) -> None:
        """Update sheets with data."""
        # Update statistics
        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=ExportConfig.SPREADSHEET_ID,
            range=f"{sheet_name}!A1:C6",
            valueInputOption="RAW",
            body={"values": stats_data}
        ).execute()
        
        # Update detailed data
        if len(detailed_data) > 1:
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=ExportConfig.SPREADSHEET_ID,
                range=f"{sheet_name}!D1:K{len(detailed_data)}",
                valueInputOption="RAW",
                body={"values": detailed_data}
            ).execute()
    
    def _apply_formatting(self, sheet_id: int, stats: Statistics, data_count: int) -> None:
        """Apply formatting to the sheet."""
        requests = self._build_formatting_requests(sheet_id, stats, data_count)
        
        if requests:
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=ExportConfig.SPREADSHEET_ID,
                body={"requests": requests}
            ).execute()
    
    def _build_formatting_requests(self, sheet_id: int, stats: Statistics, data_count: int) -> List[Dict]:
        """Build formatting requests."""
        requests = []
        
        # Column width requests
        for col, width in ExportConfig.COLUMN_WIDTHS.items():
            col_index = ord(col) - ord('A')
            requests.append({
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
            })
        
        # Statistics section formatting
        requests.extend([
            # Merge A1:C1 for title
            {
                "mergeCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 3,
                    },
                    "mergeType": "MERGE_ALL",
                }
            },
            # Merge A5:C5 for summary stats
            {
                "mergeCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 4,
                        "endRowIndex": 5,
                        "startColumnIndex": 0,
                        "endColumnIndex": 3,
                    },
                    "mergeType": "MERGE_ALL",
                }
            },
            # Merge A6:C6 for performance metrics
            {
                "mergeCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 5,
                        "endRowIndex": 6,
                        "startColumnIndex": 0,
                        "endColumnIndex": 3,
                    },
                    "mergeType": "MERGE_ALL",
                }
            },
            # Format title
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 3,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {
                                "bold": True,
                                "fontSize": 14,
                                "fontFamily": ExportConfig.FONT_FAMILY,
                            },
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE",
                            "wrapStrategy": "WRAP",
                        }
                    },
                    "fields": "userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment,userEnteredFormat.wrapStrategy",
                }
            },
            # Format statistics headers (A2:C2) with Open Sans, center alignment, vertical center, and text wrapping
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": 2,
                        "startColumnIndex": 0,
                        "endColumnIndex": 3,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {
                                "bold": True,
                                "fontSize": 12,
                                "fontFamily": ExportConfig.FONT_FAMILY,
                            },
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE",
                            "wrapStrategy": "WRAP",
                        }
                    },
                    "fields": "userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment,userEnteredFormat.wrapStrategy",
                }
            },
            # Format statistics values (A3:C6) with Open Sans, center alignment, vertical center, and text wrapping
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 2,
                        "endRowIndex": 6,
                        "startColumnIndex": 0,
                        "endColumnIndex": 3,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {"fontSize": 11, "fontFamily": ExportConfig.FONT_FAMILY},
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE",
                            "wrapStrategy": "WRAP",
                        }
                    },
                    "fields": "userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment,userEnteredFormat.wrapStrategy",
                }
            },
            # Format Likes column (green)
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": 4,
                        "startColumnIndex": 0,
                        "endColumnIndex": 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.7, "green": 0.9, "blue": 0.7}
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor",
                }
            },
            # Format Neutral column (white)
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": 4,
                        "startColumnIndex": 1,
                        "endColumnIndex": 2,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor",
                }
            },
            # Format Dislikes column (red)
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": 4,
                        "startColumnIndex": 2,
                        "endColumnIndex": 3,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.9, "green": 0.7, "blue": 0.7}
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor",
                }
            },
            # Add borders to statistics section
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 9,
                        "startColumnIndex": 0,
                        "endColumnIndex": 3,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "borders": {
                                "top": {"style": "SOLID", "color": ExportConfig.BORDER_COLOR},
                                "bottom": {"style": "SOLID", "color": ExportConfig.BORDER_COLOR},
                                "left": {"style": "SOLID", "color": ExportConfig.BORDER_COLOR},
                                "right": {"style": "SOLID", "color": ExportConfig.BORDER_COLOR},
                            }
                        }
                    },
                    "fields": "userEnteredFormat.borders",
                }
            }
        ])
        
        # Add borders to detailed data section
        if data_count > 1:
            requests.extend([
                # Format detailed data headers (D1:K1) with Open Sans
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 3,
                            "endColumnIndex": 11,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "textFormat": {
                                    "bold": True,
                                    "fontSize": 12,
                                    "fontFamily": ExportConfig.FONT_FAMILY,
                                },
                                "horizontalAlignment": "CENTER",
                                "verticalAlignment": "MIDDLE",
                                "wrapStrategy": "WRAP",
                            }
                        },
                        "fields": "userEnteredFormat.textFormat,userEnteredFormat.horizontalAlignment,userEnteredFormat.verticalAlignment,userEnteredFormat.wrapStrategy",
                    }
                },
                # Format detailed data content (D2:K*) with Open Sans
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": data_count,
                            "startColumnIndex": 3,
                            "endColumnIndex": 11,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "textFormat": {"fontSize": 10, "fontFamily": ExportConfig.FONT_FAMILY},
                                "verticalAlignment": "TOP",
                                "wrapStrategy": "WRAP",
                            }
                        },
                        "fields": "userEnteredFormat.textFormat,userEnteredFormat.verticalAlignment,userEnteredFormat.wrapStrategy",
                    }
                },
                # Add borders to detailed data section
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": data_count,
                            "startColumnIndex": 3,
                            "endColumnIndex": 11,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "borders": {
                                    "top": {"style": "SOLID", "color": ExportConfig.BORDER_COLOR},
                                    "bottom": {"style": "SOLID", "color": ExportConfig.BORDER_COLOR},
                                    "left": {"style": "SOLID", "color": ExportConfig.BORDER_COLOR},
                                    "right": {"style": "SOLID", "color": ExportConfig.BORDER_COLOR},
                                }
                            }
                        },
                        "fields": "userEnteredFormat.borders",
                    }
                }
            ])
        
        return requests


# =============================================================================
# MAIN ORCHESTRATOR CLASS
# =============================================================================

class FeedbackExporter:
    """Main orchestrator class for feedback export operations."""
    
    def __init__(self, db_service: DatabaseService, data_processor: DataProcessor):
        self.db_service = db_service
        self.data_processor = data_processor
        self.export_strategies: Dict[str, ExportStrategy] = {}
    
    def add_export_strategy(self, name: str, strategy: ExportStrategy) -> None:
        """Add an export strategy."""
        self.export_strategies[name] = strategy
    
    def run_export(self, start_date: date, end_date: Optional[date] = None, 
                   strategies: Optional[List[str]] = None) -> Dict[str, ExportResult]:
        """Run export using specified strategies."""
        try:
            # Connect to database
            self.db_service.connect()
            
            # Fetch data
            raw_records = self.db_service.fetch_feedback_data(start_date, end_date)
            
            if not raw_records:
                date_range_str = (
                    f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
                    if end_date and start_date != end_date
                    else start_date.strftime("%d.%m.%Y")
                )
                logger.warning(f"No feedback records found for {date_range_str}")
                return {}
            
            # Process data
            processed_records = self.data_processor.process_records(raw_records)
            stats = self.data_processor.calculate_statistics(raw_records)
            
            # Run exports
            results = {}
            strategies_to_run = strategies or list(self.export_strategies.keys())
            
            for strategy_name in strategies_to_run:
                if strategy_name in self.export_strategies:
                    logger.info(f"Running {strategy_name} export...")
                    result = self.export_strategies[strategy_name].export(
                        processed_records, stats, start_date, end_date
                    )
                    results[strategy_name] = result
                else:
                    logger.warning(f"Strategy '{strategy_name}' not found")
            
            return results
            
        except Exception as e:
            logger.error(f"Export operation failed: {e}")
            raise
        finally:
            self.db_service.disconnect()


# =============================================================================
# FACTORY AND APPLICATION CLASSES
# =============================================================================

class FeedbackExportFactory:
    """Factory for creating feedback export components."""
    
    @staticmethod
    def create_database_service(config: Dict[str, Union[str, int]]) -> DatabaseService:
        """Create database service instance."""
        return DatabaseServiceImpl(
            host=config["host"],
            database=config["database"],
            user=config["user"],
            password=config["password"],
            port=config["port"]
        )
    
    @staticmethod
    def create_data_processor() -> DataProcessor:
        """Create data processor instance."""
        return DataProcessorImpl()
    
    @staticmethod
    def create_excel_strategy() -> ExportStrategy:
        """Create Excel export strategy."""
        return ExcelExportStrategy()
    
    @staticmethod
    def create_sheets_strategy() -> ExportStrategy:
        """Create Google Sheets export strategy."""
        return GoogleSheetsExportStrategy()
    
    @staticmethod
    def create_exporter(db_service: DatabaseService, data_processor: DataProcessor) -> FeedbackExporter:
        """Create main exporter with all strategies."""
        exporter = FeedbackExporter(db_service, data_processor)
        
        # Add default strategies
        exporter.add_export_strategy("excel", FeedbackExportFactory.create_excel_strategy())
        exporter.add_export_strategy("sheets", FeedbackExportFactory.create_sheets_strategy())
        
        return exporter


class FeedbackExportApplication:
    """Main application class for feedback export."""
    
    def __init__(self):
        self.config = self._load_config()
        self.factory = FeedbackExportFactory()
    
    def _load_config(self) -> Dict[str, Union[str, int]]:
        """Load database configuration."""
        config = configparser.ConfigParser()
        config.read("../database.ini")

        if "postgresql" not in config:
            raise ValueError("No [postgresql] section found in database.ini")

        return {
            "host": config["postgresql"]["host"],
            "database": config["postgresql"]["database"],
            "user": config["postgresql"]["user"],
            "password": config["postgresql"]["password"],
            "port": int(config["postgresql"]["port"]),
        }
    
    def _get_date_range(self) -> tuple[date, Optional[date]]:
        """Get date range from user input."""
        start_date_str = input("Enter start date (DD.MM.YYYY): ")
        start_date = datetime.strptime(start_date_str, "%d.%m.%Y").date()

        end_date_str = input("Enter end date (DD.MM.YYYY) or press Enter for single day: ")
        end_date = None
        if end_date_str.strip():
            end_date = datetime.strptime(end_date_str, "%d.%m.%Y").date()

        return start_date, end_date
    
    def _get_user_confirmation(self, start_date: date, end_date: Optional[date] = None) -> bool:
        """Get user confirmation for export operation."""
        if end_date is None or start_date == end_date:
            date_str = start_date.strftime("%d.%m.%Y")
        else:
            date_str = f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"

        print(f"\nExporting feedback for period: {date_str}")
        print("=" * 50)
        response = input("Continue? (y/n): ").lower().strip()
        return response in ["y", "yes"]
    
    def _get_export_strategies(self) -> List[str]:
        """Get export strategies from user."""
        print("\nAvailable export formats:")
        print("1. Excel (excel)")
        print("2. Google Sheets (sheets)")
        print("3. All formats (all)")
        
        choice = input("Select export format (1/2/3): ").strip()
        
        if choice == "1":
            return ["excel"]
        elif choice == "2":
            return ["sheets"]
        elif choice == "3":
            return ["excel", "sheets"]
        else:
            print("Invalid choice. Using all formats.")
            return ["excel", "sheets"]
    
    def run(self) -> None:
        """Run the feedback export application."""
        try:
            # Get date range
            start_date, end_date = self._get_date_range()
            
            # Get user confirmation
            if not self._get_user_confirmation(start_date, end_date):
                print("Operation cancelled.")
                return
            
            # Get export strategies
            strategies = self._get_export_strategies()
            
            # Create components
            db_service = self.factory.create_database_service(self.config)
            data_processor = self.factory.create_data_processor()
            exporter = self.factory.create_exporter(db_service, data_processor)
            
            # Run export
            results = exporter.run_export(start_date, end_date, strategies)
            
            # Display results
            self._display_results(results)
            
        except Exception as e:
            print(f"Error: {e}")
            logger.error(f"Application error: {e}")
    
    def _display_results(self, results: Dict[str, ExportResult]) -> None:
        """Display export results."""
        print(f"\nExport Results:")
        print("=" * 50)
        
        for strategy_name, result in results.items():
            print(f"\n{strategy_name.upper()}:")
            if result.success:
                print(f"  Status: Success")
                print(f"  Records: {result.records_count}")
                print(f"  Presentations: {result.presentations_count}")
                if result.excel_file:
                    print(f"  File: {result.excel_file}")
                if result.sheets_updated:
                    print(f"  Google Sheets updated")
            else:
                print(f"  Status: Error - {result.message}")


def main():
    """Main function to run the feedback export application."""
    app = FeedbackExportApplication()
    app.run()


if __name__ == "__main__":
    main()