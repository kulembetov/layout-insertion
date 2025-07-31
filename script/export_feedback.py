#!/usr/bin/env python3
"""
Script to export PresentationFeedback data to Google Sheets with daily statistics and comments.
"""

import os
import sys
import logging
import configparser
from datetime import datetime, date
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from enum import Enum

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
os.makedirs("feedback_reports", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("feedback_reports/feedback_export.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Suppress oauth2client file_cache warning
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

# Configuration
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDENTIALS_FILE = "../credentials.json"
TOKEN_FILE = "../token.json"
SPREADSHEET_ID = "1GGUznHFHmsjfH2bqCvEsbBm8rQWalcRa8dD7EQwq-KI"


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


class FeedbackExporter:
    """Main class to handle the feedback export process."""

    def __init__(self, host: str, database: str, user: str, password: str, port: int):
        self.db_config = {
            "host": host,
            "database": database,
            "user": user,
            "password": password,
            "port": port,
        }
        self.connection = Optional[psycopg2.extensions.connection]
        self.sheets_service = Optional[build]

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

    def fetch_feedback_data(
        self, start_date: date, end_date: Optional[date] = None
    ) -> List[FeedbackRecord]:
        """Fetch PresentationFeedback records for a specific date or date range."""
        if not self.connection:
            raise RuntimeError("Database connection not established")

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
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (start_date, end_date))
                rows = cursor.fetchall()

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
                            infographics_generated_left=row[
                                "infographics_generated_left"
                            ],
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
                logger.info(
                    f"Fetched {len(feedback_records)} feedback records for {date_range_str}"
                )
                return feedback_records

        except psycopg2.Error as e:
            logger.error(f"Failed to fetch feedback records: {e}")
            raise

    def calculate_statistics(
        self, feedback_records: List[FeedbackRecord]
    ) -> Statistics:
        """Calculate statistics for the feedback data."""
        if not feedback_records:
            return Statistics(
                likes=0,
                neutral=0,
                dislikes=0,
                likes_percent=0.0,
                neutral_percent=0.0,
                dislikes_percent=0.0,
                total=0,
                presentations_count=0,
                avg_symbols=0,
                avg_text_regenerations=0,
                avg_image_regenerations=0,
                avg_infographics=0,
                avg_slide_changes=0,
                avg_user_presentations=0,
                download_rate=0.0,
                error_rate=0.0,
            )

        total = len(feedback_records)
        likes = sum(
            1 for record in feedback_records if record.rating == PresentationRating.LIKE
        )
        neutral = sum(
            1
            for record in feedback_records
            if record.rating == PresentationRating.NEUTRAL
        )
        dislikes = sum(
            1
            for record in feedback_records
            if record.rating == PresentationRating.DISLIKE
        )

        # Count unique presentations
        unique_presentations = len(
            set(record.presentation_id for record in feedback_records)
        )

        # Calculate additional metrics
        symbols_used = [
            r.symbols_used for r in feedback_records if r.symbols_used is not None
        ]
        avg_symbols = sum(symbols_used) / len(symbols_used) if symbols_used else 0

        text_regenerations = [
            r.text_regenerations_left
            for r in feedback_records
            if r.text_regenerations_left is not None
        ]
        avg_text_regenerations = (
            sum(text_regenerations) / len(text_regenerations)
            if text_regenerations
            else 0
        )

        image_regenerations = [
            r.image_regenerations_left
            for r in feedback_records
            if r.image_regenerations_left is not None
        ]
        avg_image_regenerations = (
            sum(image_regenerations) / len(image_regenerations)
            if image_regenerations
            else 0
        )

        infographics = [
            r.infographics_generated_left
            for r in feedback_records
            if r.infographics_generated_left is not None
        ]
        avg_infographics = sum(infographics) / len(infographics) if infographics else 0

        slide_changes = [
            r.slide_changes_left
            for r in feedback_records
            if r.slide_changes_left is not None
        ]
        avg_slide_changes = (
            sum(slide_changes) / len(slide_changes) if slide_changes else 0
        )

        user_presentations = [
            r.user_presentations_count
            for r in feedback_records
            if r.user_presentations_count is not None
        ]
        avg_user_presentations = (
            sum(user_presentations) / len(user_presentations)
            if user_presentations
            else 0
        )

        downloads = [
            r.download_count for r in feedback_records if r.download_count is not None
        ]
        download_rate = sum(downloads) / len(downloads) if downloads else 0

        errors = [
            r
            for r in feedback_records
            if r.generation_error and r.generation_error != ""
        ]
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

    def authenticate_sheets(self) -> None:
        """Authenticate with Google Sheets API."""
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"Credentials file '{CREDENTIALS_FILE}' not found"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())

        self.sheets_service = build("sheets", "v4", credentials=creds)
        logger.info("Google Sheets API authenticated")

    def create_or_get_sheet(self, sheet_name: str) -> int:
        """Create a new sheet or get existing sheet ID."""
        try:
            # Get spreadsheet info
            result = (
                self.sheets_service.spreadsheets()
                .get(spreadsheetId=SPREADSHEET_ID)
                .execute()
            )

            # Check if sheet exists
            for sheet in result.get("sheets", []):
                if sheet["properties"]["title"] == sheet_name:
                    return sheet["properties"]["sheetId"]

            # Create new sheet
            requests = [{"addSheet": {"properties": {"title": sheet_name}}}]

            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID, body={"requests": requests}
            ).execute()

            # Get the new sheet ID
            result = (
                self.sheets_service.spreadsheets()
                .get(spreadsheetId=SPREADSHEET_ID)
                .execute()
            )

            for sheet in result.get("sheets", []):
                if sheet["properties"]["title"] == sheet_name:
                    return sheet["properties"]["sheetId"]

            raise ValueError(f"Failed to create sheet '{sheet_name}'")

        except HttpError as error:
            logger.error(f"Failed to create/get sheet: {error}")
            raise

    def export_to_excel(
        self,
        feedback_records: List[FeedbackRecord],
        stats: Statistics,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> str:
        """Export feedback data to Excel file."""
        # Create filename based on date range
        if end_date is None or start_date == end_date:
            filename = f"feedback_report_{start_date.strftime('%Y%m%d')}.xlsx"
        else:
            filename = f"feedback_report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"

        filepath = f"feedback_reports/{filename}"

        # Remove existing file if it exists
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Removed existing file: {filepath}")

        data = [
            {
                "ID": record.id,
                "Rating": record.rating.value,
                "Comment": record.comment or "",
                "Presentation ID": record.presentation_id,
                "Presentation Name": record.presentation_name or "Unknown",
                "Created At": (
                    record.created_at.strftime("%d.%m.%Y %H:%M:%S")
                    if record.created_at
                    else "N/A"
                ),
                "Theme": record.theme or "N/A",
                "Language": record.lang or "N/A",
                "Presentation Source": record.presentation_source or "N/A",
                "Text Amount": record.text_amount or "N/A",
                "Text Tone": record.text_tone or "N/A",
                "Audience": record.audience or "N/A",
                "Text Change": record.text_change or "N/A",
            }
            for record in feedback_records
        ]

        df = pd.DataFrame(data)

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Feedback Data", index=False)

            # Create statistics sheet
            stats_df = pd.DataFrame(
                [
                    {
                        "Metric": "Likes",
                        "Count": stats.likes,
                        "Percentage": f"{stats.likes_percent}%",
                    },
                    {
                        "Metric": "Neutral",
                        "Count": stats.neutral,
                        "Percentage": f"{stats.neutral_percent}%",
                    },
                    {
                        "Metric": "Dislikes",
                        "Count": stats.dislikes,
                        "Percentage": f"{stats.dislikes_percent}%",
                    },
                    {"Metric": "Total", "Count": stats.total, "Percentage": "100%"},
                ]
            )

            stats_df.to_excel(writer, sheet_name="Statistics", index=False)

        logger.info(
            f"Exported {len(feedback_records)} feedback records to Excel: {filepath}"
        )
        return filepath

    def update_sheets(
        self,
        feedback_records: List[FeedbackRecord],
        stats: Statistics,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> None:
        """Update Google Sheets with feedback data and statistics."""
        try:
            # Create sheet name based on date range
            if end_date is None or start_date == end_date:
                sheet_name = start_date.strftime("%d.%m.%Y")
            else:
                sheet_name = (
                    f"{start_date.strftime('%d.%m.%Y')}-{end_date.strftime('%d.%m.%Y')}"
                )

            sheet_id = self.create_or_get_sheet(sheet_name)

            # Prepare data for enhanced statistics section (A1:C6)
            stats_data = [
                [f"Статистика - {sheet_name}"],  # A1 (merged)
                ["Лайки", "Нейтрально", "Дизлайки"],  # A2:C2
                [stats.likes, stats.neutral, stats.dislikes],  # A3:C3
                [
                    f"{stats.likes_percent}%",
                    f"{stats.neutral_percent}%",
                    f"{stats.dislikes_percent}%",
                ],  # A4:C4
                [
                    f"Всего: {stats.total} | Презентаций: {stats.presentations_count}"
                ],  # A5 (merged)
                [
                    f"Ср. символов: {stats.avg_symbols} | Текст: {stats.avg_text_regenerations} | Изображения: {stats.avg_image_regenerations} | Инфографика: {stats.avg_infographics} | Слайды: {stats.avg_slide_changes} | Скачиваний: {stats.download_rate}"
                ],  # A6 (merged)
            ]

            # Prepare comments data (D column)
            comments_data = [["Детальные отзывы"]]  # D1

            # Add each comment once
            for record in feedback_records:
                if record.comment:
                    created_info = (
                        f" ({record.created_at.strftime('%d.%m.%Y')})"
                        if record.created_at
                        else ""
                    )

                    # Enhanced settings info with user context and performance metrics
                    user_info = f"Количество презентаций: {record.user_presentations_count or 0} презентаций, Роль: {record.user_role or 'N/A'}, Пользователь: {record.user_contact or 'N/A'}"
                    performance_info = f"Потрачено символов: {record.symbols_used or 0}, Статус: {record.presentation_status or 'N/A'}"
                    usage_info = f"Регенераций текста: {record.text_regenerations_left or 0}, Регенераций изображений: {record.image_regenerations_left or 0}, Регенераций инфографика: {record.infographics_generated_left or 0}, Регенераций слайдов: {record.slide_changes_left or 0}, Скачиваний: {record.download_count or 0}"

                    settings_info = (
                        f" | {user_info} | {performance_info} | {usage_info}"
                    )
                    settings_info += f" | Тема: {record.theme or 'N/A'}, Язык: {record.lang or 'N/A'}, Источник: {record.presentation_source or 'N/A'}"
                    settings_info += f" | Цвет: {record.color or 'N/A'}, Веб-поиск: {'Да' if record.use_web_search else 'Нет'}"
                    settings_info += f" | Стиль изображений: {record.image_style_type or 'N/A'}, Слайдов: {record.slides_count or 'N/A'}"
                    settings_info += f" | Аудитория: {record.audience or 'N/A'}, Текст: {record.text_change or 'N/A'}/{record.text_amount or 'N/A'}/{record.text_tone or 'N/A'}"

                    rating_text = {
                        "like": "[ЛАЙК]",
                        "dislike": "[ДИЗЛАЙК]",
                        "neutral": "[НЕЙТРАЛЬНО]",
                    }.get(record.rating.value, "[НЕИЗВЕСТНО]")
                    comment_text = f"[{record.presentation_name or 'Неизвестно'} | ID презентации: {record.presentation_id} {rating_text} {record.comment}{created_info}{settings_info}"
                    comments_data.append([comment_text])

            # Update statistics section
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{sheet_name}!A1:C6",
                valueInputOption="RAW",
                body={"values": stats_data},
            ).execute()

            # Update comments section
            if comments_data:
                self.sheets_service.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=f"{sheet_name}!D1:D{len(comments_data)}",
                    valueInputOption="RAW",
                    body={"values": comments_data},
                ).execute()

            # Apply formatting
            self._apply_formatting(sheet_id, stats)

            logger.info(f"Updated Google Sheets with feedback data for {sheet_name}")

        except HttpError as error:
            logger.error(f"Failed to update Google Sheets: {error}")
            raise

    def _apply_formatting(self, sheet_id: int, stats: Statistics) -> None:
        """Apply formatting to the sheet with Open Sans font."""
        requests = [
            # Set column widths for better readability
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": 1,
                    },
                    "properties": {"pixelSize": 230},  # Column A width
                    "fields": "pixelSize",
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 1,
                        "endIndex": 2,
                    },
                    "properties": {"pixelSize": 230},  # Column B width
                    "fields": "pixelSize",
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 2,
                        "endIndex": 3,
                    },
                    "properties": {"pixelSize": 230},  # Column C width
                    "fields": "pixelSize",
                }
            },
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 3,
                        "endIndex": 4,
                    },
                    "properties": {"pixelSize": 600},  # Column D width for comments
                    "fields": "pixelSize",
                }
            },
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
            # Format title with Open Sans, center alignment, vertical center, and text wrapping
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
                                "fontFamily": "Open Sans",
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
                                "fontFamily": "Open Sans",
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
                            "textFormat": {"fontSize": 11, "fontFamily": "Open Sans"},
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
            # Format comments header (D1) with Open Sans
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 3,
                        "endColumnIndex": 4,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {
                                "bold": True,
                                "fontSize": 14,
                                "fontFamily": "Open Sans",
                            }
                        }
                    },
                    "fields": "userEnteredFormat.textFormat",
                }
            },
            # Format comments content (D2:D*) with Open Sans
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "startColumnIndex": 3,
                        "endColumnIndex": 4,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {"fontSize": 11, "fontFamily": "Open Sans"},
                            "verticalAlignment": "TOP",
                            "wrapStrategy": "WRAP",
                        }
                    },
                    "fields": "userEnteredFormat.textFormat,userEnteredFormat.verticalAlignment,userEnteredFormat.wrapStrategy",
                }
            },
            # Add borders to all cells (A1:D*)
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "startColumnIndex": 0,
                        "endColumnIndex": 4,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "borders": {
                                "top": {
                                    "style": "SOLID",
                                    "color": {"red": 0.8, "green": 0.8, "blue": 0.8},
                                },
                                "bottom": {
                                    "style": "SOLID",
                                    "color": {"red": 0.8, "green": 0.8, "blue": 0.8},
                                },
                                "left": {
                                    "style": "SOLID",
                                    "color": {"red": 0.8, "green": 0.8, "blue": 0.8},
                                },
                                "right": {
                                    "style": "SOLID",
                                    "color": {"red": 0.8, "green": 0.8, "blue": 0.8},
                                },
                            }
                        }
                    },
                    "fields": "userEnteredFormat.borders",
                }
            },
        ]

        self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID, body={"requests": requests}
        ).execute()

    def run_export(
        self, start_date: date, end_date: Optional[date] = None
    ) -> ExportResult:
        """Run the complete feedback export process."""
        try:
            self.connect_db()
            feedback_records = self.fetch_feedback_data(start_date, end_date)

            if not feedback_records:
                date_range_str = (
                    f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
                    if end_date and start_date != end_date
                    else start_date.strftime("%d.%m.%Y")
                )
                return ExportResult(
                    success=True,
                    message=f"No feedback records found for {date_range_str}",
                    excel_file=None,
                    sheets_updated=False,
                    records_count=0,
                    statistics=None,
                    presentations_count=0,
                )

            stats = self.calculate_statistics(feedback_records)
            excel_file = self.export_to_excel(
                feedback_records, stats, start_date, end_date
            )

            sheets_updated = False
            try:
                self.authenticate_sheets()
                self.update_sheets(feedback_records, stats, start_date, end_date)
                sheets_updated = True
            except Exception as e:
                logger.warning(f"Google Sheets update failed: {e}")

            return ExportResult(
                success=True,
                message="Feedback export completed successfully",
                excel_file=excel_file,
                sheets_updated=sheets_updated,
                records_count=len(feedback_records),
                statistics=stats,
                presentations_count=stats.presentations_count,
            )

        except Exception as e:
            logger.error(f"Feedback export failed: {e}")
            return ExportResult(
                success=False,
                message=str(e),
                excel_file=None,
                sheets_updated=False,
                records_count=0,
                statistics=None,
                presentations_count=0,
            )
        finally:
            self.disconnect_db()


def load_database_config() -> Dict[str, Union[str, int]]:
    """Load database configuration from database.ini file."""
    config = configparser.ConfigParser()
    if not os.path.exists("../database.ini"):
        raise FileNotFoundError("database.ini file not found")

    config.read("../database.ini")
    if "postgresql" not in config:
        raise ValueError("postgresql section not found in database.ini")

    db_config = config["postgresql"]
    return {
        "host": db_config.get("host"),
        "database": db_config.get("database"),
        "user": db_config.get("user"),
        "password": db_config.get("password"),
        "port": int(db_config.get("port", 5432)),
    }


def get_user_confirmation(start_date: date, end_date: Optional[date] = None) -> bool:
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

        if end_date and start_date != end_date:
            print(
                f"Date Range: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
            )
        else:
            print(f"Target Date: {start_date.strftime('%d.%m.%Y')}")

        print("=" * 40)
        print("\nThis script will:")
        print("1. Connect to database and fetch PresentationFeedback records")
        print("2. Calculate statistics (likes/neutral/dislikes with percentages)")
        print("3. Export data to Excel file in 'feedback_reports/' directory")
        print("4. Create/update Google Sheets with formatted statistics and comments")
        print("5. Apply color formatting (green for likes, red for dislikes)")

        response = input("\nDo you want to proceed? (y/N): ").strip().lower()
        return response in ["y", "yes"]

    except Exception as e:
        print(f"Error loading database configuration: {e}")
        return False


def main():
    """Main function to run the feedback export process."""
    load_dotenv()
    print("Presentation Feedback Export Script")
    print("=" * 40)

    # Get date range from user
    print("Enter date range for feedback export:")
    print("1. Single day (e.g., 15.07.2025)")
    print("2. Date range (e.g., 08.07-15.07.2025)")

    date_input = input("\nEnter date(s) (DD.MM.YYYY or DD.MM-DD.MM.YYYY): ").strip()

    try:
        if "-" in date_input:
            # Date range format: DD.MM-DD.MM.YYYY
            parts = date_input.split("-")
            if len(parts) != 2:
                raise ValueError("Invalid date range format. Use DD.MM-DD.MM.YYYY")

            start_part, end_part = parts
            if "." not in end_part:
                # Format: DD.MM-DD.MM.YYYY
                start_day_month, year = end_part.rsplit(".", 1)
                end_day_month = start_day_month
            else:
                # Format: DD.MM-DD.MM.YYYY
                end_day_month, year = end_part.rsplit(".", 1)

            start_date = datetime.strptime(f"{start_part}.{year}", "%d.%m.%Y").date()
            end_date = datetime.strptime(f"{end_day_month}.{year}", "%d.%m.%Y").date()
        else:
            # Single date format: DD.MM.YYYY
            start_date = datetime.strptime(date_input, "%d.%m.%Y").date()
            end_date = None

        if end_date and start_date > end_date:
            start_date, end_date = end_date, start_date

        if end_date and start_date != end_date:
            print(
                f"Date range: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
            )
        else:
            print(f"Target date: {start_date.strftime('%d.%m.%Y')}")

        if not get_user_confirmation(start_date, end_date):
            print("Export cancelled by user.")
            sys.exit(0)

        db_config = load_database_config()
        exporter = FeedbackExporter(**db_config)

        print("\nStarting feedback export process...")
        result = exporter.run_export(start_date, end_date)

        if result.success:
            print(f"\nFeedback export completed successfully!")
            print(f"Records exported: {result.records_count}")
            print(f"Presentations with feedback: {result.presentations_count}")
            if result.excel_file:
                print(f"Excel file: {result.excel_file}")
            if result.sheets_updated:
                print(
                    f"Google Sheets updated: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
                )
                if result.statistics:
                    stats = result.statistics
                    print(
                        f"Statistics: {stats.likes} likes ({stats.likes_percent}%), "
                        f"{stats.neutral} neutral ({stats.neutral_percent}%), "
                        f"{stats.dislikes} dislikes ({stats.dislikes_percent}%)"
                    )
            else:
                print("Google Sheets was not updated (authentication or access error)")
        else:
            print(f"\nExport failed: {result.message}")
            sys.exit(1)

    except ValueError as e:
        print(f"\nDate format error: {e}")
        print(
            "Please use format DD.MM.YYYY for single day or DD.MM-DD.MM.YYYY for date range"
        )
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
