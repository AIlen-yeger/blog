"""意图 judge：小模型 + 关键词兜底。"""

from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config.config import AgentConfig
from server.agent import ChatModel
from server.state import AgentState
from utils.path_tools import get_abs_path
from utils.trace_log import log_event, record_model

logger = logging.getLogger(__name__)

_VALID_INTENTS = frozenset({"chat", "music", "add_son", "commit_user"})

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
    """用户原文强信号（模型误判时覆盖）。"""
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


def normalize_intent(raw: str) -> str:
    """把 judge 模型输出解析成 intent。"""
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


class IntentRouter:
    def __init__(self) -> None:
        cfg = AgentConfig()
        self.chat_model = ChatModel()
        self.judge_model_name = cfg.judge_model_name
        self._judge_llm = ChatOpenAI(
            model=cfg.judge_model_name,
            base_url=cfg.judge_base_url,
            temperature=cfg.judge_temperature,
            api_key=cfg.judge_api_key,
            timeout=90,
            max_retries=1,
        )
        with open(get_abs_path("prompt/judge.md"), encoding="utf-8") as f:
            self._judge_prompt = f.read()

    def classify_intent(self, state: AgentState) -> str:
        """调 judge 小模型 → 解析 JSON → 必要时用关键词覆盖。"""
        question = (state.get("question") or "").strip()
        record_model(self.judge_model_name)

        try:
            resp = self._judge_llm.invoke(
                [
                    SystemMessage(content=self._judge_prompt),
                    HumanMessage(content=question),
                ]
            )
            raw = (resp.content or "").strip() if resp.content else ""
        except Exception as exc:
            logger.warning("[intent] judge failed: %s", exc)
            intent = intent_from_question(question) or "chat"
            log_event(
                "intent.fallback",
                reason="judge_api_failed",
                intent=intent,
                error=str(exc)[:200],
                question_preview=question[:120],
            )
            return intent

        model_intent = normalize_intent(raw)
        keyword_intent = intent_from_question(question)
        if keyword_intent and keyword_intent != model_intent:
            log_event(
                "intent.override",
                model_route=model_intent,
                intent=keyword_intent,
                reason=f"question_keyword→{keyword_intent}",
                question_preview=question[:120],
            )
            return keyword_intent

        return model_intent
