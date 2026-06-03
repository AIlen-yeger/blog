"""兼容导入：请使用 server.qq.market_pipeline。"""
from server.qq.market_pipeline import (  # noqa: F401
    env_two_phase_enabled,
    env_two_phase_enabled as _env_two_phase_enabled,
    parse_market_facts_json,
    run_aicoin_qq_two_phase,
)
