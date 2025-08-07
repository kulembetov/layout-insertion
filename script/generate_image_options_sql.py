#!/usr/bin/env python3
"""
Script to scan S3 bucket for images and generate SQL statements for ImageOption insertion.
Follows the design patterns of the existing codebase.
"""

import logging
import mimetypes
import os
from pathlib import Path
from typing import TypedDict

import boto3
import uuid_utils as uuid
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
YANDEX_ENDPOINT_URL = "https://storage.yandexcloud.net"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".svg"}
DEFAULT_IMAGE_SOURCE = "brand"


# Type definitions
class S3ImageInfo(TypedDict):
    """Type definition for S3 image information"""

    key: str
    filename: str
    size: int
    content_type: str
    url: str
    folder_path: str


# Setup logging
def setup_logging():
    """Setup logging to both file and console"""
    # Setup file handler
    file_handler = logging.FileHandler("image_options_generation.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)

    # Setup console handler (only for errors and critical messages)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)

    # Setup logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()


def generate_uuid() -> str:
    """Generate a UUID7 string for database use."""
    return str(uuid.uuid7())


class S3ImageScanner:
    """Handles S3 bucket scanning for images"""

    def __init__(self):
        self.s3_client = self._setup_client()
        self.bucket_name = os.getenv("YANDEX_BUCKET_NAME")

    def _setup_client(self):
        """Setup S3 client for Yandex Cloud"""
        access_key = os.getenv("YANDEX_STATIC_KEY")
        secret_key = os.getenv("YANDEX_STATIC_SECRET")

        if not access_key or not secret_key:
            raise ValueError("Yandex Cloud credentials not found. Set YANDEX_STATIC_KEY and YANDEX_STATIC_SECRET")

        return boto3.client(
            "s3",
            endpoint_url=YANDEX_ENDPOINT_URL,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="ru-central1",
        )

    def check_bucket_access(self) -> bool:
        """Check if we can access the bucket"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Successfully accessed bucket: {self.bucket_name}")
            return True
        except ClientError as error:
            logger.error(f"Cannot access bucket {self.bucket_name}: {error}")
            return False

    def is_image_file(self, key: str) -> bool:
        """Check if file is an image based on extension"""
        file_ext = Path(key).suffix.lower()
        return file_ext in IMAGE_EXTENSIONS

    def extract_folder_path(self, key: str) -> str:
        """Extract folder path from S3 key"""
        path_parts = key.split("/")
        if len(path_parts) > 1:
            return "/".join(path_parts[:-1]) + "/"
        return ""

    def list_images_in_bucket(self, prefix: str = "") -> list[S3ImageInfo]:
        """List all images in S3 bucket with optional prefix"""
        images: list[S3ImageInfo] = []
        paginator = self.s3_client.get_paginator("list_objects_v2")

        try:
            page_iterator = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)

            for page in page_iterator:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        key = obj["Key"]

                        if self.is_image_file(key):
                            # Extract filename and folder path
                            filename = Path(key).name
                            folder_path = self.extract_folder_path(key)

                            # Build full URL
                            url = f"https://storage.yandexcloud.net/{self.bucket_name}/{key}"

                            # Determine content type
                            content_type = mimetypes.guess_type(key)[0] or "image/jpeg"

                            images.append({"key": key, "filename": filename, "size": obj["Size"], "content_type": content_type, "url": url, "folder_path": folder_path})

            logger.info(f"Found {len(images)} images in bucket")
            return images

        except ClientError as error:
            logger.error(f"Error listing objects in bucket: {error}")
            return images


class SQLGenerator:
    """Generates SQL statements for ImageOption insertion"""

    def __init__(self) -> None:
        self.sql_statements: list[str] = []

    def generate_image_option_sql(self, image_info: S3ImageInfo, source: str = DEFAULT_IMAGE_SOURCE) -> str:
        """Generate SQL statement for a single ImageOption"""
        image_id = generate_uuid()

        sql = f"""-- ImageOption: {image_info['filename']}
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
            '{image_id}',
            '{source}'::"ImageSource",
            '{image_info["url"]}',    # ← Fixed: double quotes inside
            '{image_info["key"]}',    # ← Fixed: double quotes inside
            NULL,
            NULL,
            NULL,
            NULL,
            NULL
        );"""  # nosec

        return sql

    def generate_batch_sql(self, images: list[S3ImageInfo], source: str = DEFAULT_IMAGE_SOURCE) -> str:
        """Generate batch SQL for multiple ImageOptions"""
        if not images:
            return ""

        sql_parts = []
        sql_parts.append("-- Batch insert ImageOptions")
        sql_parts.append("BEGIN;")
        sql_parts.append("")

        for image_info in images:
            sql_parts.append(self.generate_image_option_sql(image_info, source))
            sql_parts.append("")

        sql_parts.append("COMMIT;")

        return "\n".join(sql_parts)

    def save_sql_to_file(self, sql_content: str, output_file: str):
        """Save SQL content to file"""
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(sql_content)
            logger.info(f"SQL saved to: {output_file}")
        except Exception as error:
            logger.error(f"Error saving SQL to file: {error}")


def create_env_file():
    """Interactive function to create .env file"""
    print("Yandex Cloud Credentials Setup")
    print("Get these from: Yandex Cloud Console → Service Accounts → Static Access Keys\n")

    yandex_static_key = input("YANDEX_STATIC_KEY (Access Key ID): ").strip()
    yandex_static_secret = input("YANDEX_STATIC_SECRET (Secret Access Key): ").strip()
    yandex_bucket_name = input("YANDEX_BUCKET_NAME [presentsimple-dev-s3]: ").strip()

    print("\nConfiguration")
    s3_prefix = input("S3 prefix to scan [layouts/raiffeisen/miniatures/]: ").strip()
    image_source = input("Image source type [uploaded]: ").strip()
    output_file = input("Output SQL file [image_options.sql]: ").strip()

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


def check_credentials():
    """Check if required credentials are available"""
    required_vars = ["YANDEX_STATIC_KEY", "YANDEX_STATIC_SECRET", "YANDEX_BUCKET_NAME"]
    missing = [var for var in required_vars if not os.getenv(var)]
    return missing


def main():
    """Main function to generate SQL for image options"""
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
                if check_credentials():
                    logger.error("Still missing credentials after .env creation")
                    print("Still missing credentials. Please check your .env file.")
                    return
            else:
                print("Set environment variables and run again.")
                return

        # Get configuration
        s3_prefix = os.getenv("S3_PREFIX", "layouts/raiffeisen/miniatures/")
        image_source = os.getenv("IMAGE_SOURCE", DEFAULT_IMAGE_SOURCE)
        output_file = os.getenv("OUTPUT_FILE", "image_options.sql")
        bucket_name = os.getenv("YANDEX_BUCKET_NAME")

        logger.info(f"Starting image scan from s3://{bucket_name}/{s3_prefix}")

        # Initialize services
        scanner = S3ImageScanner()
        sql_generator = SQLGenerator()

        if not scanner.check_bucket_access():
            logger.error("Cannot access Yandex Cloud bucket. Exiting.")
            print("Cannot access Yandex Cloud bucket. Check credentials.")
            return

        # Scan for images
        logger.info(f"Scanning bucket for images with prefix: {s3_prefix}")
        images = scanner.list_images_in_bucket(s3_prefix)

        if not images:
            logger.warning("No images found in the specified prefix")
            print("No images found in the specified prefix")
            return

        logger.info(f"Found {len(images)} images to process")

        # Group images by folder for better organization
        images_by_folder = {}
        for image in images:
            folder = image["folder_path"] or "root"
            if folder not in images_by_folder:
                images_by_folder[folder] = []
            images_by_folder[folder].append(image)

        # Generate SQL
        all_sql_parts = []
        all_sql_parts.append("-- Generated ImageOption SQL statements")
        all_sql_parts.append(f"-- Source: s3://{bucket_name}/{s3_prefix}")
        all_sql_parts.append(f"-- Total images: {len(images)}")
        all_sql_parts.append("")

        for folder, folder_images in images_by_folder.items():
            logger.info(f"Processing folder: {folder} ({len(folder_images)} images)")

            all_sql_parts.append(f"-- Folder: {folder}")
            all_sql_parts.append(f"-- Images: {len(folder_images)}")
            all_sql_parts.append("")

            # Generate SQL for this folder
            folder_sql = sql_generator.generate_batch_sql(folder_images, image_source)
            all_sql_parts.append(folder_sql)
            all_sql_parts.append("")

            logger.info(f"Generated SQL for folder: {folder} ({len(folder_images)} images)")

        # Combine all SQL
        final_sql = "\n".join(all_sql_parts)

        # Save to file
        sql_generator.save_sql_to_file(final_sql, output_file)

        # Summary
        logger.info("SQL generation completed!")
        logger.info(f"Total images processed: {len(images)}")
        logger.info(f"Folders found: {len(images_by_folder)}")
        logger.info(f"SQL saved to: {output_file}")

        # Print only the summary to console
        print(f"Processed {len(images)} images and generated SQL statements")
        print(f"Found {len(images_by_folder)} folders")
        print(f"SQL saved to: {output_file}")
        print("Detailed logs: image_options_generation.log")

    except Exception as error:
        logger.error(f"SQL generation failed: {error}")
        raise


if __name__ == "__main__":
    main()
