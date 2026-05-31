import json

import logging

import re



from langchain_core.messages import HumanMessage, SystemMessage

from langchain_openai import ChatOpenAI

from langgraph.graph import END, START, StateGraph



from config.config import AgentConfig
from server.agent import ChatModel
from server.route_graph.music_route import run_music_react
from server.state import AgentState
from utils.path_tools import get_abs_path
from utils.trace_log import log_event, record_model

_DEFAULT_HISTORY_LIMIT = AgentConfig().history_limit

logger = logging.getLogger(__name__)



_VALID_INTENTS = frozenset({"chat", "music", "add_son", "commit_user"})

# 用户原文命中则强制 music（模型误判 chat 时的兜底，不依赖历史）
_MUSIC_QUESTION_SIGNALS = (
    "听歌报告",
    "听歌排行",
    "听歌情况",
    "听歌情绪",
    "听歌习惯",
    "听歌数据",
    "听歌记录",
    "最近听了",
    "最近听",
    "听了什么",
    "播放记录",
    "播放次数",
    "播放排行",
    "加歌",
    "添加歌曲",
    "添加音乐",
    "歌曲背景",
    "制作背景",
    "创作背景",
    "qq音乐",
    "qq 音乐",
)

_MUSIC_QUERY_WORDS = ("查询", "查一下", "看看", "统计", "分析", "报告", "数据", "记录", "排行")
_MUSIC_TOPIC_WORDS = ("听歌", "歌曲", "音乐", "播放")


def intent_from_question(question: str) -> str | None:
    """从用户当前问题推断意图；仅做 music 等强信号兜底。"""
    q = (question or "").strip()
    if not q:
        return None
    lower = q.lower()
    if "y.qq.com" in lower or "songid" in lower:
        return "music"
    if any(signal in q for signal in _MUSIC_QUESTION_SIGNALS):
        return "music"
    if any(k in q for k in _MUSIC_TOPIC_WORDS) and any(
        k in q for k in ("分析", "报告", "排行", "记录", "数据", "统计", "背景", "情绪", "循环")
    ):
        return "music"
    if any(k in q for k in _MUSIC_QUERY_WORDS) and any(k in q for k in _MUSIC_TOPIC_WORDS):
        return "music"
    if "笔记" in q and any(k in q for k in ("发布", "写了", "刚发", "我的笔记")):
        return "commit_user"
    return None


def resolve_intent(question: str, raw: str) -> tuple[str, str | None]:
    """模型输出 + 用户原文规则；不一致时以原文强信号为准。"""
    model_intent = normalize_intent(raw)
    question_intent = intent_from_question(question)
    if question_intent and question_intent != model_intent:
        return question_intent, f"question_keyword→{question_intent}"
    return model_intent, None





def normalize_intent(raw: str) -> str:

    """解析 judge 输出为意图标识。"""

    text = (raw or "").strip()

    if not text:

        return "chat"



    try:

        data = json.loads(text)

        if isinstance(data, dict):

            route = (data.get("route") or data.get("intent") or "").strip().lower()

            if route == "comment_user":

                route = "commit_user"

            if route == "add_son":

                route = "music"

            if route in _VALID_INTENTS:

                return "music" if route == "add_son" else route

    except json.JSONDecodeError:

        pass



    lowered = text.lower()

    if "add_son" in lowered or "songid" in lowered or "y.qq.com" in lowered:

        return "music"

    if "music" in lowered or "听歌" in text or "歌曲" in text or "音乐" in text:

        return "music"

    if "commit_user" in lowered or "笔记" in text:

        return "commit_user"

    if "chat" in lowered:

        return "chat"



    m = re.search(r'"route"\s*:\s*"(\w+)"', text, re.I)

    if m:

        route = m.group(1).lower()

        if route == "add_son":

            return "music"

        if route in _VALID_INTENTS:

            return "music" if route == "add_son" else route



    return "chat"





class AgentLangGraph:

    def __init__(self):

        cfg = AgentConfig()

        self.chat_model = ChatModel()

        self.judge_model_name = cfg.judge_model_name

        self.judge_model = ChatOpenAI(

            model=cfg.judge_model_name,

            base_url=cfg.judge_base_url,

            temperature=cfg.judge_temperature,

            api_key=cfg.judge_api_key,

            timeout=90,

            max_retries=1,

        )

        self.execute_model_name = cfg.judge_model_name

        self.execute_model = self.judge_model

        self.router_graph = self.compile_router_graph()

        self.graph = self.compile_graph()



    def classify_intent(self, state: AgentState) -> str:

        """仅跑意图识别子图（供 HTTP 入口分流，闲聊不在此图内流式输出）。"""

        result = self.router_graph.invoke(state)

        return normalize_intent(result.get("intent") or result.get("route") or "chat")



    def judge_route(self, state: AgentState) -> dict:

        """判断路由：小模型 + judge_prompt，输出结构化 intent。"""

        judge_prompt_path = get_abs_path("prompt/judge_prompt")

        with open(judge_prompt_path, "r", encoding="utf-8") as f:

            judge_prompt = f.read()



        messages = [

            SystemMessage(content=judge_prompt),

            HumanMessage(content=state.get("question") or ""),

        ]

        record_model(self.judge_model_name)

        question = state.get("question") or ""
        try:
            resp = self.execute_model.invoke(messages)
            raw = resp.content.strip() if resp.content else ""
        except Exception as exc:
            logger.warning("[agent] judge_route api failed: %s", exc)
            intent = intent_from_question(question) or "chat"
            log_event(
                "intent.fallback",
                reason="judge_api_failed",
                intent=intent,
                error=str(exc)[:200],
                question_preview=question[:120],
            )
            return {"route": intent, "intent": intent}

        intent, override = resolve_intent(question, raw)
        if override:
            log_event(
                "intent.override",
                model_route=normalize_intent(raw),
                intent=intent,
                reason=override,
                question_preview=(state.get("question") or "")[:120],
            )

        return {"route": intent, "intent": intent}



    def pick_route(self, state: AgentState) -> str:

        intent = normalize_intent(state.get("intent") or state.get("route") or "chat")

        if intent in _VALID_INTENTS:

            return "music" if intent == "add_son" else intent

        return "chat"



    def compile_router_graph(self):

        """仅意图识别：START → judge → END（接入 Agent 入口用此图）。"""

        g = StateGraph(AgentState)

        g.add_node("judge_route", self.judge_route)

        g.add_edge(START, "judge_route")

        g.add_edge("judge_route", END)



        return g.compile()



    def compile_graph(self):

        """完整图：judge 后 music 走子 ReAct，chat 走闲聊节点（自测用）。"""

        g = StateGraph(AgentState)

        g.add_node("judge_route", self.judge_route)

        g.add_node("chat", self.chat)

        g.add_node("music", self.music)



        g.add_edge(START, "judge_route")

        g.add_conditional_edges(

            "judge_route",

            self.pick_route,

            {

                "chat": "chat",

                "music": "music",

                "commit_user": END,

            },

        )

        g.add_edge("chat", END)

        g.add_edge("music", END)

        return g.compile()



    def music(self, state: AgentState) -> dict:

        return run_music_react(state)



    def chat(self, state: AgentState) -> dict:

        """闲聊节点：消费流式结果写入 final_answer（供 graph.invoke 测试，非线上 SSE）。"""

        question = state.get("question") or ""

        session_id = state.get("session_id") or ""

        user_id = state.get("user_id") or 0

        limit = state.get("limit") or _DEFAULT_HISTORY_LIMIT



        parts: list[str] = []

        for chunk in self.chat_model.chat(

            question=question,

            session_id=session_id,

            user_id=user_id,

            limit=limit,

        ):

            if chunk.get("type") == "delta":

                content = chunk.get("content")

                if content:

                    parts.append(str(content))

                continue

            if chunk.get("code"):

                message = str(chunk.get("message") or "模型调用失败")

                return {"final_answer": message}



        return {"final_answer": "".join(parts).strip()}





if __name__ == "__main__":

    state: AgentState = {

        "question": "我想添加歌曲",

        "session_id": "test-session",

        "user_id": 1,

        "limit": _DEFAULT_HISTORY_LIMIT,

    }

    agent = AgentLangGraph()

    intent = agent.classify_intent(state)

    print("识别意图：", intent)



    result_state = agent.graph.invoke(state)

    print("完整返回状态：", result_state)

    print("final_answer：", result_state.get("final_answer", ""))


