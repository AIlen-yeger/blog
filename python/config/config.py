"""Agent 配置：统一从 python/.env 读取（启动时自动 load_dotenv）。"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_ENV_LOADED = False
_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


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
        self.history_limit = _env_int("DP_CHAT_HISTORY_LIMIT", 6)

        # ── 意图识别 judge（默认与闲聊同 DeepSeek）──
        # 仅当 DP_JUDGE_ENABLED=true 时读取 DP_JUDGE_* / DP_EXECUTE_*（避免 .env 残留千问配置）
        if _env_bool("DP_JUDGE_ENABLED", False):
            _judge_model = _read_env("DP_JUDGE_MODEL", "DP_EXECUTE_MODEL", "dp-judge-model")
            _judge_key = _read_env("DP_JUDGE_API_KEY", "dp-judge-api-key") or _read_env(
                "DP_EXECUTE_API_KEY", "dp-execute-api-key"
            )
            _judge_url = _read_env(
                "DP_JUDGE_API_URL", "DP_EXECUTE_API_URL", "dp-judge-api-url"
            )
            self.judge_model_name = _judge_model or "qwen-plus"
            self.judge_api_key = _judge_key or ""
            self.judge_base_url = (
                _judge_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            self.judge_temperature = _env_float(
                "DP_JUDGE_TEMPERATURE",
                _env_float("DP_EXECUTE_TEMPERATURE", 0.0),
            )
        else:
            self.judge_model_name = self.chat_model_name
            self.judge_api_key = self.chat_api_key
            self.judge_base_url = self.chat_base_url
            self.judge_temperature = 0.0

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

        # 搜狗 MCP：见 config/mcp_servers.json（SOGOU_MCP_* 环境变量注入）
        self.sogou_mcp_enabled = _env_bool("SOGOU_MCP_ENABLED", True)
        self.sogou_mcp_sse_url = _env_str(
            "SOGOU_MCP_SSE_URL",
            "https://phoenixdna-sogou-search.ms.show/gradio_api/mcp/sse",
        )

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
        self.memory_episode_key = _env_str("REDIS_MEMORY_EPISODE_KEY", "memory:episode:{user_id}")
        self.memory_episode_ttl = _env_int("REDIS_MEMORY_EPISODE_TTL", 604800)

        # ── NapCat QQ 告警（Bug Ops notify_developer / 可选即时推送）──
        self.napcat_notify_enabled = _env_bool("NAPCAT_NOTIFY_ENABLED", True)
        self.napcat_http_url = _env_str("NAPCAT_HTTP_URL", "http://127.0.0.1:3000")
        self.napcat_alert_qq = _env_str("NAPCAT_ALERT_QQ", "")
        self.napcat_access_token = _env_str("NAPCAT_ACCESS_TOKEN", "")
        self.napcat_min_severity = (_env_str("NAPCAT_MIN_SEVERITY", "high") or "high").lower()
        self.napcat_alert_on_error = _env_bool("NAPCAT_ALERT_ON_ERROR", True)
        self.qq_mcp_enabled = _env_bool("QQ_MCP_ENABLED", False)
        self.qq_mcp_dir = _env_str("QQ_MCP_DIR", "")
        self.qq_mcp_bot_qq = _env_str("QQ_MCP_BOT_QQ", "")
        self.qq_mcp_friends = _env_str("QQ_MCP_FRIENDS", "")  # 逗号分隔
        self.qq_mcp_poll_interval = _env_float("QQ_MCP_POLL_INTERVAL_SEC", 5.0)
        self.qq_mcp_napcat_host = _env_str("QQ_MCP_NAPCAT_HOST", "127.0.0.1")
        self.qq_mcp_napcat_port = _env_str("QQ_MCP_NAPCAT_PORT", "3000")
        self.qq_mcp_ws_port = _env_str("QQ_MCP_WS_PORT", "3001")
        # 新设备/无状态文件时：首轮只同步水位线，不对历史私聊自动回复
        self.qq_mcp_bootstrap_on_start = _env_bool("QQ_MCP_BOOTSTRAP_ON_START", True)
        self.agent_ops_token = _env_str("AGENT_OPS_TOKEN", "")
        # 与 Java application.yml 的 developer.email 保持一致；用于 AiCoin 行情路由鉴权
        self.developer_email = (
            _read_env("DEVELOPER_EMAIL", "developer.email", "DEVELOPER.EMAIL") or ""
        ).strip().lower()
        _dev_qq = _env_str("DEVELOPER_QQ", "")
        if not _dev_qq:
            _dev_qq = _env_str("NAPCAT_ALERT_QQ", "")
        self.developer_qq = "".join(c for c in _dev_qq if c.isdigit())

        # ── BTC 定投日报（QQ 私聊推送 + 持仓记账）──
        self.btc_dca_daily_enabled = _env_bool("BTC_DCA_DAILY_ENABLED", True)
        self.btc_dca_daily_tz = _env_str("BTC_DCA_DAILY_TZ", "Asia/Shanghai")
        self.btc_dca_daily_hour = _env_int("BTC_DCA_DAILY_HOUR", 9)
        self.btc_dca_daily_minute = _env_int("BTC_DCA_DAILY_MINUTE", 0)
        self.btc_dca_check_interval_sec = _env_float("BTC_DCA_CHECK_INTERVAL_SEC", 60.0)
        self.btc_dca_initial_btc_qty = _env_float("BTC_DCA_INITIAL_BTC_QTY", 0.00288579)
        self.btc_dca_initial_cost_usdt = _env_float("BTC_DCA_INITIAL_COST_USDT", 0)
        self.btc_dca_initial_avg_usdt = _env_float("BTC_DCA_INITIAL_AVG_USDT", 92212.5651)

        # ── 向量模型（用户记忆 embed / recall；未配 key 时 recall 自动跳过）──
        self.embedding_model_name = _env_str("EMBEDDING_MODEL_NAME", "text-embedding-v4")
        self.embedding_base_url = _env_str(
            "EMBEDDING_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.embedding_api_key = _env_str("EMBEDDING_API_KEY", "")

        # ── Chroma 用户记忆（仅向量库，不写 MySQL）──
        self.chroma_memory_enabled = _env_bool("CHROMA_MEMORY_ENABLED", True)
        self.chroma_memory_path = _env_str("CHROMA_MEMORY_PATH", "data/chroma_user_memory")
        self.chroma_memory_collection = _env_str(
            "CHROMA_MEMORY_COLLECTION", "user_memories"
        )

def _key_status(value: str) -> str:
    return "ok" if (value or "").strip() else "MISSING"


def embedding_configured(cfg: AgentConfig | None = None) -> bool:
    """EMBEDDING_* 三项齐全才可做向量 recall / 持久化 embed。"""
    c = cfg or AgentConfig()
    return bool(
        (c.embedding_model_name or "").strip()
        and (c.embedding_api_key or "").strip()
        and (c.embedding_base_url or "").strip()
    )


def chat_llm_configured(cfg: AgentConfig | None = None) -> bool:
    c = cfg or AgentConfig()
    return bool((c.chat_model_name or "").strip() and (c.chat_api_key or "").strip())


def normalize_openai_base_url(url: str) -> str:
    base = (url or "https://api.deepseek.com").strip().rstrip("/")
    if base.endswith("/v1"):
        return base
    return base + "/v1"


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
    logger.info(
        "[config] judge_via_qwen=%s",
        _env_bool("DP_JUDGE_ENABLED", False),
    )
    try:
        from utils.mcp.registry import is_mcp_enabled, list_mcp_names

        for mcp_name in list_mcp_names():
            logger.info("[config] mcp %s enabled=%s", mcp_name, is_mcp_enabled(mcp_name))
    except Exception as exc:
        logger.warning("[config] mcp registry load failed: %s", exc)
    from utils.qq.napcat_notify import napcat_configured
    from utils.log.agent_log_config import resolve_log_dir

    logger.info(
        "[config] napcat enabled=%s configured=%s url=%s qq=%s min_severity=%s",
        cfg.napcat_notify_enabled,
        napcat_configured(),
        cfg.napcat_http_url or "-",
        cfg.napcat_alert_qq or "MISSING",
        cfg.napcat_min_severity,
    )
    logger.info(
        "[config] qq_mcp enabled=%s dir=%s bot=%s friends=%s interval=%.1fs",
        cfg.qq_mcp_enabled,
        cfg.qq_mcp_dir or "MISSING",
        cfg.qq_mcp_bot_qq or "MISSING",
        cfg.qq_mcp_friends or "-",
        cfg.qq_mcp_poll_interval,
    )
    logger.info(
        "[config] agent_ops_token=%s (QQ 桥接 JWT 须与 Java app.agent.ops-token 相同)",
        _key_status(cfg.agent_ops_token),
    )
    logger.info(
        "[config] agent_log_dir=%s (active *.jsonl; rotated in archive/)",
        resolve_log_dir(),
    )
    missing: list[str] = []
    if not cfg.mysql_password:
        missing.append("MYSQL_PASSWORD")
    if not cfg.chat_api_key:
        missing.append("DP_AGENT_API_KEY / DP_CHAT_API_KEY")
    if cfg.qq_mcp_enabled and not cfg.agent_ops_token:
        missing.append("AGENT_OPS_TOKEN (QQ 私聊登录态工具)")
    if missing:
        logger.warning("[config] 缺少必填项: %s", ", ".join(missing))
