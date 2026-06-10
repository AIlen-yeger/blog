"""IntentNode 注册表：元数据 + 执行器，单/多步共用。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from server.intent_types import OutputMode, StepResult
from server.state import AgentState

if TYPE_CHECKING:
    from server.agent import ChatModel

IntentExecutor = Callable[
    [AgentState, "ChatModel | None", str],
    StepResult,
]
GuardFn = Callable[[AgentState], bool]


@dataclass(frozen=True)
class IntentNode:
    intent: str
    description: str
    orchestratable: bool
    plan_title: str
    output_mode: OutputMode = "once"
    guard: GuardFn | None = None
    denied_message: str = ""


@dataclass
class _RegisteredIntent:
    node: IntentNode
    executor: IntentExecutor


class IntentRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, _RegisteredIntent] = {}
        self._bootstrapped = False

    @property
    def is_bootstrapped(self) -> bool:
        return self._bootstrapped

    def mark_bootstrapped(self) -> None:
        self._bootstrapped = True

    def register(self, node: IntentNode, executor: IntentExecutor) -> None:
        key = (node.intent or "").strip().lower()
        if key == "add_son":
            key = "music"
        if not key:
            raise ValueError("IntentNode.intent is required")
        self._entries[key] = _RegisteredIntent(node=node, executor=executor)

    def get(self, intent: str) -> IntentNode | None:
        entry = self._entry(intent)
        return entry.node if entry else None

    def get_output_mode(self, intent: str) -> OutputMode:
        entry = self._entry(intent)
        return entry.node.output_mode if entry else "once"

    def _entry(self, intent: str) -> _RegisteredIntent | None:
        key = (intent or "").strip().lower()
        if key == "add_son":
            key = "music"
        return self._entries.get(key)

    def orchestratable_intents(self) -> frozenset[str]:
        return frozenset(
            k for k, e in self._entries.items() if e.node.orchestratable
        )

    def all_intents(self) -> frozenset[str]:
        return frozenset(self._entries.keys())

    def plan_step_title(self, intent: str) -> str:
        node = self.get(intent)
        if node and node.plan_title:
            return node.plan_title
        return (intent or "chat").strip().lower() or "chat"

    def execute(
        self,
        intent: str,
        state: AgentState,
        *,
        chat_model: ChatModel | None = None,
        task_title: str = "",
    ) -> StepResult:
        entry = self._entry(intent)
        if not entry:
            key = (intent or "chat").strip().lower()
            return StepResult(
                ok=False,
                text=f"未知步骤：{key}",
                summary="未知任务",
            )
        node = entry.node
        if node.guard is not None and not node.guard(state):
            msg = (node.denied_message or "").strip() or "当前账号无法执行该步骤。"
            return StepResult(ok=False, text=msg, summary="无权限")
        title = (task_title or "").strip() or node.plan_title
        return entry.executor(state, chat_model, title)

    def planner_intent_line(self) -> str:
        return ", ".join(sorted(self.orchestratable_intents()))


_default_registry: IntentRegistry | None = None


def get_intent_registry() -> IntentRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = IntentRegistry()
    return _default_registry
