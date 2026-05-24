import json
from typing import Iterator

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter()
_llm_agent = None


class ChatRequest(BaseModel):
    limit: int = Field(default=5, ge=1, le=50)
    session_id: str
    question: str
    account: str = ""
    user_name: str = ""
    user_id: int = 0


def get_agent_service():
    global _llm_agent
    if _llm_agent is None:
        from server.agent import ChatModel

        _llm_agent = ChatModel()
    return _llm_agent


def _sse_events(chunks: Iterator[dict]) -> Iterator[str]:
    for chunk in chunks:
        payload = json.dumps(chunk, ensure_ascii=False)
        yield f"data: {payload}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/ai/chat")
def llm_chat(body: ChatRequest):
    if not body.account or not body.user_name or not body.user_id:
        return JSONResponse(
            status_code=400,
            content={"code": 40000, "message": "用户不存在！"},
        )

    chat_llm = get_agent_service()
    stream = chat_llm.chat(
        question=body.question,
        session_id=body.session_id,
        user_id=body.user_id,
        limit=body.limit,
    )
    return StreamingResponse(_sse_events(stream), media_type="text/event-stream")
