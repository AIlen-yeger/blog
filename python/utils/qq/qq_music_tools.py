import httpx
import json
import logging
import re
import os
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

_DEFAULT_BLOG_API_BASE = "http://127.0.0.1:8080/v1"


def blog_api_base() -> str:
    """读取 BLOG_API_BASE，自动补全 http(s) 协议，避免 httpx UnsupportedProtocol。"""
    raw = (os.getenv("BLOG_API_BASE") or "").strip()
    if not raw:
        return _DEFAULT_BLOG_API_BASE.rstrip("/")
    if raw.startswith(("http://", "https://")):
        return raw.rstrip("/")
    normalized = f"http://{raw.lstrip('/')}".rstrip("/")
    logger.warning(
        "BLOG_API_BASE 缺少协议，已自动补全为 %s（建议在 .env 写完整 URL，如 http://127.0.0.1:8080/v1）",
        normalized,
    )
    return normalized


QQ_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://y.qq.com/",
    "Origin": "https://y.qq.com",
}

# 客户端短链重定向常用移动端 UA
_QQ_MOBILE_HEADERS = {
    **QQ_HEADERS,
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    ),
    "Referer": "https://i.y.qq.com/",
}

# 客户端分享短链，例：https://c6.y.qq.com/base/fcgi-bin/u?__=nvydylMI0n8h
_QQ_SHORT_LINK_RE = re.compile(
    r"https?://c\d*\.y\.qq\.com/base/fcgi-bin/u\?",
    re.IGNORECASE,
)

_QQ_URL_IN_TEXT = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def _normalize_share_input(raw: str) -> str:
    text = (raw or "").strip()
    match = _QQ_URL_IN_TEXT.search(text)
    return match.group(0) if match else text

_SONGID_URL_PATTERNS = (
    re.compile(r"/songDetail/(\d+)", re.IGNORECASE),
    re.compile(r"[?&]songid=(\d+)", re.IGNORECASE),
    re.compile(r"[?&]id=(\d+)", re.IGNORECASE),
)

_SONGID_BODY_PATTERNS = (
    re.compile(r'"songid"\s*:\s*"?(\d+)"?', re.IGNORECASE),
    re.compile(r"g_songid\s*=\s*'?(\d+)'?", re.IGNORECASE),
)

_SONGMID_URL_PATTERNS = (
    re.compile(r"[?&]songmid=([A-Za-z0-9]+)", re.IGNORECASE),
    re.compile(r"/song/([A-Za-z0-9]+)\.html", re.IGNORECASE),
)


def _extract_songid_from_url(url: str) -> int | None:
    """仅从 URL 提取 songid；songDetail 优先于泛化 id=。"""
    for pattern in _SONGID_URL_PATTERNS:
        match = pattern.search(url or "")
        if match:
            return int(match.group(1))
    return None


def _extract_songid_from_text(text: str) -> int | None:
    song_id = _extract_songid_from_url(text)
    if song_id is not None:
        return song_id
    for pattern in _SONGID_BODY_PATTERNS:
        match = pattern.search(text or "")
        if match:
            return int(match.group(1))
    return None


def _extract_songmid_from_url(url: str) -> str | None:
    for pattern in _SONGMID_URL_PATTERNS:
        match = pattern.search(url or "")
        if match:
            mid = match.group(1).strip()
            if mid and not mid.isdigit():
                return mid
    return None


def _is_qq_short_link(url: str) -> bool:
    return bool(_QQ_SHORT_LINK_RE.search(url or ""))


def _collect_redirect_targets(url: str, *, headers: dict | None = None) -> list[str]:
    """手动跟随重定向，收集 Location 链（客户端短链的真实目标在 Location 里）。"""
    headers = headers or _QQ_MOBILE_HEADERS
    seen: set[str] = set()
    chain: list[str] = []
    current = url.strip()
    with httpx.Client(headers=headers, timeout=15.0, follow_redirects=False) as client:
        for _ in range(8):
            if not current or current in seen:
                break
            seen.add(current)
            chain.append(current)
            try:
                resp = client.get(current)
            except httpx.HTTPError:
                break
            if resp.status_code in {301, 302, 303, 307, 308}:
                location = (resp.headers.get("Location") or "").strip()
                if not location:
                    break
                current = urljoin(str(resp.url), location)
                continue
            break
    return chain


def _songmid_to_songid(song_mid: str) -> int:
    """songmid → 数字 songid（供 GetTrackInfo 使用）。"""
    resp = httpx.get(
        "https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg",
        params={"songmid": song_mid, "format": "json", "platform": "yqq"},
        headers=QQ_HEADERS,
        timeout=15.0,
    )
    resp.raise_for_status()
    body = resp.json()
    rows = body.get("data") or []
    if not rows:
        raise RuntimeError("fcg_play_single_song 未返回曲目")
    song_id = rows[0].get("id")
    if song_id is None:
        raise RuntimeError("返回数据中缺少 id")
    return int(song_id)


def _resolve_from_url_candidates(*candidates: str) -> int | None:
    """只从 URL / Location 解析，不读 HTML（避免推荐位 mid 干扰）。"""
    for target in reversed(candidates):
        if not target:
            continue
        song_id = _extract_songid_from_url(target)
        if song_id is not None:
            return song_id
        song_mid = _extract_songmid_from_url(target)
        if song_mid:
            try:
                return _songmid_to_songid(song_mid)
            except Exception as exc:
                logger.warning("[qq] songmid=%s 转 songid 失败: %s", song_mid, exc)
    return None


def _resolve_qq_short_link(url: str) -> int | dict[str, str]:
    """解析 QQ 客户端短链：Location 链 + 最终 URL（与浏览器一致，优先桌面 UA）。"""
    last_detail = ""
    for headers in (QQ_HEADERS, _QQ_MOBILE_HEADERS):
        chain = _collect_redirect_targets(url, headers=headers)
        song_id = _resolve_from_url_candidates(*chain)
        if song_id is not None:
            logger.info("[qq] short link resolved via redirect chain -> songid=%s", song_id)
            return song_id

        try:
            resp = httpx.get(
                url,
                headers=headers,
                follow_redirects=True,
                timeout=15.0,
            )
            last_detail = str(resp.url)
            song_id = _extract_songid_from_url(str(resp.url))
            if song_id is not None:
                logger.info(
                    "[qq] short link resolved via final url %s -> songid=%s",
                    resp.url,
                    song_id,
                )
                return song_id
        except httpx.HTTPError as exc:
            last_detail = str(exc)
            continue

    return {
        "message": "短链已访问但未找到 songid",
        "hint": "请尝试在 QQ 音乐中使用「复制链接」获取含 songid 的网页链接",
        "detail": last_detail[:200] if last_detail else "",
    }


def parse_qq_music_url(url: str) -> int | dict[str, str]:
    """从 QQ 音乐分享链接中提取 songid（支持网页链接与客户端短链）。"""
    text = _normalize_share_input(url)
    if not text:
        return {"message": "链接为空"}

    song_id = _extract_songid_from_url(text) or _extract_songid_from_text(text)
    if song_id is not None:
        return song_id

    if _is_qq_short_link(text) or re.search(
        r"y\.qq\.com/base/fcgi-bin/u\?", text, re.IGNORECASE
    ):
        return _resolve_qq_short_link(text)

    return {"message": "提取失败"}


def parse_qq_share_with_meta(share_url: str) -> dict:
    """解析分享链接并拉取元数据，供 Agent 校验歌名。"""
    normalized = _normalize_share_input(share_url)
    parsed = parse_qq_music_url(normalized)
    if isinstance(parsed, dict):
        return parsed
    meta = get_track_by_song_id(parsed)
    return {
        "songId": parsed,
        "title": meta.get("title") or "",
        "artist": meta.get("artist") or "",
        "durationSec": meta.get("durationSec"),
        "album": meta.get("album") or "",
        "shareUrl": normalized,
    }


def get_track_by_song_id(song_id:int | str) -> dict:
    song_id = int(song_id)

    payload = {
        "comm": {"ct": 24, "cv": 0, "format": "json"},
        "req_0": {
            "module": "music.trackInfo.UniformRuleCtrl",
            "method": "GetTrackInfo",
            "param": {
                "ids": [song_id],
                "types": [0],
            },
        },
    }

    data_str = json.dumps(payload,separators=(",", ":"),ensure_ascii=False)
    resp = httpx.get(
        "https://u.y.qq.com/cgi-bin/musicu.fcg",
        params={"format": "json", "data": data_str},
        headers=QQ_HEADERS,
        timeout=15.0,
    )

    resp.raise_for_status()
    body = resp.json()

    req0 = body.get("req_0")
    if req0.get("code") != 0:
        raise RuntimeError(f"QQ 返回 code={req0.get('code')}")

    data = req0.get("data")
    tracks = data.get("tracks") or data.get("track_info") or []
    if not tracks:
        raise RuntimeError("tracks 为空，可能接口字段变了")

    t = tracks[0]
    singers = t.get("singer") or []
    if isinstance(singers, list):
        artist = " / ".join(
            (s.get("name") or "") if isinstance(s, dict) else str(s)
            for s in singers
        ).strip()
    else:
        artist = str(singers)

    return {
        "qqSongId": str(song_id),
        "songmid": t.get("mid") or t.get("songmid") or "",
        "title": (t.get("name") or t.get("title") or "").strip(),
        "artist": artist,
        "durationSec": t.get("interval"),  # 一般是秒
        "album": (t.get("album") or {}).get("name", "")
        if isinstance(t.get("album"), dict) else "",
    }

def save_music_track(
    *,
    access_token: str,
    title: str,
    artist: str,
    qq_song_id: int | str,
    duration_sec: int | None = None,
    share_url: str | None = None,
) -> dict:
    """保存曲目到当前用户播放列表（POST /music/tracks）。"""
    base = blog_api_base()
    save_music_url = f"{base}/music/tracks"

    payload: dict = {
        "title": title,
        "artist": artist,
        "qqSongId": str(qq_song_id),
    }
    if duration_sec is not None:
        payload["durationSec"] = duration_sec
    if share_url:
        payload["shareUrl"] = share_url

    resp = httpx.post(
        save_music_url,
        json=payload,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15.0,
    )
    try:
        body = resp.json()
    except Exception:
        body = {}

    if resp.status_code >= 400:
        msg = body.get("message") if isinstance(body, dict) else None
        return {"message": msg or resp.text or f"HTTP {resp.status_code}"}

    if body.get("code") != 0:
        return {"message": body.get("message") or "保存失败"}
    return body.get("data") or {}


def get_music_weekly_plays(*, access_token: str) -> list[dict]:
    """查询当前用户近一周播放排行（GET /agent/music/weekly-plays）。"""
    base = blog_api_base()
    url = f"{base}/agent/music/weekly-plays"
    resp = httpx.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15.0,
    )
    try:
        body = resp.json()
    except Exception:
        body = {}

    if resp.status_code >= 400:
        msg = body.get("message") if isinstance(body, dict) else None
        raise RuntimeError(msg or resp.text or f"HTTP {resp.status_code}")

    if not isinstance(body, dict) or body.get("code") != 0:
        raise RuntimeError(body.get("message") if isinstance(body, dict) else "查询失败")

    data = body.get("data")
    return data if isinstance(data, list) else []


def get_music_all_plays(*, access_token: str) -> list[dict]:
    """查询当前用户库内累计播放排行（GET /agent/music/all-plays）。

    当周 Redis 近一周数据为空时，Agent 可回退调用本接口；
    数据来自 user_music_track.play_count，按次数降序，条数由后端配置限制。
    """
    base = blog_api_base()
    url = f"{base}/agent/music/all-plays"
    resp = httpx.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15.0,
    )
    try:
        body = resp.json()
    except Exception:
        body = {}

    if resp.status_code >= 400:
        msg = body.get("message") if isinstance(body, dict) else None
        raise RuntimeError(msg or resp.text or f"HTTP {resp.status_code}")

    if not isinstance(body, dict) or body.get("code") != 0:
        raise RuntimeError(body.get("message") if isinstance(body, dict) else "查询失败")

    data = body.get("data")
    return data if isinstance(data, list) else []


def get_music_plays_with_fallback(*, access_token: str) -> list[dict]:
    """优先近一周排行；为空时回退为库内累计排行。"""
    weekly = get_music_weekly_plays(access_token=access_token)
    if weekly:
        return weekly
    return get_music_all_plays(access_token=access_token)





