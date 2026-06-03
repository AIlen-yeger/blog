from dataclasses import dataclass, field
from enum import Enum
from typing import List, Any


class McpTransport(str, Enum):
    STDIO = "stdio"
    SSE = "sse"


@dataclass
class McpStdioConfig:
    command: str
    args: List[str] = field(default_factory=list)
    cwd:str | None = None
    env: dict[str,str] | None = None


@dataclass
class McpSseConfig:
    url:str
    headers: dict[str, str] | None = None

@dataclass
class McpClientConfig:
    name:str
    transport: McpTransport
    enabled:bool = True
    stdio: McpStdioConfig | None = None
    sse: McpSseConfig | None = None
    default_tool:str | None = None

@dataclass
class McpCallResult:
    ok: bool
    text: str
    raw:Any = None
    error: str | None = None
