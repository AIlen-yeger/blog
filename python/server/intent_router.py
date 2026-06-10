"""意图 judge：小模型 + 关键词兜底。"""

from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config.config import AgentConfig, normalize_openai_base_url
from server.agent import ChatModel
from server.skills_server.skill_registry import get_registry, skill_catalog_for_judge
from server.state import AgentState
from utils.path_tools import get_abs_path
from utils.log.token_usage import record_from_response
from utils.log.trace_log import log_event, record_model

logger = logging.getLogger(__name__)


def _valid_intents() -> frozenset[str]:
    return get_registry().routable_intents

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

_AICOIN_SIGNALS = (
    "btc",
    "eth",
    "比特币",
    "纠缠之缘",
    "原石",
    "以太坊",
    "加密货币",
    "数字货币",
    "币价",
    "行情",
    "定投",
    "恐惧贪婪",
    "资金费率",
    "快讯",
    "上所",
    "大盘",
    "k线",
    "k 线",
)
_AICOIN_TOPIC_WORDS = ("币", "代币", "山寨", "合约", "现货")

_ROUTE_PRIORITY = ("publish_note", "music", "aicoin", "commit_user", "chat")


def _normalize_route_key(raw: str) -> str | None:
    key = (raw or "").strip().lower()
    if key == "add_son":
        key = "music"
    if key == "comment_user":
        key = "commit_user"
    if key in _valid_intents():
        return key
    return None


def _question_has_music(q: str, lower: str) -> bool:
    if "y.qq.com" in lower or "songid" in lower:
        return True
    if "qq.com" in lower and any(k in q for k in ("歌", "音乐", "加")):
        return True
    if any(signal in q for signal in _MUSIC_QUESTION_SIGNALS):
        return True
    if any(k in q for k in _MUSIC_TOPIC_WORDS) and any(
        k in q for k in ("分析", "报告", "排行", "记录", "数据", "统计", "背景", "情绪", "循环")
    ):
        return True
    if any(k in q for k in _MUSIC_QUERY_WORDS) and any(k in q for k in _MUSIC_TOPIC_WORDS):
        return True
    return False


def _question_has_publish_note(q: str, attachments: list | None) -> bool:
    from server.route_graph.publish_note_route import wants_publish_note

    if wants_publish_note(q, attachments or []):
        return True
    return any(
        k in q for k in ("发布笔记", "发一篇笔记", "发笔记", "上传的是笔记", "发布到博客", "发到博客")
    )


def _question_has_commit_user(q: str) -> bool:
    return "笔记" in q and any(k in q for k in ("回复", "评论", "agent回复"))


def _question_has_aicoin(q: str, lower: str) -> bool:
    if any(s in lower or s in q for s in _AICOIN_SIGNALS):
        return True
    return any(k in q for k in _AICOIN_TOPIC_WORDS) and any(
        k in q for k in ("价格", "涨跌", "新闻", "走势", "市值", "买入", "定投", "盈亏", "持仓")
    )


def routes_from_question(
    question: str,
    attachments: list | None = None,
) -> list[str]:
    """关键词收集全部命中 intent（多意图编排入口）。"""
    q = (question or "").strip()
    if not q and not attachments:
        return []

    lower = q.lower()
    found: set[str] = set()

    if _question_has_music(q, lower):
        found.add("music")
    if _question_has_publish_note(q, attachments):
        found.add("publish_note")
    if _question_has_commit_user(q):
        found.add("commit_user")
    if _question_has_aicoin(q, lower):
        found.add("aicoin")

    if not found:
        return []

    return [r for r in _ROUTE_PRIORITY if r in found]


def intent_from_question(question: str) -> str | None:
    """用户原文强信号（模型误判时覆盖）。"""
    q = (question or "").strip()
    if not q:
        return None
    lower = q.lower()
    if _question_has_music(q, lower):
        return "music"
    if _question_has_publish_note(q, None):
        return "publish_note"
    if _question_has_commit_user(q):
        return "commit_user"
    if _question_has_aicoin(q, lower):
        return "aicoin"
    return None


def parse_judge_routes(raw: str) -> list[str]:
    """解析 judge 输出：支持 routes[] 或单 route。"""
    text = (raw or "").strip()
    if not text:
        return ["chat"]

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            routes_raw = data.get("routes")
            if isinstance(routes_raw, list):
                out: list[str] = []
                for item in routes_raw:
                    key = _normalize_route_key(str(item))
                    if key and key not in out:
                        out.append(key)
                if out:
                    return out
            route = _normalize_route_key(
                str(data.get("route") or data.get("intent") or "")
            )
            if route:
                return [route]
    except json.JSONDecodeError:
        pass

    return [_normalize_intent_legacy(text)]


def normalize_intent(raw: str) -> str:
    """把 judge 模型输出解析成 intent（单路由）。"""
    routes = parse_judge_routes(raw)
    return routes[0] if routes else "chat"


def _normalize_intent_legacy(raw: str) -> str:
    """兼容旧逻辑：仅从文本片段推断单 intent。"""
    text = (raw or "").strip()
    if not text:
        return "chat"

    try:
        data = json.loads(text)
        if isinstance(data, dict) and not isinstance(data.get("routes"), list):
            route = _normalize_route_key(
                str(data.get("route") or data.get("intent") or "")
            )
            if route:
                return route
    except json.JSONDecodeError:
        pass

    lowered = text.lower()
    if "add_son" in lowered or "songid" in lowered or "y.qq.com" in lowered:
        return "music"
    if "music" in lowered or "听歌" in text or "歌曲" in text or "音乐" in text:
        return "music"
    if "publish_note" in lowered or "发布笔记" in text or "发笔记" in text:
        return "publish_note"
    if "commit_user" in lowered:
        return "commit_user"
    if "aicoin" in lowered or "行情" in text or "币价" in text:
        return "aicoin"
    if "chat" in lowered:
        return "chat"

    m = re.search(r'"route"\s*:\s*"(\w+)"', text, re.I)
    if m:
        route = _normalize_route_key(m.group(1))
        if route:
            return route

    return "chat"


class IntentRouter:
    def __init__(self) -> None:
        cfg = AgentConfig()
        self.chat_model = ChatModel()
        self.judge_model_name = cfg.judge_model_name
        judge_model = (cfg.judge_model_name or cfg.chat_model_name or "deepseek-chat").strip()
        if not judge_model:
            raise RuntimeError("未配置 judge/chat 模型名（DP_MODEL 或 DP_JUDGE_MODEL）")
        self._judge_llm = ChatOpenAI(
            model=judge_model,
            base_url=normalize_openai_base_url(cfg.judge_base_url or cfg.chat_base_url),
            temperature=cfg.judge_temperature,
            api_key=cfg.judge_api_key or cfg.chat_api_key,
            timeout=90,
            max_retries=1,
            stream_usage=True,
        )
        self._judge_prompt = self._load_judge_prompt()
        self._skill_catalog = skill_catalog_for_judge()

    @staticmethod
    def _load_judge_prompt() -> str:
        registry = get_registry()
        candidates = [
            registry.global_prompt_path("judge"),
            "skills/judge.md",
            "prompt/judge.md",
        ]
        for rel in candidates:
            if not rel:
                continue
            path = get_abs_path(rel)
            if path.is_file():
                return path.read_text(encoding="utf-8")
        raise FileNotFoundError("judge prompt not found (manifest global_prompts.judge / skills/judge.md)")

    def classify_intent(self, state: AgentState) -> str:
        """调 judge 小模型 → 解析 JSON → 必要时用关键词覆盖。"""
        question = (state.get("question") or "").strip()
        record_model(self.judge_model_name)
        human_body = question
        if self._skill_catalog:
            human_body = f"{question}\n\n{self._skill_catalog}"

        judge_messages = [
            SystemMessage(content=self._judge_prompt),
            HumanMessage(content=human_body),
        ]
        try:
            resp = self._judge_llm.invoke(judge_messages)
            record_from_response(
                phase="judge",
                model=self.judge_model_name,
                messages=judge_messages,
                response=resp,
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

        model_routes = parse_judge_routes(raw)
        model_intent = model_routes[0] if model_routes else "chat"
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
