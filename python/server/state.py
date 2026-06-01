from typing import TypedDict, Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages


class AgentState(TypedDict, total=False):
    session_id: str
    bug_session_id: str
    incident_id: str
    trace_id: str
    trigger: str
    source: str
    severity: str
    question: str
    final_answer: str
    history: list[dict[str, str]]
    route: str
    intent: str
    user_id: int
    limit: int
    access_token: str
    channel: str  # web | qq | internal
    messages: Annotated[list[AnyMessage], add_messages]
