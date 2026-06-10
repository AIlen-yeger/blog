#!/usr/bin/env python3
"""文档解析清洗冒烟测试。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from service.document_ingest import (  # noqa: E402
    merge_parsed_documents,
    parse_text_content,
)


def test_markdown_title_and_clean() -> None:
    raw = "# 我的笔记\n\n\n段落一\n\n\n\n段落二\n"
    doc = parse_text_content(raw, filename="note.md", mime="text/markdown")
    assert doc.title == "我的笔记", doc.title
    assert "段落一" in doc.body
    assert doc.char_count == len(doc.body)
    print("markdown:", doc.title, "chars=", doc.char_count)


def test_merge_documents() -> None:
    a = parse_text_content("A part", filename="a.txt")
    b = parse_text_content("B part", filename="b.txt")
    merged = merge_parsed_documents([a, b])
    assert "A part" in merged.body and "B part" in merged.body
    print("merge:", merged.title, merged.source_filename)


if __name__ == "__main__":
    test_markdown_title_and_clean()
    test_merge_documents()
    print("ok")
