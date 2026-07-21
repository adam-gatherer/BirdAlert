from pathlib import Path
import shutil
import subprocess
import zipfile
import sys

ROOT = Path(__file__).resolve().parent.parent

SOURCE = ROOT / "src" / "poller"

BUILD = ROOT / "build"

PACKAGE_DIR = BUILD / "poller"

ZIP_FILE = BUILD / "poller.zip"


def main():

    # Clear existing package dir if exists for clean start
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)

    # temp package dir.
    PACKAGE_DIR.mkdir(parents=True)

    BUILD.mkdir(exist_ok=True)

    # install python requirements directly into package dir, Lambda expects
    # code and dependencies in deployment .zip
    subprocess.run(
        [
            "pip",
            "install",
            "-r",
            str(SOURCE / "requirements.txt"),
            "-t",
            str(PACKAGE_DIR),
        ],
        check=True,
    )

    shutil.copy(
        SOURCE / "app.py",
        PACKAGE_DIR / "app.py",
    )

    if ZIP_FILE.exists():
        ZIP_FILE.unlink()

    # build deployment package
    with zipfile.ZipFile(ZIP_FILE, "w", zipfile.ZIP_DEFLATED) as archive:

        for file in PACKAGE_DIR.rglob("*"):

            if file.is_file():
                archive.write(
                    file,
                    file.relative_to(PACKAGE_DIR),
                )

    # delete temp package dir., no longer needed after build
    shutil.rmtree(PACKAGE_DIR)

    print(f"Created {ZIP_FILE}")


if __name__ == "__main__":
    main()