"""Convenient launcher for the Natural Language to SQL Query Interface."""

import sys
import subprocess
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent
    app_script = root / "app.py"
    
    print("=" * 60)
    print("Starting Natural Language to SQL Query Interface")
    print(f"App Script: {app_script}")
    print("=" * 60)
    
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_script)]
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
