"""Intent 执行层共享类型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

OutputMode = Literal["stream", "once"]


@dataclass
class StepResult:
    ok: bool
    text: str
    summary: str = ""
    preview: dict | None = None
    action: str = ""
