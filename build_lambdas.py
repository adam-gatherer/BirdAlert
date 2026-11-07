"""Build every BirdAlert Lambda deployment package."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
BUILD_SCRIPTS = (
    "build_poller.py",
    "build_processor.py",
    "build_read.py",
)


def main():
    for script_name in BUILD_SCRIPTS:
        script_path = ROOT / "scripts" / script_name
        print(f"Building {script_name.removeprefix('build_').removesuffix('.py')}...")
        subprocess.run([sys.executable, str(script_path)], check=True)

    print("All Lambda deployment packages built.")


if __name__ == "__main__":
    main()
