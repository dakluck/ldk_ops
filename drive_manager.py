#!/usr/bin/env python3
"""
Google Drive Manager for LDK Ops
Provides full programmatic access, folder organization, file upload/download,
and search capabilities for dailey@ldk-international.com.
"""

import os
import sys
import json
import urllib.parse
import urllib.request
import mimetypes
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

SCRIPT_DIR = Path(__file__).resolve().parent
TOKEN_FILE = SCRIPT_DIR / ".google_drive_token.json"
TOKEN_URI = "https://oauth2.googleapis.com/token"


class GoogleDriveClient:
    """Client for interacting with Google Drive API v3."""

    def __init__(self, token_path: Path = TOKEN_FILE):
        self.token_path = token_path
        self.creds = self._load_credentials()

    def _load_credentials(self) -> Dict[str, Any]:
        if not self.token_path.exists():
            raise FileNotFoundError(
                f"Google Drive credentials not found at {self.token_path}.\n"
                f"Please run 'python3 drive_oauth_helper.py' to authorize access."
            )
        try:
            return json.loads(self.token_path.read_text())
        except Exception as e:
            raise RuntimeError(f"Failed to read token file {self.token_path}: {e}")

    def _save_credentials(self):
        self.token_path.write_text(json.dumps(self.creds, indent=2))
        os.chmod(self.token_path, 0o600)

    def get_access_token(self) -> str:
        """Returns valid access token, refreshing it if necessary."""
        token = self.creds.get("access_token")
        # Validate current token
        if token:
            req = urllib.request.Request(
                f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={token}"
            )
            try:
                with urllib.request.urlopen(req) as resp:
                    info = json.loads(resp.read().decode("utf-8"))
                    if "expires_in" in info and int(info["expires_in"]) > 60:
                        return token
            except Exception:
                pass  # Expired or invalid, proceed to refresh

        return self.refresh_access_token()

    def refresh_access_token(self) -> str:
        """Refreshes access token using refresh_token."""
        refresh_token = self.creds.get("refresh_token")
        if not refresh_token:
            raise RuntimeError(
                "No refresh_token found in credentials. Please re-run drive_oauth_helper.py."
            )

        data = urllib.parse.urlencode({
            "client_id": self.creds.get("client_id"),
            "client_secret": self.creds.get("client_secret"),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }).encode("utf-8")

        req = urllib.request.Request(
            TOKEN_URI,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        try:
            with urllib.request.urlopen(req) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                new_token = res.get("access_token")
                self.creds["access_token"] = new_token
                self._save_credentials()
                return new_token
        except Exception as e:
            raise RuntimeError(f"Failed to refresh Google Drive access token: {e}")

    def _api_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Executes an authorized HTTP request against the Google Drive API."""
        access_token = self.get_access_token()
        url = endpoint if endpoint.startswith("http") else f"https://www.googleapis.com/drive/v3/{endpoint}"
        
        req_headers = {
            "Authorization": f"Bearer {access_token}"
        }
        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise RuntimeError(f"Drive API Error ({e.code}): {error_body}")

    def list_files(
        self,
        query: str = "trashed = false",
        parent_id: Optional[str] = None,
        page_size: int = 50,
        fields: str = "files(id, name, mimeType, modifiedTime, size, parents, webViewLink)"
    ) -> List[Dict[str, Any]]:
        """Lists files matching query."""
        q_parts = [query]
        if parent_id:
            q_parts.append(f"'{parent_id}' in parents")
        full_q = " and ".join(f"({p})" for p in q_parts)
        
        params = {
            "q": full_q,
            "pageSize": str(page_size),
            "fields": f"nextPageToken, {fields}",
            "orderBy": "folder,name"
        }
        url = f"https://www.googleapis.com/drive/v3/files?{urllib.parse.urlencode(params)}"
        res = self._api_request(url)
        return res.get("files", [])

    def create_folder(self, name: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Creates a folder in Google Drive."""
        metadata: Dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        if parent_id:
            metadata["parents"] = [parent_id]
        
        data = json.dumps(metadata).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=UTF-8"}
        return self._api_request("files", method="POST", data=data, headers=headers)

    def get_or_create_folder(self, name: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Finds a folder by name or creates it if it doesn't exist."""
        q = f"mimeType = 'application/vnd.google-apps.folder' and name = '{name}' and trashed = false"
        if parent_id:
            q += f" and '{parent_id}' in parents"
        files = self.list_files(query=q)
        if files:
            return files[0]
        return self.create_folder(name, parent_id=parent_id)

    def upload_file(
        self,
        local_path: Path,
        name: Optional[str] = None,
        parent_id: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Uploads a local file to Google Drive using multipart upload."""
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        file_name = name or local_path.name
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(str(local_path))
            mime_type = mime_type or "application/octet-stream"

        metadata: Dict[str, Any] = {"name": file_name}
        if parent_id:
            metadata["parents"] = [parent_id]

        boundary = "===============7330837588304934567=="
        crlf = b"\r\n"
        meta_part = (
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(metadata)}\r\n"
        ).encode("utf-8")

        media_header = (
            f"--{boundary}\r\n"
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode("utf-8")

        file_content = local_path.read_bytes()
        closing = f"\r\n--{boundary}--\r\n".encode("utf-8")

        body = meta_part + media_header + file_content + closing
        headers = {
            "Content-Type": f"multipart/related; boundary={boundary}",
            "Content-Length": str(len(body))
        }

        url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,mimeType,webViewLink"
        return self._api_request(url, method="POST", data=body, headers=headers)

    def move_file(self, file_id: str, new_parent_id: str, current_parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Moves a file to a new folder."""
        params = {
            "addParents": new_parent_id,
            "fields": "id, name, parents"
        }
        if current_parent_id:
            params["removeParents"] = current_parent_id
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?{urllib.parse.urlencode(params)}"
        return self._api_request(url, method="PATCH")

    def upload_directory(self, local_dir: Path, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Recursively mirrors a local directory structure into Google Drive."""
        local_dir = Path(local_dir)
        folder = self.get_or_create_folder(local_dir.name, parent_id=parent_id)
        folder_id = folder["id"]

        for item in sorted(local_dir.iterdir()):
            if item.name.startswith("."):
                continue
            if item.is_dir():
                self.upload_directory(item, parent_id=folder_id)
            elif item.is_file():
                existing = self.list_files(query=f"name = '{item.name}' and trashed = false", parent_id=folder_id)
                if not existing:
                    print(f"  ⬆️ Uploading {item.name} to {local_dir.name}/...")
                    self.upload_file(item, parent_id=folder_id)
                else:
                    print(f"  ✓ {item.name} already exists in {local_dir.name}/")
        return folder


def print_tree(client: GoogleDriveClient, folder_id: str = "root", indent: int = 0, max_depth: int = 2):
    """Prints a formatted hierarchical directory tree of Google Drive contents."""
    if indent // 2 >= max_depth:
        return

    items = client.list_files(parent_id=folder_id)
    prefix = "  " * indent
    for item in items:
        name = item.get("name")
        item_id = item.get("id")
        mime = item.get("mimeType")
        if mime == "application/vnd.google-apps.folder":
            print(f"{prefix}📁 \033[1;34m{name}/\033[0m (ID: {item_id})")
            print_tree(client, folder_id=item_id, indent=indent + 1, max_depth=max_depth)
        else:
            size_kb = int(item.get("size", 0)) / 1024 if "size" in item else 0
            size_str = f" [{size_kb:.1f} KB]" if size_kb > 0 else ""
            print(f"{prefix}📄 {name}{size_str} (ID: {item_id})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Drive Manager for LDK Ops")
    subparsers = parser.add_subparsers(dest="command")

    # list command
    p_list = subparsers.add_parser("list", help="List files")
    p_list.add_argument("--parent", help="Parent folder ID (default: root)", default="root")
    p_list.add_argument("--tree", action="store_true", help="Print recursive tree")

    # mkdir command
    p_mkdir = subparsers.add_parser("mkdir", help="Create folder")
    p_mkdir.add_argument("name", help="Folder name")
    p_mkdir.add_argument("--parent", help="Parent folder ID (default: root)")

    # upload command
    p_upload = subparsers.add_parser("upload", help="Upload a file")
    p_upload.add_argument("path", help="Local file path")
    p_upload.add_argument("--name", help="Target file name")
    p_upload.add_argument("--parent", help="Target folder ID")

    # sync command
    p_sync = subparsers.add_parser("sync", help="Sync local directory recursively to Drive")
    p_sync.add_argument("dir", help="Local directory path")
    p_sync.add_argument("--parent", help="Target parent folder ID (default: root)")

    # search command
    p_search = subparsers.add_parser("search", help="Search files by name")
    p_search.add_argument("query", help="Search substring or name")

    args = parser.parse_args()

    try:
        client = GoogleDriveClient()
    except Exception as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    if args.command == "list":
        if args.tree:
            print("🗂️ Google Drive Hierarchy:")
            print_tree(client, folder_id=args.parent)
        else:
            files = client.list_files(parent_id=args.parent)
            for f in files:
                icon = "📁" if f.get("mimeType") == "application/vnd.google-apps.folder" else "📄"
                print(f"{icon} {f.get('name')} (ID: {f.get('id')})")
    elif args.command == "mkdir":
        res = client.get_or_create_folder(args.name, parent_id=args.parent)
        print(f"✅ Folder ready: '{res.get('name')}' (ID: {res.get('id')})")
    elif args.command == "upload":
        res = client.upload_file(Path(args.path), name=args.name, parent_id=args.parent)
        print(f"✅ File uploaded: '{res.get('name')}' (ID: {res.get('id')})")
    elif args.command == "sync":
        print(f"🔄 Syncing {args.dir} to Google Drive...")
        res = client.upload_directory(Path(args.dir), parent_id=args.parent)
        print(f"✅ Sync complete: '{res.get('name')}' (ID: {res.get('id')})")
    elif args.command == "search":
        q = f"name contains '{args.query}' and trashed = false"
        files = client.list_files(query=q)
        print(f"🔍 Found {len(files)} matches for '{args.query}':")
        for f in files:
            icon = "📁" if f.get("mimeType") == "application/vnd.google-apps.folder" else "📄"
            print(f"{icon} {f.get('name')} (ID: {f.get('id')})")
    else:
        parser.print_help()
