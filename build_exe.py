"""
Build script for creating JobRadar.exe
Run this to create a standalone executable.
"""
import os
import subprocess
import sys
from pathlib import Path

def main():
    print("=" * 60)
    print("Building JobRadar.exe")
    print("=" * 60)

    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("\n❌ PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller installed")

    # Get project root
    project_root = Path(__file__).parent

    # Files and folders to include
    data_files = [
        ('tools', 'tools'),
        ('chrome-extension', 'chrome-extension'),
        ('workflows', 'workflows'),
        ('*.yaml.template', '.'),
        ('CLAUDE.md', '.'),
        ('README.md', '.'),
        ('.tmp', '.tmp'),  # Empty folder for temp files
    ]

    # Build the datas argument for PyInstaller
    datas_arg = []
    for src, dst in data_files:
        if '*' in src:
            # Handle glob patterns
            import glob
            for file in glob.glob(str(project_root / src)):
                datas_arg.append(f"{file}{os.pathsep}{dst}")
        else:
            src_path = project_root / src
            if src_path.exists():
                datas_arg.append(f"{src_path}{os.pathsep}{dst}")

    # Hidden imports (modules that PyInstaller might miss)
    hidden_imports = [
        'streamlit',
        'flask',
        'flask_cors',
        'anthropic',
        'yaml',
        'dotenv',
        'gspread',
        'google.auth',
        'serpapi',
        'docx',
        'pandas',
        'requests',
    ]

    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=JobRadar",
        "--onefile",
        "--windowed",  # No console window
        "--icon=NONE",  # TODO: Add an icon later
        "--clean",
    ]

    # Add data files
    for data in datas_arg:
        cmd.extend(["--add-data", data])

    # Add hidden imports
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # Add the launcher script
    cmd.append("launcher.py")

    print("\nRunning PyInstaller...")
    print(" ".join(cmd))
    print()

    try:
        result = subprocess.run(cmd, cwd=str(project_root), check=True)
        print("\n" + "=" * 60)
        print("✅ Build successful!")
        print("=" * 60)
        print(f"\nExecutable created at: {project_root / 'dist' / 'JobRadar.exe'}")
        print("\nTo distribute:")
        print("1. Copy the entire 'dist' folder")
        print("2. Include .env.template for users to configure")
        print("3. Include README.md with setup instructions")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
