"""移除 Python 源文件中「几乎每行后都空一行」的无意义换行。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _is_import(line: str) -> bool:
    s = line.lstrip()
    return s.startswith("import ") or s.startswith("from ")


def _should_drop_blank(prev: str, nxt: str) -> bool:
    if not prev.strip() or not nxt.strip():
        return True

    prev_indent = _indent(prev)
    nxt_indent = _indent(nxt)
    prev_r = prev.rstrip()

    if _is_import(prev) and _is_import(nxt):
        return True

    if prev_r.endswith(":"):
        return True

    if nxt_indent > prev_indent:
        return True

    if prev_indent > 0 and nxt_indent == prev_indent:
        if nxt.lstrip().startswith(("def ", "class ", "@")):
            return False
        return True

    if prev_indent == 0 and nxt_indent == 0:
        if prev_r.endswith(('"""', "'''")):
            return False
        if nxt.lstrip().startswith(("def ", "class ", "@")):
            return False
        if prev.lstrip().startswith(("def ", "class ")):
            return False
        return True

    return False


def normalize_py(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            prev = out[-1] if out else ""
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            nxt = lines[j] if j < len(lines) else ""

            if prev.strip() and nxt.strip() and _should_drop_blank(prev, nxt):
                i += 1
                continue

            if out and out[-1].strip() == "":
                i += 1
                continue

            out.append("")
            i += 1
            continue

        out.append(line)
        i += 1

    collapsed: list[str] = []
    blank_run = 0
    for line in out:
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 2:
                collapsed.append(line)
        else:
            blank_run = 0
            collapsed.append(line)

    result = "\n".join(collapsed)
    if text.endswith("\n"):
        result += "\n"
    return result


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
    changed = 0
    for path in sorted(root.rglob("*.py")):
        if path.name == "normalize_py_spacing.py":
            continue
        raw = path.read_text(encoding="utf-8")
        fixed = normalize_py(raw)
        if fixed != raw:
            path.write_text(fixed, encoding="utf-8", newline="\n")
            changed += 1
            print(path.relative_to(root))
    print(f"updated {changed} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
