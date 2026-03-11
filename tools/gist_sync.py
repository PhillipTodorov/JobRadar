"""Sync user data to/from a private GitHub Gist.

Uses the GitHub REST API directly. Syncs all config and data files
so the user's profile, jobs, and tracker stay in sync across machines.

Requires in .env:
    GITHUB_GIST_TOKEN=ghp_xxxxx  (personal access token with 'gist' scope)
    GITHUB_GIST_ID=abc123        (auto-set after first push)

Usage:
    python gist_sync.py push
    python gist_sync.py pull
    python gist_sync.py status
"""

import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv, set_key

PROJECT_ROOT = Path(__file__).parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
TMP_DIR = PROJECT_ROOT / ".tmp"

# Files to sync — same set as backup_restore.py
SYNC_FILES = [
    # Config files (root)
    ("user_profile.yaml", PROJECT_ROOT / "user_profile.yaml"),
    ("job_search_config.yaml", PROJECT_ROOT / "job_search_config.yaml"),
    ("qa_databank.yaml", PROJECT_ROOT / "qa_databank.yaml"),
    ("github_projects.yaml", PROJECT_ROOT / "github_projects.yaml"),
    # Data files (.tmp/)
    ("scored_jobs.json", TMP_DIR / "scored_jobs.json"),
    ("application_tracker.json", TMP_DIR / "application_tracker.json"),
    ("hidden_jobs.json", TMP_DIR / "hidden_jobs.json"),
    ("company_reports.json", TMP_DIR / "company_reports.json"),
    ("session_state.json", TMP_DIR / "session_state.json"),
    ("cv_extracted.json", TMP_DIR / "cv_extracted.json"),
    ("cv_text.json", TMP_DIR / "cv_text.json"),
]

GIST_DESCRIPTION = "JobRadar Sync (auto-managed)"
API_BASE = "https://api.github.com"
METADATA_FILE = "_sync_metadata.json"


def _get_token():
    """Load GitHub token from .env. Returns empty string if not set."""
    load_dotenv(ENV_PATH, override=True)
    return os.getenv("GITHUB_GIST_TOKEN", "")


def _get_gist_id():
    """Load gist ID from .env, or None if not yet created."""
    load_dotenv(ENV_PATH, override=True)
    return os.getenv("GITHUB_GIST_ID") or None


def _save_gist_id(gist_id):
    """Persist gist ID to .env file."""
    set_key(str(ENV_PATH), "GITHUB_GIST_ID", gist_id)


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _read_local_files():
    """Read all sync files that exist locally. Returns {name: content}."""
    files = {}
    for name, path in SYNC_FILES:
        if path.exists():
            try:
                files[name] = path.read_text(encoding="utf-8")
            except Exception:
                pass
    return files


def _build_metadata():
    """Build sync metadata dict."""
    return {
        "synced_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "machine": platform.node(),
        "platform": platform.system(),
    }


def push():
    """Push local files to GitHub Gist.

    Creates a new gist if GITHUB_GIST_ID is not set,
    otherwise updates the existing gist.

    Returns: {success, gist_url, gist_id, files_pushed, error}
    """
    token = _get_token()
    if not token:
        return {"success": False, "error": "GITHUB_GIST_TOKEN not set in .env"}

    local_files = _read_local_files()
    if not local_files:
        return {"success": False, "error": "No data files found to sync"}

    # Add metadata
    local_files[METADATA_FILE] = json.dumps(_build_metadata(), indent=2)

    # Format for GitHub API
    gist_files = {name: {"content": content} for name, content in local_files.items()}

    gist_id = _get_gist_id()

    try:
        if gist_id:
            resp = requests.patch(
                f"{API_BASE}/gists/{gist_id}",
                headers=_headers(token),
                json={"files": gist_files, "description": GIST_DESCRIPTION},
                timeout=30,
            )
        else:
            resp = requests.post(
                f"{API_BASE}/gists",
                headers=_headers(token),
                json={
                    "description": GIST_DESCRIPTION,
                    "public": False,
                    "files": gist_files,
                },
                timeout=30,
            )
    except requests.RequestException as e:
        return {"success": False, "error": f"Network error: {e}"}

    if resp.status_code in (200, 201):
        data = resp.json()
        new_gist_id = data["id"]
        if new_gist_id != gist_id:
            _save_gist_id(new_gist_id)
        return {
            "success": True,
            "gist_url": data["html_url"],
            "gist_id": new_gist_id,
            "files_pushed": [n for n in local_files if n != METADATA_FILE],
            "error": None,
        }
    elif resp.status_code == 404 and gist_id:
        # Gist was deleted — clear ID and retry as create
        _save_gist_id("")
        return push()
    else:
        return {
            "success": False,
            "error": f"GitHub API {resp.status_code}: {resp.text[:300]}",
        }


def pull():
    """Pull files from GitHub Gist to local filesystem.

    Returns: {success, files_pulled, remote_meta, error}
    """
    token = _get_token()
    if not token:
        return {"success": False, "error": "GITHUB_GIST_TOKEN not set in .env"}

    gist_id = _get_gist_id()
    if not gist_id:
        return {"success": False, "error": "No GITHUB_GIST_ID set. Push first to create a gist."}

    try:
        resp = requests.get(
            f"{API_BASE}/gists/{gist_id}",
            headers=_headers(token),
            timeout=30,
        )
    except requests.RequestException as e:
        return {"success": False, "error": f"Network error: {e}"}

    if resp.status_code == 404:
        return {"success": False, "error": "Gist not found. It may have been deleted."}
    if resp.status_code != 200:
        return {"success": False, "error": f"GitHub API {resp.status_code}: {resp.text[:300]}"}

    gist_files = resp.json().get("files", {})

    # Extract metadata
    remote_meta = None
    if METADATA_FILE in gist_files:
        try:
            remote_meta = json.loads(gist_files[METADATA_FILE]["content"])
        except (json.JSONDecodeError, KeyError):
            pass

    # Write recognized files
    allowed = {name for name, _ in SYNC_FILES}
    pulled = []

    TMP_DIR.mkdir(exist_ok=True)

    for name, path in SYNC_FILES:
        if name in gist_files:
            try:
                content = gist_files[name]["content"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                pulled.append(name)
            except Exception:
                pass

    return {
        "success": True,
        "files_pulled": pulled,
        "remote_meta": remote_meta,
        "error": None,
    }


def get_sync_status():
    """Check current sync state without modifying anything.

    Returns: {configured, gist_id, gist_url, remote_meta, local_files}
    """
    token = _get_token()
    gist_id = _get_gist_id()
    local_files = [name for name, path in SYNC_FILES if path.exists()]

    result = {
        "configured": bool(token),
        "gist_id": gist_id,
        "gist_url": f"https://gist.github.com/{gist_id}" if gist_id else None,
        "remote_meta": None,
        "local_files": local_files,
    }

    if token and gist_id:
        try:
            resp = requests.get(
                f"{API_BASE}/gists/{gist_id}",
                headers=_headers(token),
                timeout=10,
            )
            if resp.status_code == 200:
                gist_files = resp.json().get("files", {})
                if METADATA_FILE in gist_files:
                    result["remote_meta"] = json.loads(
                        gist_files[METADATA_FILE]["content"]
                    )
        except Exception:
            pass

    return result


def auto_push():
    """Silent push for use after save operations. Never raises."""
    try:
        token = _get_token()
        if not token:
            return
        gist_id = _get_gist_id()
        if not gist_id:
            return
        push()
    except Exception:
        pass


def auto_pull_if_newer():
    """Pull from gist if remote is newer than local metadata.

    Returns True if a pull was performed, False otherwise.
    """
    try:
        token = _get_token()
        if not token:
            return False
        gist_id = _get_gist_id()
        if not gist_id:
            return False

        # Check remote metadata
        resp = requests.get(
            f"{API_BASE}/gists/{gist_id}",
            headers=_headers(token),
            timeout=10,
        )
        if resp.status_code != 200:
            return False

        gist_files = resp.json().get("files", {})
        if METADATA_FILE not in gist_files:
            return False

        remote_meta = json.loads(gist_files[METADATA_FILE]["content"])
        remote_time = remote_meta.get("synced_at", "")
        remote_machine = remote_meta.get("machine", "")

        # If pushed from this same machine, no need to pull
        if remote_machine == platform.node():
            return False

        # Check local metadata file
        local_meta_path = TMP_DIR / "_sync_metadata.json"
        if local_meta_path.exists():
            try:
                local_meta = json.loads(local_meta_path.read_text(encoding="utf-8"))
                local_time = local_meta.get("synced_at", "")
                if local_time >= remote_time:
                    return False
            except Exception:
                pass

        # Remote is newer and from different machine — pull
        result = pull()
        if result["success"]:
            # Save local metadata so we don't pull again this session
            TMP_DIR.mkdir(exist_ok=True)
            local_meta_path.write_text(
                json.dumps(_build_metadata(), indent=2), encoding="utf-8"
            )
            return True
        return False
    except Exception:
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python gist_sync.py push|pull|status")
        sys.exit(1)

    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1].lower()

    if cmd == "push":
        result = push()
        if result["success"]:
            print(f"Pushed {len(result['files_pushed'])} files to gist.")
            print(f"URL: {result['gist_url']}")
            for f in result["files_pushed"]:
                print(f"  - {f}")
        else:
            print(f"Error: {result['error']}")
            sys.exit(1)

    elif cmd == "pull":
        result = pull()
        if result["success"]:
            print(f"Pulled {len(result['files_pulled'])} files.")
            for f in result["files_pulled"]:
                print(f"  - {f}")
            if result["remote_meta"]:
                m = result["remote_meta"]
                print(f"Last pushed: {m.get('synced_at', '?')} from {m.get('machine', '?')}")
        else:
            print(f"Error: {result['error']}")
            sys.exit(1)

    elif cmd == "status":
        status = get_sync_status()
        print(f"Configured: {status['configured']}")
        print(f"Gist ID: {status['gist_id'] or 'Not set'}")
        print(f"Local files: {len(status['local_files'])}")
        if status["remote_meta"]:
            m = status["remote_meta"]
            print(f"Last pushed: {m.get('synced_at', '?')} from {m.get('machine', '?')}")
        else:
            print("Remote: No sync data found")

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
