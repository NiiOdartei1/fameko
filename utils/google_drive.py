"""
Google Drive utility for downloading GraphML files
"""
import os
import logging
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
import io

logger = logging.getLogger(__name__)

def download_file_from_drive(file_id, destination_path, credentials_json=None):
    """
    Download a file from Google Drive
    
    Args:
        file_id: Google Drive file ID
        destination_path: Local path to save the file
        credentials_json: JSON string of service account credentials
    """
    try:
        # If credentials_json is provided, use service account
        if credentials_json:
            import json
            credentials_info = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
        else:
            # Use default credentials (from environment)
            from google.auth import default
            credentials, _ = default()
        
        # Build Drive service
        service = build('drive', 'v3', credentials=credentials)
        
        # Get file metadata
        file_metadata = service.files().get(fileId=file_id).execute()
        logger.info(f"Downloading file: {file_metadata['name']} ({file_metadata.get('size', 'unknown')} bytes)")
        
        # Download file
        request = service.files().get_media(fileId=file_id)
        
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        # Write file to destination
        with io.FileIO(destination_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                if status:
                    logger.info(f"Download progress: {int(status.progress() * 100)}%")
        
        logger.info(f"File downloaded successfully to: {destination_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error downloading file from Google Drive: {e}")
        return False


def download_graphml_files():
    """
    Download all required GraphML files from Google Drive
    Called during app startup
    """
    # Get file IDs from environment variables
    files_to_download = [
        {
            'file_id': os.environ.get('GOOGLE_DRIVE_ASHANTI_FILE_ID'),
            'destination': 'data/Ashanti_Region_Ghana.graphml'
        }
    ]
    
    credentials_json = os.environ.get('GOOGLE_DRIVE_CREDENTIALS')
    
    for file_info in files_to_download:
        if not file_info['file_id']:
            logger.warning(f"No file ID provided for {file_info['destination']}, skipping")
            continue
        
        # Check if file already exists locally
        if os.path.exists(file_info['destination']):
            logger.info(f"File already exists: {file_info['destination']}, skipping download")
            continue
        
        success = download_file_from_drive(
            file_info['file_id'],
            file_info['destination'],
            credentials_json
        )
        
        if not success:
            logger.error(f"Failed to download {file_info['destination']}")


if __name__ == '__main__':
    # Test the download function
    logging.basicConfig(level=logging.INFO)
    download_graphml_files()
