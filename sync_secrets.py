#!/usr/bin/env python3
"""
LDK Ops — GCP Secret Manager Synchronization Utility
Syncs local .env files with Google Cloud Secret Manager in `ldk-international`.

Usage:
    python3 sync_secrets.py --push       # Back up local .env to Secret Manager
    python3 sync_secrets.py --pull       # Restore .env from Secret Manager
    python3 sync_secrets.py --status     # Compare local .env with Secret Manager
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_PROJECT = "ldk-international"
DEFAULT_SECRET = "ldk-ops-env"
ENV_PATH = Path(__file__).resolve().parent / ".env"

def run_cmd(cmd, check=True, capture=True):
    try:
        res = subprocess.run(
            cmd,
            check=check,
            capture_output=capture,
            text=True
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout.strip() if e.stdout else "", e.stderr.strip() if e.stderr else str(e)

def secret_exists(secret_name, project):
    code, out, _ = run_cmd(["gcloud", "secrets", "describe", secret_name, f"--project={project}"], check=False)
    return code == 0

def push_secrets(secret_name, project):
    if not ENV_PATH.exists():
        print(f"❌ Error: Local file not found: {ENV_PATH}")
        sys.exit(1)

    print(f"🔒 Backing up {ENV_PATH} to Secret Manager [{secret_name}] in project [{project}]...")
    
    if not secret_exists(secret_name, project):
        print(f"Creating new secret: {secret_name}...")
        cmd = [
            "gcloud", "secrets", "create", secret_name,
            f"--data-file={ENV_PATH}",
            f"--project={project}",
            "--replication-policy=automatic"
        ]
    else:
        print(f"Adding new version to existing secret: {secret_name}...")
        cmd = [
            "gcloud", "secrets", "versions", "add", secret_name,
            f"--data-file={ENV_PATH}",
            f"--project={project}"
        ]

    code, out, err = run_cmd(cmd, check=False)
    if code != 0:
        print(f"❌ Failed to push secret: {err}")
        sys.exit(1)

    print(f"✅ Successfully pushed to Secret Manager!")
    print(out)

def pull_secrets(secret_name, project):
    print(f"📥 Pulling secret [{secret_name}] from project [{project}]...")
    
    cmd = [
        "gcloud", "secrets", "versions", "access", "latest",
        f"--secret={secret_name}",
        f"--project={project}"
    ]
    code, out, err = run_cmd(cmd, check=False)
    if code != 0:
        print(f"❌ Failed to pull secret: {err}")
        sys.exit(1)

    if ENV_PATH.exists():
        bak_path = ENV_PATH.with_suffix(".env.bak")
        ENV_PATH.replace(bak_path)
        print(f"📦 Existing .env backed up to {bak_path.name}")

    ENV_PATH.write_text(out + "\n", encoding="utf-8")
    print(f"✅ Successfully restored {ENV_PATH}")

def status_secrets(secret_name, project):
    print(f"🔍 Checking status for [{secret_name}] in project [{project}]...")
    if not secret_exists(secret_name, project):
        print(f"⚠️ Secret [{secret_name}] does NOT exist in GCP.")
        return

    # Get remote keys
    cmd = [
        "gcloud", "secrets", "versions", "access", "latest",
        f"--secret={secret_name}",
        f"--project={project}"
    ]
    code, out, err = run_cmd(cmd, check=False)
    if code != 0:
        print(f"❌ Error accessing remote secret: {err}")
        return

    remote_keys = set()
    for line in out.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            remote_keys.add(line.split("=", 1)[0].strip())

    local_keys = set()
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                local_keys.add(line.split("=", 1)[0].strip())

    print(f"\nLocal .env keys ({len(local_keys)}):")
    for k in sorted(local_keys):
        print(f"  • {k}")

    print(f"\nRemote Secret Manager keys ({len(remote_keys)}):")
    for k in sorted(remote_keys):
        print(f"  • {k}")

    missing_remote = local_keys - remote_keys
    missing_local = remote_keys - local_keys
    if missing_remote:
        print(f"\n⚠️  Keys in local .env but NOT in Secret Manager: {list(missing_remote)}")
    if missing_local:
        print(f"\n⚠️  Keys in Secret Manager but NOT in local .env: {list(missing_local)}")
    if not missing_remote and not missing_local:
        print("\n✅ Local and Remote keys are completely in sync!")

def main():
    parser = argparse.ArgumentParser(description="LDK Ops Secret Manager Sync")
    parser.add_argument("--push", action="store_true", help="Push local .env to GCP Secret Manager")
    parser.add_argument("--pull", action="store_true", help="Pull latest secret from GCP Secret Manager to local .env")
    parser.add_argument("--status", action="store_true", help="Compare local .env with Secret Manager")
    parser.add_argument("--project", default=DEFAULT_PROJECT, help=f"GCP Project ID (default: {DEFAULT_PROJECT})")
    parser.add_argument("--secret", default=DEFAULT_SECRET, help=f"Secret name (default: {DEFAULT_SECRET})")

    args = parser.parse_args()

    if args.push:
        push_secrets(args.secret, args.project)
    elif args.pull:
        pull_secrets(args.secret, args.project)
    elif args.status:
        status_secrets(args.secret, args.project)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
