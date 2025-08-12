#!/usr/bin/env python3
"""
Script to scan S3 bucket for images and generate SQL statements for ImageOption insertion
and PresentationLayoutImageOption junction table population.

Features:
- Scans Yandex Cloud S3 bucket for images
- Generates SQL INSERT statements for ImageOption table
- Generates SQL INSERT statements for PresentationLayoutImageOption junction table
- Creates combined SQL files with proper transaction handling
- Generates corresponding DELETE SQL statements for cleanup
"""

import logging
import mimetypes
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final

import boto3
import uuid_utils as uuid
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Import configuration
try:
    from config import DEFAULT_VALUES
except ImportError:
    # Fallback if config is not available
    DEFAULT_VALUES = {"presentation_layout_id": "0197c55e-1c1b-7760-9525-f51752cf23e2"}

# Load environment variables
load_dotenv()

# Configuration Constants
YANDEX_ENDPOINT_URL: Final[str] = "https://storage.yandexcloud.net"
IMAGE_EXTENSIONS: Final[set[str]] = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".svg"}
DEFAULT_IMAGE_SOURCE: Final[str] = "raiffeisen"
LOGS_DIR: Final[Path] = Path("logs")

# Global logger - will be initialized in main()
logger: logging.Logger | None = None


@dataclass(frozen=True)
class S3ImageInfo:
    """Data class for S3 image information."""

    key: str
    filename: str
    size: int
    content_type: str
    url: str
    folder_path: str


class SOURCE(Enum):
    """Image source enum."""

    RAIFFEISEN = "raiffeisen"


@dataclass(frozen=True)
class Config:
    """Configuration data class."""

    s3_prefix: str
    image_source: SOURCE
    output_file: str
    bucket_name: str
    presentation_layout_id: str

    @classmethod
    def from_env(cls) -> "Config":
        """Create config from environment variables."""
        return cls(
            s3_prefix=os.getenv("S3_PREFIX", "layouts/raiffeisen/library/"),
            image_source=SOURCE(os.getenv("IMAGE_SOURCE", DEFAULT_IMAGE_SOURCE)),
            output_file=os.getenv("OUTPUT_FILE", "insert_image_options.sql"),
            bucket_name=os.getenv("YANDEX_BUCKET_NAME", ""),
            presentation_layout_id=str(DEFAULT_VALUES.get("presentation_layout_id", "")),
        )


class LoggerSetup:
    """Handles logging configuration."""

    @staticmethod
    def setup() -> logging.Logger:
        """Setup logging to both file and console."""
        LOGS_DIR.mkdir(exist_ok=True)

        log_file = LOGS_DIR / "image_options_generation.log"

        # Configure logger
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        # Avoid duplicate handlers
        if logger.handlers:
            return logger

        # File handler
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(file_formatter)

        # Console handler (errors only)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")
        console_handler.setFormatter(console_formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger


def generate_uuid() -> str:
    """Generate a UUID7 string for database use."""
    return str(uuid.uuid7())


class S3ImageScanner:
    """Handles S3 bucket scanning for images."""

    def __init__(self, config: Config):
        self.config = config
        self.s3_client = self._setup_client()

    def _setup_client(self) -> boto3.client:
        """Setup S3 client for Yandex Cloud."""
        access_key = os.getenv("YANDEX_STATIC_KEY")
        secret_key = os.getenv("YANDEX_STATIC_SECRET")

        if not access_key or not secret_key:
            raise ValueError("Missing Yandex Cloud credentials: YANDEX_STATIC_KEY and YANDEX_STATIC_SECRET required")

        return boto3.client(
            "s3",
            endpoint_url=YANDEX_ENDPOINT_URL,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="ru-central1",
        )

    def check_bucket_access(self) -> bool:
        """Check if we can access the bucket."""
        try:
            self.s3_client.head_bucket(Bucket=self.config.bucket_name)
            if logger:
                logger.info(f"Successfully accessed bucket: {self.config.bucket_name}")
            return True
        except ClientError as error:
            if logger:
                logger.error(f"Cannot access bucket {self.config.bucket_name}: {error}")
            return False

    def _is_image_file(self, key: str) -> bool:
        """Check if file is an image based on extension."""
        return Path(key).suffix.lower() in IMAGE_EXTENSIONS

    def _extract_folder_path(self, key: str) -> str:
        """Extract folder path from S3 key."""
        path_parts = key.split("/")
        return "/".join(path_parts[:-1]) + "/" if len(path_parts) > 1 else ""

    def _build_image_url(self, key: str) -> str:
        """Build full URL for image."""
        return f"https://storage.yandexcloud.net/{self.config.bucket_name}/{key}"

    def list_images(self, prefix: str = "") -> list[S3ImageInfo]:
        """List all images in S3 bucket with optional prefix."""
        images: list[S3ImageInfo] = []
        paginator = self.s3_client.get_paginator("list_objects_v2")

        try:
            page_iterator = paginator.paginate(Bucket=self.config.bucket_name, Prefix=prefix)

            for page in page_iterator:
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    key = obj["Key"]

                    if not self._is_image_file(key):
                        continue

                    filename = Path(key).name
                    folder_path = self._extract_folder_path(key)
                    url = self._build_image_url(key)
                    content_type = mimetypes.guess_type(key)[0] or "image/jpeg"

                    images.append(
                        S3ImageInfo(
                            key=key,
                            filename=filename,
                            size=obj["Size"],
                            content_type=content_type,
                            url=url,
                            folder_path=folder_path,
                        )
                    )

            if logger:
                logger.info(f"Found {len(images)} images in bucket")
            return images

        except ClientError as error:
            if logger:
                logger.error(f"Error listing objects in bucket: {error}")
            return []


class SQLGenerator:
    """Generates SQL statements for ImageOption and PresentationLayoutImageOption insertion."""

    @staticmethod
    def _escape_sql_string(value: str) -> str:
        """Escape single quotes in SQL strings to prevent injection."""
        return value.replace("'", "''")

    @staticmethod
    def _validate_uuid(uuid_str: str) -> str:
        """Validate that the string is a valid UUID format."""
        import re

        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        if not re.match(uuid_pattern, uuid_str.lower()):
            raise ValueError(f"Invalid UUID format: {uuid_str}")
        return uuid_str

    @staticmethod
    def _validate_image_source(source: str) -> str:
        """Validate image source enum value."""
        valid_sources = [source.value for source in SOURCE]
        if source not in valid_sources:
            raise ValueError(f"Invalid image source: {source}. Must be one of {valid_sources}")
        return source

    def generate_image_option_sql(self, image_info: S3ImageInfo, source: str) -> tuple[str, str]:
        """Generate SQL statement for a single ImageOption and return both SQL and ID."""
        image_id = generate_uuid()

        # Validate and escape inputs
        validated_id = self._validate_uuid(image_id)
        validated_source = self._validate_image_source(source)
        escaped_filename = self._escape_sql_string(image_info.filename)
        escaped_url = self._escape_sql_string(image_info.url)
        escaped_key = self._escape_sql_string(image_info.key)

        sql = f"""-- ImageOption: {escaped_filename}
INSERT INTO "ImageOption" (
    "id",
    "source",
    "url",
    "downloadLocation",
    "authorName",
    "authorImage",
    "authorLink",
    "referalLink",
    "imageSourceId"
) VALUES (
    '{validated_id}',
    '{validated_source}'::"ImageSource",
    '{escaped_url}',
    '{escaped_key}',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL
);"""

        return sql, image_id

    def generate_junction_sql(self, image_option_id: str, presentation_layout_id: str) -> str:
        """Generate SQL statement for PresentationLayoutImageOption junction table."""
        # Validate UUIDs
        validated_image_id = self._validate_uuid(image_option_id)
        validated_layout_id = self._validate_uuid(presentation_layout_id)

        return f"""INSERT INTO "PresentationLayoutImageOption" (
    "imageOptionId",
    "presentationLayoutId"
) VALUES (
    '{validated_image_id}',
    '{validated_layout_id}'
);"""

    def generate_batch_sql(self, images: list[S3ImageInfo], presentation_layout_id: str, source: str) -> tuple[str, list[str]]:
        """Generate batch SQL for multiple ImageOptions and PresentationLayoutImageOption records using bulk INSERT.

        Returns:
            tuple: (sql_string, list_of_generated_image_option_ids)
        """
        if not images:
            return "", []

        sql_parts = ["-- Batch insert ImageOptions and PresentationLayoutImageOption records", "BEGIN;", "", "-- ImageOption bulk INSERT statement"]

        # Generate all ImageOption VALUES and collect IDs
        image_option_ids = []
        values_parts = []

        for i, image_info in enumerate(images):
            image_id = generate_uuid()
            validated_id = self._validate_uuid(image_id)
            validated_source = self._validate_image_source(source)
            escaped_filename = self._escape_sql_string(image_info.filename)
            escaped_url = self._escape_sql_string(image_info.url)
            escaped_key = self._escape_sql_string(image_info.key)

            # Add comma for all entries except the last one
            comma = "," if i < len(images) - 1 else ""
            values_parts.append(f"    ('{validated_id}', '{validated_source}'::\"ImageSource\", '{escaped_url}', '{escaped_key}', NULL, NULL, NULL, NULL, NULL){comma} -- {escaped_filename}")
            image_option_ids.append(image_id)

        # Create single bulk INSERT for ImageOption
        image_option_sql = f"""INSERT INTO "ImageOption" (
    "id",
    "source",
    "url",
    "downloadLocation",
    "authorName",
    "authorImage",
    "authorLink",
    "referalLink",
    "imageSourceId"
) VALUES
{chr(10).join(values_parts)};"""

        sql_parts.append(image_option_sql)
        sql_parts.extend(["", "-- PresentationLayoutImageOption bulk INSERT statement"])

        # Generate bulk INSERT for junction table
        if presentation_layout_id:
            validated_layout_id = self._validate_uuid(presentation_layout_id)
            junction_values = []
            for i, image_option_id in enumerate(image_option_ids):
                validated_image_id = self._validate_uuid(image_option_id)
                comma = "," if i < len(image_option_ids) - 1 else ""
                junction_values.append(f"    ('{validated_image_id}', '{validated_layout_id}'){comma}")

            junction_sql = f"""INSERT INTO "PresentationLayoutImageOption" (
    "imageOptionId",
    "presentationLayoutId"
) VALUES
{chr(10).join(junction_values)};"""

            sql_parts.append(junction_sql)

        sql_parts.extend(["", "COMMIT;"])
        return "\n".join(sql_parts), image_option_ids

    def generate_batch_delete_sql_by_ids(self, image_option_ids: list[str]) -> str:
        """Generate batch DELETE SQL using specific ImageOption IDs."""
        if not image_option_ids:
            return ""

        # Validate all UUIDs first
        validated_ids = [self._validate_uuid(id_) for id_ in image_option_ids]

        # Create comma-separated list of validated IDs for WHERE IN clause
        # Split into multiple lines for better readability if there are many IDs
        if len(validated_ids) > 10:
            # Format with multiple lines for readability
            ids_formatted = []
            for i, id_ in enumerate(validated_ids):
                if i % 10 == 0 and i > 0:
                    ids_formatted.append(f"\n        '{id_}'")
                else:
                    ids_formatted.append(f"'{id_}'")
            ids_in_clause = ", ".join(ids_formatted)
        else:
            ids_in_clause = ", ".join([f"'{id_}'" for id_ in validated_ids])

        sql_parts = [
            "-- Batch delete ImageOptions and related PresentationLayoutImageOption records by IDs",
            "BEGIN;",
            "",
            "-- Delete PresentationLayoutImageOption records",
            f"""DELETE FROM "PresentationLayoutImageOption" WHERE "imageOptionId" IN ({ids_in_clause});""",
            "",
            "-- Delete ImageOption records",
            f"""DELETE FROM "ImageOption" WHERE "id" IN ({ids_in_clause});""",
            "",
            "COMMIT;",
        ]

        return "\n".join(sql_parts)

    def save_sql_to_file(self, sql_content: str, output_file: str) -> None:
        """Save SQL content to file."""
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(sql_content)
            if logger:
                logger.info(f"SQL saved to: {output_file}")
        except Exception as error:
            if logger:
                logger.error(f"Error saving SQL to file: {error}")
            raise


def create_env_file() -> bool:
    """Interactive function to create .env file."""
    print("Yandex Cloud Credentials Setup")
    print("Get these from: Yandex Cloud Console → Service Accounts → Static Access Keys\n")

    yandex_static_key = input("YANDEX_STATIC_KEY (Access Key ID): ").strip()
    yandex_static_secret = input("YANDEX_STATIC_SECRET (Secret Access Key): ").strip()
    yandex_bucket_name = input("YANDEX_BUCKET_NAME [presentsimple-dev-s3]: ").strip() or "presentsimple-dev-s3"

    print("\nConfiguration")
    s3_prefix = input("S3 prefix to scan [layouts/raiffeisen/miniatures/]: ").strip() or "layouts/raiffeisen/miniatures/"
    image_source = input("Image source type [brand]: ").strip() or "brand"
    output_file = input("Output SQL file [insert_image_options.sql]: ").strip() or "insert_image_options.sql"

    env_content = f"""# Yandex Cloud Credentials
YANDEX_STATIC_KEY={yandex_static_key}
YANDEX_STATIC_SECRET={yandex_static_secret}
YANDEX_BUCKET_NAME={yandex_bucket_name}

# Configuration
S3_PREFIX={s3_prefix}
IMAGE_SOURCE={image_source}
OUTPUT_FILE={output_file}
"""

    with open(".env", "w") as f:
        f.write(env_content)

    print("\nCreated .env file successfully!")
    print("Security: Add .env to your .gitignore file")
    return True


def check_credentials() -> list[str]:
    """Check if required credentials are available."""
    required_vars = ["YANDEX_STATIC_KEY", "YANDEX_STATIC_SECRET", "YANDEX_BUCKET_NAME"]
    return [var for var in required_vars if not os.getenv(var)]


def group_images_by_folder(images: list[S3ImageInfo]) -> dict[str, list[S3ImageInfo]]:
    """Group images by folder for better organization."""
    images_by_folder: dict[str, list[S3ImageInfo]] = {}

    for image in images:
        folder = image.folder_path or "root"
        if folder not in images_by_folder:
            images_by_folder[folder] = []
        images_by_folder[folder].append(image)

    return images_by_folder


def main() -> None:
    """Main function to generate SQL for image options."""
    global logger
    logger = LoggerSetup.setup()

    try:
        # Check credentials
        missing_vars = check_credentials()
        if missing_vars:
            logger.error(f"Missing credentials: {', '.join(missing_vars)}")
            print(f"Missing credentials: {', '.join(missing_vars)}")
            choice = input("Create .env file? (y/n): ").strip().lower()

            if choice == "y":
                create_env_file()
                load_dotenv(override=True)
                missing_vars = check_credentials()
                if missing_vars:
                    logger.error("Still missing credentials after .env creation")
                    print("Still missing credentials. Please check your .env file.")
                    return
            else:
                print("Set environment variables and run again.")
                return

        # Load configuration
        config = Config.from_env()

        if not config.presentation_layout_id:
            logger.warning("No PresentationLayout ID found in config - skipping junction table generation")

        logger.info(f"Starting image scan from s3://{config.bucket_name}/{config.s3_prefix}")

        # Initialize services
        scanner = S3ImageScanner(config)
        sql_generator = SQLGenerator()

        if not scanner.check_bucket_access():
            logger.error("Cannot access Yandex Cloud bucket. Exiting.")
            print("Cannot access Yandex Cloud bucket. Check credentials.")
            return

        # Scan for images
        logger.info(f"Scanning bucket for images with prefix: {config.s3_prefix}")
        images = scanner.list_images(config.s3_prefix)

        if not images:
            logger.warning("No images found in the specified prefix")
            print("No images found in the specified prefix")
            return

        logger.info(f"Found {len(images)} images to process")

        # Group images by folder for better organization
        images_by_folder = group_images_by_folder(images)

        # Generate single large INSERT transaction for all images
        all_insert_sql_parts = ["-- Generated ImageOption INSERT statements", f"-- Source: s3://{config.bucket_name}/{config.s3_prefix}", f"-- Total images: {len(images)}", ""]

        all_delete_sql_parts = ["-- Generated ImageOption DELETE statements", f"-- Source: s3://{config.bucket_name}/{config.s3_prefix}", f"-- Total images: {len(images)}", ""]

        # Add folder organization comments
        for folder, folder_images in images_by_folder.items():
            all_insert_sql_parts.extend([f"-- Folder: {folder}", f"-- Images: {len(folder_images)}", ""])

        logger.info(f"Generating single large INSERT transaction for {len(images)} images")

        # Generate one large transaction for all images
        single_insert_sql, all_generated_ids = sql_generator.generate_batch_sql(images, config.presentation_layout_id, config.image_source.value)
        all_insert_sql_parts.append(single_insert_sql)

        # Generate single DELETE SQL using all generated IDs
        logger.info(f"Generating single DELETE transaction for {len(all_generated_ids)} ImageOption IDs")
        single_delete_sql = sql_generator.generate_batch_delete_sql_by_ids(all_generated_ids)
        all_delete_sql_parts.append(single_delete_sql)

        # Save SQL files
        final_insert_sql = "\n".join(all_insert_sql_parts)
        final_delete_sql = "\n".join(all_delete_sql_parts)

        sql_generator.save_sql_to_file(final_insert_sql, config.output_file)

        delete_output_file = "delete_image_options.sql"
        sql_generator.save_sql_to_file(final_delete_sql, delete_output_file)

        # Calculate statistics
        junction_records_count = len(images) if config.presentation_layout_id else 0

        # Log summary
        logger.info("SQL generation completed!")
        logger.info(f"Total images processed: {len(images)}")
        logger.info(f"Folders found: {len(images_by_folder)}")
        logger.info(f"PresentationLayout ID: {config.presentation_layout_id}")
        logger.info(f"PresentationLayoutImageOption records to create: {junction_records_count}")
        logger.info(f"INSERT SQL saved to: {config.output_file}")
        logger.info(f"DELETE SQL saved to: {delete_output_file}")

        # Print summary to console
        print(f"Processed {len(images)} images and generated SQL statements")
        print(f"Found {len(images_by_folder)} folders")
        print(f"PresentationLayout ID: {config.presentation_layout_id}")
        print(f"Junction records to create: {junction_records_count}")
        print(f"INSERT SQL saved to: {config.output_file}")
        print(f"DELETE SQL saved to: {delete_output_file}")
        print("Detailed logs: logs/image_options_generation.log")

    except Exception as error:
        logger.error(f"SQL generation failed: {error}")
        raise


if __name__ == "__main__":
    main()
