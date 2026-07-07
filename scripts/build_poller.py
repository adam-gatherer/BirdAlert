from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent.parent

SOURCE = ROOT / "src" / "poller"
BUILD = ROOT / "build"

ZIP_FILE = BUILD / "poller.zip"


def main():

    BUILD.mkdir(exist_ok=True)

    if ZIP_FILE.exists():
        ZIP_FILE.unlink()

    with zipfile.ZipFile(ZIP_FILE, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(
            SOURCE / "app.py",
            arcname="app.py"
        )

    print(f"Created {ZIP_FILE}")


if __name__ == "__main__":
    main()