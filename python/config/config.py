import yaml

from utils.path_tools import get_abs_path


class AgentConfig:
    def __init__(self):
        config_path = get_abs_path("config/config.yml")

        with open(config_path, encoding="utf-8") as file:
            config = yaml.safe_load(file) or {}

        ai_config = config.get("ai") or {}
        chat_config = ai_config.get("chat") or {}
        self.temperature = chat_config.get("temperature", 0.7)

        redis_config = config.get("redis") or {}
        self.chat_list_key = redis_config.get("chat_list_key", "chat:s:{session_id}")
        self.chat_ttl = int(redis_config.get("chat_ttl", 86400))
        self.max_cache_msgs = int(redis_config.get("max_cache_msgs", 40))
