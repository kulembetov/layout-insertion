#!/usr/bin/env python3
"""
Clean script to download images from Google Drive and upload to Yandex Cloud Object Storage
"""

import os
import io
import logging
from typing import List, TypedDict, Optional
from pathlib import Path
import mimetypes

# Required libraries
try:
    import boto3
    from botocore.exceptions import ClientError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaIoBaseDownload
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required library: {e}")
    print("Install with: pip install boto3 google-api-python-client google-auth-oauthlib python-dotenv")
    exit(1)

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'
YANDEX_ENDPOINT_URL = "https://storage.yandexcloud.net"
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg'}

# Type definitions
class GoogleDriveFile(TypedDict):
    """Type definition for Google Drive file objects"""
    id: str
    name: str
    mimeType: str
    size: Optional[str]

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GoogleDriveDownloader:
    """Handles Google Drive authentication and file downloads"""
    
    def __init__(self):
        self.service = self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API"""
        creds = None
        
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, GOOGLE_SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"Google credentials file '{CREDENTIALS_FILE}' not found. "
                        "Download it from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, GOOGLE_SCOPES)
                
                try:
                    logger.info("Starting OAuth flow...")
                    creds = flow.run_local_server(port=0, open_browser=True)
                except Exception as e:
                    logger.warning(f"Local server OAuth failed: {e}")
                    logger.info("Falling back to console-based OAuth flow...")
                    creds = flow.run_console()
            
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
        
        logger.info("Successfully authenticated with Google Drive")
        return build('drive', 'v3', credentials=creds)
    
    def list_files_in_folder(self, folder_id: str) -> List[GoogleDriveFile]:
        """List all files in a Google Drive folder with pagination"""
        all_files: List[GoogleDriveFile] = []
        page_token: Optional[str] = None
        
        try:
            while True:
                query = f"'{folder_id}' in parents and trashed=false"
                request_params = {
                    'q': query,
                    'fields': "nextPageToken, files(id, name, mimeType, size)",
                    'pageSize': 1000
                }
                
                if page_token:
                    request_params['pageToken'] = page_token
                
                results = self.service.files().list(**request_params).execute()
                files = results.get('files', [])
                all_files.extend(files)
                
                logger.info(f"Retrieved {len(files)} files (total: {len(all_files)})")
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            return all_files
            
        except HttpError as error:
            logger.error(f"Error listing files: {error}")
            return all_files
    
    def is_image_file(self, filename: str, mime_type: str) -> bool:
        """Check if file is an image"""
        file_ext = Path(filename).suffix.lower()
        return file_ext in IMAGE_EXTENSIONS or mime_type.startswith('image/')
    
    def download_file(self, file_id: str, filename: str) -> Optional[bytes]:
        """Download a file from Google Drive"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.info(f"Download progress for {filename}: {int(status.progress() * 100)}%")
            
            file_buffer.seek(0)
            return file_buffer.read()
            
        except HttpError as error:
            logger.error(f"Error downloading {filename}: {error}")
            return None


class YandexCloudUploader:
    """Handles Yandex Cloud Object Storage uploads"""
    
    def __init__(self):
        self.s3_client = self._setup_client()
        self.bucket_name = os.getenv('YANDEX_BUCKET_NAME')
    
    def _setup_client(self):
        """Setup S3 client for Yandex Cloud"""
        access_key = os.getenv('YANDEX_STATIC_KEY')
        secret_key = os.getenv('YANDEX_STATIC_SECRET')
        
        if not access_key or not secret_key:
            raise ValueError("Yandex Cloud credentials not found. Set YANDEX_STATIC_KEY and YANDEX_STATIC_SECRET")
        
        return boto3.client(
            's3',
            endpoint_url=YANDEX_ENDPOINT_URL,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name='ru-central1'
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
    
    def upload_file(self, file_data: bytes, key: str, content_type: Optional[str] = None) -> bool:
        """Upload file to Yandex Cloud bucket"""
        try:
            if not content_type:
                content_type = mimetypes.guess_type(key)[0] or 'application/octet-stream'
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_data,
                ContentType=content_type
            )
            
            logger.info(f"Successfully uploaded: {key}")
            return True
            
        except ClientError as error:
            logger.error(f"Error uploading {key}: {error}")
            return False


def create_env_file():
    """Interactive function to create .env file"""
    print("Yandex Cloud Credentials Setup")
    print("Get these from: Yandex Cloud Console → Service Accounts → Static Access Keys\n")
    
    yandex_static_key = input("YANDEX_STATIC_KEY (Access Key ID): ").strip()
    yandex_static_secret = input("YANDEX_STATIC_SECRET (Secret Access Key): ").strip()
    yandex_bucket_name = input("YANDEX_BUCKET_NAME [presentsimple-dev-s3]: ").strip()
    
    print("\nGoogle Drive & Path Configuration")
    google_folder_id = input("Google Drive folder ID [1m5H3yQJhTuCF3dmQGJ-zAVqsY_T6dSfk]: ").strip()
    yandex_folder_path = input("Yandex folder path [layouts/raiffeisen/]: ").strip()
    
    env_content = f"""# Yandex Cloud Credentials
YANDEX_STATIC_KEY={yandex_static_key}
YANDEX_STATIC_SECRET={yandex_static_secret}
YANDEX_BUCKET_NAME={yandex_bucket_name}

# Configuration
GOOGLE_DRIVE_FOLDER_ID={google_folder_id}
YANDEX_FOLDER_PATH={yandex_folder_path}
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("\nCreated .env file successfully!")
    print("Security: Add .env to your .gitignore file")
    return True


def check_credentials():
    """Check if required credentials are available"""
    required_vars = ['YANDEX_STATIC_KEY', 'YANDEX_STATIC_SECRET', 'YANDEX_BUCKET_NAME']
    missing = [var for var in required_vars if not os.getenv(var)]
    return missing


def main():
    """Main migration function"""
    try:
        # Check credentials
        missing_vars = check_credentials()
        if missing_vars:
            print(f"Missing credentials: {', '.join(missing_vars)}")
            choice = input("Create .env file? (y/n): ").strip().lower()
            
            if choice == 'y':
                create_env_file()
                load_dotenv(override=True)
                if check_credentials():
                    print("Still missing credentials. Please check your .env file.")
                    return
            else:
                print("Set environment variables and run again.")
                return
        
        # Get configuration
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '1m5H3yQJhTuCF3dmQGJ-zAVqsY_T6dSfk')
        folder_path = os.getenv('YANDEX_FOLDER_PATH', 'layouts/raiffeisen/')
        bucket_name = os.getenv('YANDEX_BUCKET_NAME')
        
        logger.info(f"Starting migration from Google Drive to s3://{bucket_name}/{folder_path}")
        
        # Initialize services
        gdrive = GoogleDriveDownloader()
        yandex = YandexCloudUploader()
        
        if not yandex.check_bucket_access():
            logger.error("Cannot access Yandex Cloud bucket. Exiting.")
            return
        
        # Get and filter files
        logger.info("Fetching files from Google Drive...")
        files = gdrive.list_files_in_folder(folder_id)
        
        if not files:
            logger.warning("No files found in Google Drive folder")
            return
        
        image_files = [f for f in files if gdrive.is_image_file(f['name'], f.get('mimeType', ''))]
        logger.info(f"Found {len(image_files)} image files to migrate")
        
        # Process files
        successful_uploads = 0
        failed_uploads = 0
        
        for i, file_info in enumerate(image_files, 1):
            filename = file_info['name']
            logger.info(f"Processing {i}/{len(image_files)}: {filename}")
            
            # Download
            file_data = gdrive.download_file(file_info['id'], filename)
            if not file_data:
                failed_uploads += 1
                continue
            
            # Upload
            yandex_key = f"{folder_path}{filename}"
            if yandex.upload_file(file_data, yandex_key, file_info.get('mimeType')):
                successful_uploads += 1
            else:
                failed_uploads += 1
        
        # Summary
        logger.info("Migration completed!")
        logger.info(f"Successful: {successful_uploads} files")
        logger.info(f"Failed: {failed_uploads} files")
        
        if successful_uploads > 0:
            logger.info(f"Files available at: s3://{bucket_name}/{folder_path}")
        
    except Exception as error:
        logger.error(f"Migration failed: {error}")
        raise


if __name__ == "__main__":
    main()