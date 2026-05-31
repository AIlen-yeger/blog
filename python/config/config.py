"""Agent 配置：统一从 python/.env 读取（启动时自动 load_dotenv）。"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_ENV_LOADED = False
_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def env_file_path() -> Path:
    return _ENV_PATH


def ensure_env_loaded() -> None:
    """加载 python/.env；重复调用安全。"""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    try:
        from dotenv import load_dotenv

        if _ENV_PATH.is_file():
            load_dotenv(_ENV_PATH, override=True)
        else:
            logger.warning(
                "[config] 未找到 %s — 请执行: copy .env.example .env 并填写密钥",
                _ENV_PATH,
            )
    except ImportError:
        logger.warning("[config] 未安装 python-dotenv，无法加载 .env")
    _ENV_LOADED = True


def _read_env(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _env_str(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None or not str(value).strip():
        return default
    return str(value).strip()


def _env_int(name: str, default: int) -> int:
    raw = _read_env(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = _read_env(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = _read_env(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


ensure_env_loaded()


class AgentConfig:
    def __init__(self) -> None:
        ensure_env_loaded()

        # ── 闲聊（DeepSeek 等）──
        self.chat_model_name = _env_str("DP_MODEL", "deepseek-chat")
        self.chat_api_key = (
            _read_env("DP_CHAT_API_KEY", "dp-chat-api-key")
            or _read_env("DP_AGENT_API_KEY", "dp-agent-api-key")
            or ""
        )
        self.chat_base_url = _env_str("DP_CHAT_API_URL", "https://api.deepseek.com")
        self.temperature = _env_float("DP_CHAT_TEMPERATURE", 0.7)
        self.history_limit = _env_int("DP_CHAT_HISTORY_LIMIT", 10)

        # ── 意图识别 judge（千问 DashScope；兼容旧名 DP_EXECUTE_*）──
        self.judge_model_name = (
            _read_env("DP_JUDGE_MODEL", "DP_EXECUTE_MODEL", "dp-judge-model") or "qwen-plus"
        )
        self.judge_api_key = (
            _read_env("DP_JUDGE_API_KEY", "dp-judge-api-key")
            or _read_env("DP_EXECUTE_API_KEY", "dp-execute-api-key")
            or _read_env("DP_AGENT_API_KEY", "dp-agent-api-key")
            or ""
        )
        self.judge_base_url = (
            _read_env("DP_JUDGE_API_URL", "DP_EXECUTE_API_URL", "dp-judge-api-url")
            or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.judge_temperature = _env_float(
            "DP_JUDGE_TEMPERATURE",
            _env_float("DP_EXECUTE_TEMPERATURE", 0.0),
        )

        # ── ReAct / 工具调用（默认 DeepSeek，与闲聊同 Key）──
        self.react_model_name = _read_env("DP_REACT_MODEL", "dp-react-model") or self.chat_model_name
        self.react_api_key = (
            _read_env("DP_REACT_API_KEY", "dp-react-api-key") or self.chat_api_key or ""
        )
        self.react_base_url = (
            _read_env("DP_REACT_API_URL", "dp-react-api-url") or self.chat_base_url
        )
        self.react_temperature = _env_float("DP_REACT_TEMPERATURE", 0.0)

        # 兼容旧日志字段名
        self.execute_model_name = self.judge_model_name
        self.execute_api_key = self.judge_api_key
        self.execute_base_url = self.judge_base_url
        self.execute_temperature = self.judge_temperature

        # music 千问草稿 → DeepSeek 二次润色（ReAct 已是 DeepSeek 时建议 false）
        self.music_final_via_chat = _env_bool("MUSIC_FINAL_VIA_CHAT", False)

        # ── MySQL ──
        self.mysql_host = _env_str("MYSQL_HOST", "localhost")
        self.mysql_port = _env_int("MYSQL_PORT", 3306)
        self.mysql_user = _env_str("MYSQL_USER", "root")
        self.mysql_password = _env_str("MYSQL_PASSWORD", "")
        self.mysql_database = _env_str("MYSQL_DB", "myblog")

        # ── Redis ──
        self.redis_host = _env_str("REDIS_HOST", "localhost")
        self.redis_port = _env_int("REDIS_PORT", 6379)
        self.redis_db = _env_int("REDIS_DB", 5)
        self.redis_password = _env_str("REDIS_PASSWORD", "")
        self.chat_list_key = _env_str("REDIS_CHAT_LIST_KEY", "chat:s:{session_id}")
        self.chat_ttl = _env_int("REDIS_CHAT_TTL", 86400)
        self.max_cache_msgs = _env_int("REDIS_MAX_CACHE_MSGS", 40)

        # ── NapCat QQ 告警（Bug Ops notify_developer / 可选即时推送）──
        self.napcat_notify_enabled = _env_bool("NAPCAT_NOTIFY_ENABLED", True)
        self.napcat_http_url = _env_str("NAPCAT_HTTP_URL", "http://127.0.0.1:3000")
        self.napcat_alert_qq = _env_str("NAPCAT_ALERT_QQ", "")
        self.napcat_access_token = _env_str("NAPCAT_ACCESS_TOKEN", "")
        self.napcat_min_severity = (_env_str("NAPCAT_MIN_SEVERITY", "high") or "high").lower()
        self.napcat_alert_on_error = _env_bool("NAPCAT_ALERT_ON_ERROR", True)


def _key_status(value: str) -> str:
    return "ok" if (value or "").strip() else "MISSING"


def log_startup_config() -> None:
    """启动时打印配置摘要（不输出密钥明文）。"""
    cfg = AgentConfig()
    logger.info("[config] env_file=%s exists=%s", _ENV_PATH, _ENV_PATH.is_file())
    logger.info(
        "[config] mysql=%s@%s:%s/%s password=%s",
        cfg.mysql_user,
        cfg.mysql_host,
        cfg.mysql_port,
        cfg.mysql_database,
        _key_status(cfg.mysql_password),
    )
    logger.info(
        "[config] chat model=%s api_key=%s url=%s",
        cfg.chat_model_name,
        _key_status(cfg.chat_api_key),
        cfg.chat_base_url,
    )
    logger.info(
        "[config] judge model=%s api_key=%s url=%s",
        cfg.judge_model_name,
        _key_status(cfg.judge_api_key),
        cfg.judge_base_url,
    )
    logger.info(
        "[config] react model=%s api_key=%s url=%s",
        cfg.react_model_name,
        _key_status(cfg.react_api_key),
        cfg.react_base_url,
    )
    logger.info("[config] music_final_via_chat=%s", cfg.music_final_via_chat)
    from utils.napcat_notify import napcat_configured

    logger.info(
        "[config] napcat enabled=%s configured=%s url=%s qq=%s min_severity=%s",
        cfg.napcat_notify_enabled,
        napcat_configured(),
        cfg.napcat_http_url or "-",
        cfg.napcat_alert_qq or "MISSING",
        cfg.napcat_min_severity,
    )
    missing: list[str] = []
    if not cfg.mysql_password:
        missing.append("MYSQL_PASSWORD")
    if not cfg.judge_api_key:
        missing.append("DP_JUDGE_API_KEY / DP_EXECUTE_API_KEY")
    if not cfg.react_api_key:
        missing.append("DP_AGENT_API_KEY / DP_REACT_API_KEY")
    if missing:
        logger.warning("[config] 缺少必填项: %s", ", ".join(missing))
