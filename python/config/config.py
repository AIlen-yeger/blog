from utils.path_tools import get_abs_path


class AgentConfig:
    def __init__(self):
        config_path = get_abs_path("config/config.yml")

        with open(config_path) as file:
            config = file.read()

        agent_config = config.get("ai")
        self.api_key = agent_config.get("api_key")
        self.temperature = agent_config.get("temperature")
