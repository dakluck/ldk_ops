---
name: google-drive
description: Manages, searches, uploads, organizes, and retrieves files and folders in Google Drive for both business (dailey@ldk-international.com) and personal (dailey.kluck@gmail.com) accounts using drive_manager.py and drive_oauth_helper.py.
---

# Google Drive Integration for LDK Ops

This skill enables full programmatic access to Google Drive for:
- **Business Account:** `dailey@ldk-international.com` (token: `.google_drive_token.json`)
- **Personal Account:** `dailey.kluck@gmail.com` (token: `.google_drive_token_personal.json`)

## Primary Components
- **OAuth & Credentials:** [`drive_oauth_helper.py`](file:///home/dailey/Development/ldk_ops/drive_oauth_helper.py)
- **Token Cache:** `.google_drive_token.json` & `.google_drive_token_personal.json` (gitignored, 0600 permissions, automatic refresh)
- **Drive Client & CLI:** [`drive_manager.py`](file:///home/dailey/Development/ldk_ops/drive_manager.py)

## CLI Usage

```bash
# Authorize personal or business account
python3 drive_oauth_helper.py --account personal
python3 drive_oauth_helper.py --account business

# List top-level files (default: business)
python3 drive_manager.py list
python3 drive_manager.py --account personal list

# Print directory tree
python3 drive_manager.py list --tree
python3 drive_manager.py --account personal list --tree

# Search files by name
python3 drive_manager.py search "Tax 2025"
python3 drive_manager.py --account personal search "Receipt"

# Create a folder
python3 drive_manager.py mkdir "LDK Corporate Documents"

# Upload a file
python3 drive_manager.py upload /path/to/local/file.pdf --parent <FOLDER_ID>
```

## Python SDK Usage

```python
from drive_manager import GoogleDriveClient

# Access business Drive (default)
client = GoogleDriveClient(account="business")

# Access personal Drive
personal_client = GoogleDriveClient(account="personal")
files = personal_client.list_files(query="mimeType = 'application/pdf'")
```
