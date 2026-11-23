"""Check the A4 handout's contents page numbers and internal links."""

from argparse import ArgumentParser
from collections import defaultdict
import json
from pathlib import Path
import re
import unicodedata

import fitz


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "dist/xidian-821-reviewed.pdf"
CONTENTS = ROOT / "source/contents.json"
SECTION_TARGETS = {
    "电路基础精编辅导讲义": "电路基础",
    "信号与系统精编辅导讲义": "一、信号与系统的基本概念",
}
ENTRY = re.compile(r"(.+?)\.{4,}\s*(\d+)")
FOOTER_TOP = 804


def normalized_heading(text):
    return "".join(char for char in unicodedata.normalize("NFKC", text).lower() if char.isalnum())


def verify_footer(page):
    # Filter after extraction so cropped ActualText runs cannot join the footer.
    words = [word for word in page.get_text("words") if word[1] >= FOOTER_TOP]
    if page.number == 0:
        assert not words, ("Unexpected number on cover", words)
        return
    assert len(words) == 1 and words[0][4] == str(page.number + 1), (page.number + 1, words)
    x0, _, x1, *_ = words[0]
    assert abs(x0 + x1 - page.rect.width) <= 1, ("Footer is off-center", page.number + 1)


def verify_navigation(pdf, label_map):
    label_anchors = {
        normalized_heading(label): anchor
        for anchor, labels in label_map.items() for label in labels
    }
    assert len(label_anchors) == sum(map(len, label_map.values())), "Duplicate directory labels"
    page_numbers = defaultdict(set)
    seen = []

    with fitz.open(pdf) as book:
        outline = book.get_toc()
        assert outline[0][1] == "目录" and outline[0][2] == 2, outline[:2]
        assert outline[1][1] == "电路基础", outline[:2]
        first_body_page = outline[1][2] - 1
        assert first_body_page > 1, first_body_page + 1
        assert book[first_body_page].get_text(sort=True).lstrip().startswith("电路基础"), (
            "Missing first chapter", first_body_page + 1,
        )
        cover = book[0].get_text()
        assert "2024" in cover and "821" in cover, cover

        for page in book:
            assert abs(page.rect.width - 595.28) < 1 and abs(page.rect.height - 841.89) < 1, (
                page.number + 1, page.rect,
            )
            verify_footer(page)

        for page in book[1:first_body_page]:
            links = page.get_links()
            body = fitz.Rect(0, 0, page.rect.width, FOOTER_TOP)
            for block in page.get_text("dict", sort=True, clip=body)["blocks"]:
                if block["type"] != 0:
                    continue
                for line in block["lines"]:
                    text = "".join(span["text"] for span in line["spans"]).strip()
                    if not text or normalized_heading(text) == "目录":
                        continue
                    entry = ENTRY.fullmatch(text)
                    label = entry[1].strip() if entry else text
                    key = normalized_heading(label)
                    assert key in label_anchors, (page.number + 1, label)
                    assert entry or label in SECTION_TARGETS, ("Missing directory page number", label)
                    x0, y0, _, y1 = line["bbox"]
                    middle = (y0 + y1) / 2
                    candidates = [
                        link for link in links
                        if abs(link["from"].x0 - x0) < 8
                        and link["from"].y0 <= middle <= link["from"].y1
                    ]
                    assert len(candidates) == 1, (label, candidates)
                    link, = candidates
                    assert link["kind"] == fitz.LINK_GOTO, (label, link)
                    destination = link["page"]
                    assert first_body_page <= destination < len(book), (label, link)
                    if entry:
                        assert int(entry[2]) == destination + 1, (label, entry[2], destination + 1)

                    target = book[destination]
                    top = link["to"].y
                    target_area = fitz.Rect(0, max(0, top - 4), target.rect.width, top + 38)
                    location = normalized_heading(target.get_text(clip=target_area, sort=True))
                    expected = normalized_heading(SECTION_TARGETS.get(label, label))
                    assert expected in location, (label, destination + 1, location)
                    page_numbers[label_anchors[key]].add(destination + 1)
                    seen.append(key)

        assert seen == list(label_anchors), (len(seen), len(label_anchors), set(label_anchors) - set(seen))
        assert all(len(numbers) == 1 for numbers in page_numbers.values()), page_numbers
        print(
            f"Verified {len(seen)} directory entries on pages 2–{first_body_page}, "
            f"the first chapter on page {first_body_page + 1}, and A4 geometry throughout {len(book)} pages."
        )

    return {anchor: pages.pop() for anchor, pages in page_numbers.items()}


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("pdf", nargs="?", type=Path, default=PDF)
    options = parser.parse_args()
    labels = json.loads(CONTENTS.read_text(encoding="utf-8"))
    verify_navigation(options.pdf, labels)
