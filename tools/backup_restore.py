"""Backup and restore user data for JobRadar.

Usage:
    python backup_restore.py export [output_path]
    python backup_restore.py import <backup_file>
"""

import io
import sys
import zipfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp"

# Files to include in backup (archive_name, file_path)
BACKUP_FILES = [
    # Root config files
    ("user_profile.yaml", PROJECT_ROOT / "user_profile.yaml"),
    ("job_search_config.yaml", PROJECT_ROOT / "job_search_config.yaml"),
    ("qa_databank.yaml", PROJECT_ROOT / "qa_databank.yaml"),
    ("github_projects.yaml", PROJECT_ROOT / "github_projects.yaml"),
    # User data in .tmp
    (".tmp/scored_jobs.json", TMP_DIR / "scored_jobs.json"),
    (".tmp/application_tracker.json", TMP_DIR / "application_tracker.json"),
    (".tmp/hidden_jobs.json", TMP_DIR / "hidden_jobs.json"),
    (".tmp/company_reports.json", TMP_DIR / "company_reports.json"),
    (".tmp/session_state.json", TMP_DIR / "session_state.json"),
    (".tmp/cv_extracted.json", TMP_DIR / "cv_extracted.json"),
    (".tmp/cv_text.json", TMP_DIR / "cv_text.json"),
]


def export_backup(output_path=None):
    """Export all user data to a zip file. Returns (path, included_files)."""
    if not output_path:
        timestamp = datetime.now().strftime("%Y-%m-%d")
        output_path = PROJECT_ROOT / f"jobradar_backup_{timestamp}.zip"

    output_path = Path(output_path)
    included = []

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for archive_name, file_path in BACKUP_FILES:
            if file_path.exists():
                zf.write(file_path, archive_name)
                included.append(archive_name)

    return str(output_path), included


def export_bytes():
    """Export backup as bytes (for Streamlit st.download_button)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for archive_name, file_path in BACKUP_FILES:
            if file_path.exists():
                zf.write(file_path, archive_name)
    buf.seek(0)
    return buf.getvalue()


def import_backup(backup_path):
    """Import user data from a zip file. Returns (success, detail)."""
    backup_path = Path(backup_path)
    if not backup_path.exists():
        return False, f"File not found: {backup_path}"

    TMP_DIR.mkdir(exist_ok=True)

    # Only extract files that match known backup entries
    allowed = {name for name, _ in BACKUP_FILES}
    restored = []

    with zipfile.ZipFile(backup_path, "r") as zf:
        for name in zf.namelist():
            if name not in allowed:
                continue
            target = PROJECT_ROOT / name
            target.parent.mkdir(parents=True, exist_ok=True)
            zf.extract(name, PROJECT_ROOT)
            restored.append(name)

    return True, restored


def import_bytes(data: bytes):
    """Import backup from bytes (for Streamlit st.file_uploader). Returns (success, detail)."""
    TMP_DIR.mkdir(exist_ok=True)
    allowed = {name for name, _ in BACKUP_FILES}
    restored = []

    buf = io.BytesIO(data)
    with zipfile.ZipFile(buf, "r") as zf:
        for name in zf.namelist():
            if name not in allowed:
                continue
            target = PROJECT_ROOT / name
            target.parent.mkdir(parents=True, exist_ok=True)
            zf.extract(name, PROJECT_ROOT)
            restored.append(name)

    return True, restored


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python backup_restore.py export [output_path]")
        print("  python backup_restore.py import <backup_file>")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "export":
        out = sys.argv[2] if len(sys.argv) > 2 else None
        path, files = export_backup(out)
        print(f"Backup saved to: {path}")
        print(f"Included {len(files)} files:")
        for f in files:
            print(f"  - {f}")

    elif command == "import":
        if len(sys.argv) < 3:
            print("Error: Please provide a backup file path.")
            sys.exit(1)
        ok, result = import_backup(sys.argv[2])
        if ok:
            print(f"Restored {len(result)} files:")
            for r in result:
                print(f"  - {r}")
        else:
            print(f"Error: {result}")
            sys.exit(1)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
