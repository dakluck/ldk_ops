---
name: google-drive
description: Manages, searches, uploads, organizes, and retrieves files and folders in Google Drive for dailey@ldk-international.com using drive_manager.py and drive_oauth_helper.py.
---

# Google Drive Integration for LDK Ops

This skill enables full programmatic access to Google Drive for `dailey@ldk-international.com`.

## Primary Components
- **OAuth & Credentials:** [`drive_oauth_helper.py`](file:///home/dailey/Development/ldk_ops/drive_oauth_helper.py)
- **Token Cache:** `.google_drive_token.json` (gitignored, 0600 permissions, automatic refresh)
- **Drive Client & CLI:** [`drive_manager.py`](file:///home/dailey/Development/ldk_ops/drive_manager.py)

## CLI Usage

```bash
# List top-level files
python3 drive_manager.py list

# Print directory tree
python3 drive_manager.py list --tree

# Search files by name
python3 drive_manager.py search "Tax 2025"

# Create a folder
python3 drive_manager.py mkdir "LDK Corporate Documents"

# Upload a file
python3 drive_manager.py upload /path/to/local/file.pdf --parent <FOLDER_ID>
```

## Python SDK Usage

```python
from drive_manager import GoogleDriveClient

client = GoogleDriveClient()
files = client.list_files(query="mimeType = 'application/pdf'")
folder = client.get_or_create_folder("Legal & Corporate")
client.upload_file(local_path="Articles_of_Org.pdf", parent_id=folder["id"])
```
