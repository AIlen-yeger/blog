import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.config import AgentConfig, ensure_env_loaded, log_startup_config
from route.app import router
from utils.agent_log_scheduler import start_agent_log_prune_scheduler
from utils.bug_agent_scheduler import start_bug_agent_scheduler
from utils.trace_log import setup_agent_logging

ensure_env_loaded()
from utils.mcp.registry import reload_mcp_configs

reload_mcp_configs()
log_startup_config()

setup_agent_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_agent_log_prune_scheduler()
    start_bug_agent_scheduler()
    cfg = AgentConfig()
    if cfg.qq_mcp_enabled:
        friends = [x.strip() for x in cfg.qq_mcp_friends.split(",") if x.strip()]
        if friends and cfg.qq_mcp_dir:
            from utils.qq.qq_inbox_poller import start_qq_inbox_poller

            start_qq_inbox_poller(friends=friends, interval=cfg.qq_mcp_poll_interval)
        else:
            logger.warning(
                "[qq_mcp] enabled but QQ_MCP_DIR or QQ_MCP_FRIENDS missing, poller skipped"
            )
    yield


app = FastAPI(title="Blog Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    # 热重载会在请求中途重启进程，导致对话卡住；需要时设 AGENT_RELOAD=true
    use_reload = os.getenv("AGENT_RELOAD", "false").lower() == "true"
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=use_reload,
        http="httptools",
        ws="websockets",
    )
