from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import yaml

from utils.path_tools import get_abs_path


@dataclass
class LoreEntry:
    id: str
    content: str
    keys: list[str]
    priority: int = 5
    constant: bool = False
    budget_chars: int = 300
    channel: Optional[str] = None
    enabled: bool = True
    source: str = "static"
    order: int = 50
    intents: Optional[list[str]] = None
    exclude_keys: Optional[list[str]] = None
    probability: float = 1.0
    replaces_recall: bool = False
    tags: Optional[list[str]] = None
    comment: str = ""
    since_version: str = "1.0.0"


@dataclass
class Lorebook:
    budget_total_chars: int
    entries: list[LoreEntry]

    @classmethod
    def load_yaml(cls, relative_path: str) -> Lorebook:
        path = get_abs_path(relative_path)
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        entries = [
            LoreEntry(
                id=e["id"],
                content=(e.get("content") or "").strip(),
                keys=[str(k).lower() for k in (e.get("keys") or [])],
                priority=int(e.get("priority", 5)),
                constant=bool(e.get("constant", False)),
                budget_chars=int(e.get("budget_chars", 300)),
                channel=e.get("channel"),

                # 下面补齐剩余所有字段，带默认兜底
                enabled=bool(e.get("enabled", True)),
                source=str(e.get("source", "static")),
                order=int(e.get("order", 50)),
                intents=[str(x) for x in e["intents"]] if "intents" in e else None,
                exclude_keys=[str(x) for x in e["exclude_keys"]] if "exclude_keys" in e else None,
                probability=float(e.get("probability", 1.0)),
                replaces_recall=bool(e.get("replaces_recall", False)),
                comment=str(e.get("comment", "")),
                tags=[str(t) for t in e["tags"]] if "tags" in e else None,
                since_version=str(e.get("since_version", "1.0.0")),
            )
            for e in raw.get("entries", [])
        ]
        return cls(
            budget_total_chars=int(raw.get("budget_total_chars", 800)),
            entries=entries,
        )

    def _pick_entries(
        self,
        message: str,
        *,
        channel: str,
        extra_text: str = "",
    ) -> list[LoreEntry]:
        hay = f"{message}\n{extra_text}".lower()
        ch = (channel or "web").strip().lower()
        picked: list[LoreEntry] = []

        for e in self.entries:
            if not e.enabled:
                continue
            if e.channel and e.channel != ch:
                continue
            if e.constant:
                picked.append(e)
                continue
            if e.keys and any(k in hay for k in e.keys):
                picked.append(e)

        picked.sort(key=lambda x: x.priority, reverse=True)
        return picked

    def select_matched_ids(
        self,
        message: str,
        *,
        channel: str,
        extra_text: str = "",
    ) -> list[str]:
        """与 select 相同筛选逻辑，返回 entry id 列表（评测用）。"""
        return [e.id for e in self._pick_entries(message, channel=channel, extra_text=extra_text)]

    def select(
            self,
            message: str,
            *,
            channel: str,
            extra_text: str = "",
    ) -> str:
        """返回可拼进 system 的 lore 块（已截断）。"""
        picked = self._pick_entries(message, channel=channel, extra_text=extra_text)

        parts: list[str] = []
        used = 0
        for e in picked:
            chunk = e.content.strip()
            if not chunk:
                continue
            cap = min(e.budget_chars, self.budget_total_chars - used)
            if cap <= 0:
                break
            if len(chunk) > cap:
                chunk = chunk[: cap - 1] + "…"
            parts.append(chunk)
            used += len(chunk)
            if used >= self.budget_total_chars:
                break

        if not parts:
            return ""
        return "【设定补充】\n" + "\n\n".join(parts)