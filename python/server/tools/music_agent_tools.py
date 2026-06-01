"""音乐 Agent 的 LangChain 工具（供 music 子 ReAct 使用）。"""

from __future__ import annotations

import json
import logging
import re

from langchain_core.tools import tool

from utils.qq import qq_music_tools as qq
from utils.sogou_mcp_search import search_song_background_story_sync
from utils.trace_log import log_event, preview

_QQ_URL_RE = re.compile(r"(y\.qq\.com|i\.qq\.com)", re.I)

_ANALYTICS_KEYWORDS = (
    "背景",
    "轶事",
    "创作",
    "灵感",
    "故事",
    "简报",
    "情绪",
    "听了什么",
    "听了啥",
    "排行",
    "播放次数",
    "报告",
    "最近听",
    "本周",
    "听歌数据",
)

_ADD_KEYWORDS = (
    "添加",
    "加歌",
    "加一首",
    "保存",
    "收录",
    "放进",
    "加入歌单",
    "导入",
)


def detect_music_task_mode(question: str) -> str:
    """根据用户问题收窄可用工具：add | analytics | general。"""
    q = (question or "").strip()
    if not q:
        return "general"
    lower = q.lower()
    has_qq_url = bool(_QQ_URL_RE.search(q))
    wants_analytics = any(k in q for k in _ANALYTICS_KEYWORDS)
    wants_add = any(k in q for k in _ADD_KEYWORDS) or has_qq_url

    if wants_analytics:
        return "analytics"
    if wants_add and not wants_analytics:
        return "add"
    return "general"


@tool
def parse_qq_share_url(share_url: str) -> str:
    """从 QQ 音乐分享链接解析 songid 及歌名歌手（供后续保存校验）。
    支持 i.y.qq.com 网页链接与 c6.y.qq.com 客户端短链。"""
    result = qq.parse_qq_share_with_meta(share_url)
    return json.dumps(result, ensure_ascii=False)


@tool
def fetch_qq_track_metadata(song_id: int) -> str:
    """根据 QQ songid 拉取歌名、歌手、时长等元数据；通常在 parse_qq_share_url 之后调用。"""
    meta = qq.get_track_by_song_id(song_id)
    return json.dumps(meta, ensure_ascii=False)


@tool
def search_song_story_on_web(title: str, artist: str = "") -> str:
    """搜索歌曲创作背景、灵感或轶事。
    仅当用户明确询问背景、故事、灵感、听歌简报或情绪分析时调用。
    禁止在：仅添加歌曲、仅发 QQ 链接、仅说「加歌/保存」时调用。"""
    try:
        text = search_song_background_story_sync(title, artist, num_results=5)
        if not (text or "").strip():
            log_event(
                "tool.search_story.empty",
                level=logging.WARNING,
                title=preview(title, 80),
                artist=preview(artist, 80),
            )
            return json.dumps(
                {"message": "未检索到可靠背景信息", "title": title, "artist": artist},
                ensure_ascii=False,
            )
        return text
    except Exception as exc:
        log_event(
            "tool.search_story.error",
            level=logging.ERROR,
            title=preview(title, 80),
            artist=preview(artist, 80),
            error=str(exc),
        )
        return json.dumps(
            {"message": f"搜狗搜索失败：{exc}", "title": title, "artist": artist},
            ensure_ascii=False,
        )


# 不依赖登录态的工具（模型可直接调用）
MUSIC_TOOLS_PUBLIC = [
    parse_qq_share_url,
    fetch_qq_track_metadata,
    search_song_story_on_web,
]


def build_music_tools(access_token: str, *, mode: str = "general") -> list:
    """按当前用户 JWT 与任务模式生成工具列表（token 闭包注入，避免模型手填）。"""
    token = (access_token or "").strip()
    task_mode = (mode or "general").strip().lower()

    @tool
    def save_music_track_tool(
        title: str,
        artist: str,
        qq_song_id: int | str,
        duration_sec: int | None = None,
        share_url: str | None = None,
    ) -> str:
        """将曲目保存到当前登录用户的播放列表；需已解析元数据或已知歌名歌手。"""
        if not token:
            return json.dumps({"message": "未登录，无法保存"}, ensure_ascii=False)
        try:
            saved = qq.save_music_track(
                access_token=token,
                title=title,
                artist=artist,
                qq_song_id=qq_song_id,
                duration_sec=duration_sec,
                share_url=share_url,
            )
            return json.dumps(saved, ensure_ascii=False)
        except Exception as exc:
            return json.dumps(
                {"message": f"保存失败：{exc}"},
                ensure_ascii=False,
            )

    @tool
    def get_user_music_plays() -> str:
        """查询用户听歌排行（近一周，空则全量累计）。
        仅当用户明确问「听了什么/排行/数据」或会话历史中完全没有歌单时再调用；
        若用户只追问某首歌背景、情绪简报且上文已有歌名与次数，不要重复调用。"""
        if not token:
            return json.dumps({"message": "未登录"}, ensure_ascii=False)
        try:
            rows = qq.get_music_plays_with_fallback(access_token=token)
            return json.dumps(rows, ensure_ascii=False)
        except Exception as exc:
            return json.dumps(
                {"message": f"查询听歌数据失败：{exc}"},
                ensure_ascii=False,
            )

    add_chain = [
        parse_qq_share_url,
        fetch_qq_track_metadata,
        save_music_track_tool,
    ]
    if task_mode == "add":
        return add_chain

    analytics_chain = [
        parse_qq_share_url,
        fetch_qq_track_metadata,
        search_song_story_on_web,
        save_music_track_tool,
        get_user_music_plays,
    ]
    if task_mode == "analytics":
        return analytics_chain

    return [
        *MUSIC_TOOLS_PUBLIC,
        save_music_track_tool,
        get_user_music_plays,
    ]
