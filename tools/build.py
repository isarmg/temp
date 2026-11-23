#!/usr/bin/env python3
"""Build the editable handout and export its PDF with LibreOffice."""

import argparse
import json
import subprocess
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile


PROJECT = Path(__file__).resolve().parent.parent
SOURCE = PROJECT / "source" / "docx"
ORDER = PROJECT / "source" / "docx-order.json"
BASENAME = "xidian-821-reviewed"
REQUIRED_PARTS = {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}
EXPORT_TIMEOUT = 180


class BuildError(Exception):
    """A build could not produce a usable artifact."""


def load_parts():
    if not SOURCE.is_dir() or SOURCE.is_symlink():
        raise BuildError(f"Missing regular source directory {SOURCE}")
    names = json.loads(ORDER.read_text(encoding="utf-8"))
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        raise BuildError(f"{ORDER} must contain an array of OPC part names")

    parts = {}
    for name in names:
        path = PurePosixPath(name)
        if (
            not path.parts
            or path.is_absolute()
            or path.as_posix() != name
            or ".." in path.parts
            or "\\" in name
            or "\0" in name
            or any(":" in segment for segment in path.parts)
        ):
            raise BuildError(f"Invalid OPC part name {name!r} in {ORDER}")
        if name in parts:
            raise BuildError(f"Duplicate OPC part {name!r} in {ORDER}")
        parts[name] = SOURCE.joinpath(*path.parts)

    missing_required = REQUIRED_PARTS - parts.keys()
    if missing_required:
        raise BuildError(f"Required OPC parts are missing: {', '.join(sorted(missing_required))}")

    files = set()
    for path in SOURCE.rglob("*"):
        if path.is_symlink():
            raise BuildError(f"OPC source must not contain a symbolic link: {path}")
        if path.is_file():
            files.add(path.relative_to(SOURCE).as_posix())
        elif not path.is_dir():
            raise BuildError(f"Unsupported OPC source entry: {path}")
    missing = sorted(parts.keys() - files)
    extra = sorted(files - parts.keys())
    if missing or extra:
        details = [f"missing files: {', '.join(missing)}"] if missing else []
        if extra:
            details.append(f"unlisted files: {', '.join(extra)}")
        raise BuildError(f"OPC source does not match {ORDER} ({', '.join(details)})")
    return parts


def export_pdf(word, pdf, executable):
    profile = word.parent / "lo-profile"
    command = [
        executable,
        f"-env:UserInstallation={profile.as_uri()}",
        "--headless",
        "--convert-to",
        "pdf:writer_pdf_Export",
        "--outdir",
        str(pdf.parent),
        str(word),
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, errors="replace", timeout=EXPORT_TIMEOUT
        )
    except FileNotFoundError as exc:
        raise BuildError(
            f"LibreOffice executable {executable!r} was not found. Use --soffice or --word-only."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise BuildError(f"LibreOffice export exceeded {EXPORT_TIMEOUT} seconds") from exc

    details = "\n".join(message.strip() for message in (result.stdout, result.stderr) if message.strip())
    if result.returncode or not pdf.is_file():
        raise BuildError(f"LibreOffice did not export a new PDF (exit {result.returncode}).\n{details}".rstrip())

    with pdf.open("rb") as stream:
        header = stream.read(5)
        stream.seek(max(0, pdf.stat().st_size - 1024))
        trailer = stream.read()
    if header != b"%PDF-" or b"%%EOF" not in trailer:
        raise BuildError(f"LibreOffice created an empty or incomplete PDF.\n{details}".rstrip())


def build(output_dir, word_only, executable):
    parts = load_parts()
    output_dir.mkdir(parents=True, exist_ok=True)
    word = output_dir / f"{BASENAME}.docx"
    pdf = output_dir / f"{BASENAME}.pdf"
    destinations = (word,) if word_only else (word, pdf)
    for destination in destinations:
        if destination.is_dir():
            raise BuildError(f"Output path is a directory: {destination}")

    # Work in a fresh directory on the destination filesystem. A failed
    # export cannot be mistaken for an existing PDF from another build.
    with TemporaryDirectory(prefix=".handout-build-", dir=output_dir) as directory:
        stage = Path(directory)
        staged_word = stage / word.name
        staged_pdf = stage / pdf.name
        with ZipFile(staged_word, "w", compression=ZIP_DEFLATED) as package:
            for name, path in parts.items():
                package.writestr(name, path.read_bytes())
        if not word_only:
            export_pdf(staged_word, staged_pdf, executable)

        staged_word.replace(word)
        print(f"Built {word}")
        if not word_only:
            staged_pdf.replace(pdf)
            print(f"Built {pdf}")
        elif pdf.exists():
            print(f"Word-only build left the existing PDF untouched at {pdf}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=PROJECT / "dist",
                        help="destination directory, relative to the project root unless absolute")
    parser.add_argument("--word-only", action="store_true", help="skip the LibreOffice PDF export")
    parser.add_argument("--soffice", default="soffice",
                        help="LibreOffice executable name on PATH or path relative to the project root")
    options = parser.parse_args()
    output_dir = (PROJECT / options.output_dir).resolve()
    executable = options.soffice
    if "/" in executable or "\\" in executable:
        executable = str((PROJECT / executable).resolve())
    try:
        build(output_dir, options.word_only, executable)
    except (BuildError, OSError, ValueError) as exc:
        parser.exit(1, f"Build failed: {exc}\n")


if __name__ == "__main__":
    main()
