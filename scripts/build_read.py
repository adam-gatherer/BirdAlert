from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src" / "read"
BUILD = ROOT / "build"
PACKAGE_DIR = BUILD / "read"
ZIP_FILE = BUILD / "read.zip"


def main():
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)

    PACKAGE_DIR.mkdir(parents=True)
    BUILD.mkdir(exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(SOURCE / "requirements.txt"),
            "-t",
            str(PACKAGE_DIR),
        ],
        check=True,
    )
    shutil.copy(SOURCE / "app.py", PACKAGE_DIR / "app.py")

    if ZIP_FILE.exists():
        ZIP_FILE.unlink()
    with zipfile.ZipFile(ZIP_FILE, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in PACKAGE_DIR.rglob("*"):
            if file.is_file():
                archive.write(file, file.relative_to(PACKAGE_DIR))
    shutil.rmtree(PACKAGE_DIR)
    print(f"Created {ZIP_FILE}")


if __name__ == "__main__":
    main()
