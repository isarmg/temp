"""Refresh the embedded vector and Word fallback after editing an SVG figure."""

import argparse
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"


def view_box(svg):
    return tuple(float(v) for v in ElementTree.parse(svg).getroot().attrib["viewBox"].split())


def refresh(figure, inkscape):
    mapping = json.loads((SOURCE / "figures.json").read_text(encoding="utf-8"))
    if figure not in mapping:
        raise ValueError(f"Unknown figure: {figure}")
    entry = mapping[figure]
    art = SOURCE / "drawings" / figure
    package = (SOURCE / "docx").resolve()
    vector, fallback = ((package / entry[key]).resolve() for key in ("svg", "png"))
    if not all(p.is_relative_to(package / "word/media") for p in (vector, fallback)):
        raise ValueError("Figure parts must be inside source/docx/word/media")
    old = view_box(vector)
    edited = view_box(art)
    if not old[2] * edited[3] == edited[2] * old[3]:
        raise ValueError("Keep the SVG's original width-to-height ratio for its Word placement")

    with TemporaryDirectory(prefix=".render-figure-", dir=vector.parent) as temporary:
        vector_file = Path(temporary) / vector.name
        png_file = Path(temporary) / fallback.name
        subprocess.run(
            [inkscape, str(art), "--export-text-to-path", "--export-plain-svg",
             f"--export-filename={vector_file}"],
            check=True,
        )
        subprocess.run(
            [inkscape, str(vector_file), "--export-type=png",
             f"--export-width={entry['png_width']}", f"--export-filename={png_file}"],
            check=True,
        )
        if not (vector_file.is_file() and png_file.is_file()):
            raise OSError("Inkscape did not create both figure parts")
        vector_file.replace(vector)
        png_file.replace(fallback)
    print(f"Updated {figure} in the Word source package")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("figure", help="name of an SVG in source/drawings")
    parser.add_argument("--inkscape", default="inkscape")
    args = parser.parse_args()
    try:
        refresh(args.figure, args.inkscape)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Figure export failed: {error}\n")


if __name__ == "__main__":
    main()
