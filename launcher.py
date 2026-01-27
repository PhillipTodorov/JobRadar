"""
JobRadar Launcher - Starts both Flask backend and Streamlit dashboard
"""
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
import signal

# Get the application directory
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    APP_DIR = Path(sys.executable).parent
else:
    # Running as script
    APP_DIR = Path(__file__).parent

TOOLS_DIR = APP_DIR / "tools"
FLASK_SCRIPT = TOOLS_DIR / "answer_questions_api.py"
STREAMLIT_SCRIPT = APP_DIR / "app.py"

# Process handles
flask_process = None
streamlit_process = None


def cleanup():
    """Kill all child processes on exit."""
    global flask_process, streamlit_process

    print("\nShutting down...")

    if flask_process:
        try:
            flask_process.terminate()
            flask_process.wait(timeout=3)
        except:
            if flask_process.poll() is None:
                flask_process.kill()

    if streamlit_process:
        try:
            streamlit_process.terminate()
            streamlit_process.wait(timeout=3)
        except:
            if streamlit_process.poll() is None:
                streamlit_process.kill()

    print("Shutdown complete.")


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    cleanup()
    sys.exit(0)


def main():
    global flask_process, streamlit_process

    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 60)
    print("            JobRadar - Application Assistant")
    print("=" * 60)
    print()

    # Check Python is available
    python_exe = sys.executable

    # Start Flask backend
    print("[1/2] Starting Flask Backend (http://localhost:5000)...")
    try:
        flask_process = subprocess.Popen(
            [python_exe, str(FLASK_SCRIPT)],
            cwd=str(TOOLS_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        print("      ✓ Flask started (PID: {})".format(flask_process.pid))
    except Exception as e:
        print(f"      ✗ Failed to start Flask: {e}")
        return 1

    # Wait for Flask to initialize
    time.sleep(2)

    # Start Streamlit dashboard
    print("[2/2] Starting Streamlit Dashboard (http://localhost:8501)...")
    try:
        env = os.environ.copy()
        env['STREAMLIT_CLI_TELEMETRY'] = '0'

        streamlit_process = subprocess.Popen(
            [python_exe, "-m", "streamlit", "run", str(STREAMLIT_SCRIPT),
             "--server.headless=true", "--server.port=8501"],
            cwd=str(APP_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        print("      ✓ Streamlit started (PID: {})".format(streamlit_process.pid))
    except Exception as e:
        print(f"      ✗ Failed to start Streamlit: {e}")
        cleanup()
        return 1

    # Wait for Streamlit to initialize
    time.sleep(3)

    print()
    print("=" * 60)
    print("  JobRadar is running!")
    print("=" * 60)
    print()
    print("  Dashboard: http://localhost:8501")
    print("  API:       http://localhost:5000")
    print()
    print("  Press Ctrl+C to stop all services")
    print("=" * 60)

    # Open browser automatically
    try:
        webbrowser.open("http://localhost:8501")
    except:
        pass

    # Keep running until user stops
    try:
        # Monitor processes
        while True:
            time.sleep(1)

            # Check if processes are still alive
            if flask_process.poll() is not None:
                print("\n⚠ Flask backend stopped unexpectedly!")
                break

            if streamlit_process.poll() is not None:
                print("\n⚠ Streamlit dashboard stopped unexpectedly!")
                break

    except KeyboardInterrupt:
        pass

    finally:
        cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
