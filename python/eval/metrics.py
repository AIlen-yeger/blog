"""Evaluation harness 指标函数。"""

from __future__ import annotations


def exact_match(actual: str, expected: str) -> tuple[float, bool, str]:
    a = (actual or "").strip()
    e = (expected or "").strip()
    ok = a == e
    return (1.0 if ok else 0.0, ok, f"actual={a!r} expected={e!r}")


def intent_match(actual: str | None, expected: str) -> tuple[float, bool, str]:
    got = (actual or "chat").strip().lower()
    want = (expected or "chat").strip().lower()
    ok = got == want
    return (1.0 if ok else 0.0, ok, f"actual={got} expected={want}")


def subset_ids(actual: list[str], expect_ids: list[str], forbid_ids: list[str] | None = None) -> tuple[float, bool, str]:
    got = set(actual or [])
    missing = [i for i in (expect_ids or []) if i not in got]
    forbidden = [i for i in (forbid_ids or []) if i in got]
    ok = not missing and not forbidden
    detail = f"actual={list(actual)} missing={missing} forbidden={forbidden}"
    return (1.0 if ok else 0.0, ok, detail)


def plan_intents_match(actual: list[str], expected: list[str]) -> tuple[float, bool, str]:
    got = [str(x).strip().lower() for x in (actual or [])]
    want = [str(x).strip().lower() for x in (expected or [])]
    ok = got == want
    return (1.0 if ok else 0.0, ok, f"actual={got} expected={want}")


def body_contains(body: str, needles: list[str]) -> tuple[float, bool, str]:
    text = body or ""
    missing = [n for n in (needles or []) if n not in text]
    ok = not missing
    return (1.0 if ok else 0.0, ok, f"missing={missing}")


def recall_hit_at_k(
    hits: list,
    *,
    expect_text_substr: str = "",
    expect_tags: list[str] | None = None,
) -> tuple[float, bool, str]:
    texts = [getattr(h, "text", "") or "" for h in hits]
    tags: list[str] = []
    for h in hits:
        tags.extend(getattr(h, "memory_tags", []) or [])

    ok = True
    detail_parts: list[str] = []
    if expect_text_substr:
        if not any(expect_text_substr in t for t in texts):
            ok = False
            detail_parts.append(f"text_substr={expect_text_substr!r} not in hits")
    if expect_tags:
        for tag in expect_tags:
            if tag not in tags:
                ok = False
                detail_parts.append(f"tag={tag!r} missing")
    if not expect_text_substr and not expect_tags:
        ok = bool(hits)
        if not ok:
            detail_parts.append("expected any hit")

    return (1.0 if ok else 0.0, ok, "; ".join(detail_parts) or f"hits={len(hits)}")
