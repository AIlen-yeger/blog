import os

import yaml

from utils.path_tools import get_abs_path


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    return value


def _read_env(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value.strip()
    return default


class AgentConfig:
    def __init__(self):
        config_path = get_abs_path("config/config.yml")

        with open(config_path, encoding="utf-8") as file:
            config = yaml.safe_load(file) or {}

        ai_config = config.get("ai") or {}
        chat_config = ai_config.get("chat") or {}
        self.temperature = chat_config.get("temperature", 0.7)
        self.history_limit = int(chat_config.get("history_limit", 10))
        self.chat_model_name = str(
            _read_env("DP_MODEL", "dp-model", "deepseek-chat") or "deepseek-chat"
        )

        mysql_config = config.get("mysql") or {}
        self.mysql_host = (mysql_config.get("host"))
        self.mysql_port = int(mysql_config.get("port"))
        self.mysql_user =(mysql_config.get("user"))
        self.mysql_password = (
            _env("MYSQL_PASSWORD") or mysql_config.get("password") or ""
        )
        self.mysql_database = str(mysql_config.get("database"))

        redis_config = config.get("redis") or {}
        self.redis_host = str(redis_config.get("host"))
        self.redis_port = int(redis_config.get("port"))
        self.redis_db = int(redis_config.get("db"))
        self.redis_password = (
            _env("REDIS_PASSWORD") or redis_config.get("password") or ""
        )
        self.chat_list_key = redis_config.get("chat_list_key")
        self.chat_ttl = int(redis_config.get("chat_ttl"))
        self.max_cache_msgs = int(redis_config.get("max_cache_msgs"))

        execute_config = ai_config.get("execute") or {}
        self.execute_model_name = str(
            _env("DP_EXECUTE_MODEL") or execute_config.get("model") or "qwen-plus"
        )
        self.execute_api_key = (
            _read_env("DP_AGENT_API_KEY", "dp-agent-api-key")
            or execute_config.get("api_key")
            or ""
        )
        self.execute_base_url = (
            _read_env("DP_AGENT_API_URL", "dp-agent-api-url")
            or execute_config.get("base_url")
            or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.execute_temperature = float(execute_config.get("temperature", 0.0))


