# AiCoin 行情 Agent 链路说明

本文说明：用户一句话如何进入 **ReAct 子图**、图里各节点做什么、与 **MCP** 的关系，以及如何扩展。

## 1. 总览（主链路）

当前架构是 **「意图路由 + 按意图执行分支」**，不是单一 LangGraph 大主图。  
`music` / `aicoin` 各自在 `run_*_react` 里 **临时编译** 一个标准 ReAct 子图并 `invoke`。

```mermaid
flowchart TD
    API["HTTP / 内部调用 AgentEntry.run()"]
    State["组装 AgentState\nquestion, session_id, token, trace_id…"]
    Judge["IntentRouter.classify_intent()\nprompt/judge.md + 关键词兜底"]
    Mode["output_mode_for(intent, channel)\nweb+chat/music→stream，其余→once"]
    Handler{"intent 查表\n_ONCE / _STREAM_HANDLERS"}
    Chat["chat → ChatModel\n无工具"]
    Music["music → run_music_react()\ncompile_react_graph"]
    Aicoin["aicoin → run_aicoin_react()\ncompile_react_graph"]
    Note["commit_user → run_note_comment()"]
    Reply["AgentReplyResult\n文本或 SSE"]

    API --> State --> Judge --> Mode --> Handler
    Handler -->|chat| Chat --> Reply
    Handler -->|music| Music --> Reply
    Handler -->|aicoin| Aicoin --> Reply
    Handler -->|commit_user| Note --> Reply
```

**触发 `run_aicoin_react` 的条件：**

1. `AgentEntry.run()` 得到 `intent == "aicoin"`（judge 或关键词覆盖，或 `force_intent="aicoin"`）。
2. **权限**：`server/aicoin_access.py` — 仅 `user_role=admin` 或 `account` 与 `.env` 的 `DEVELOPER_EMAIL` 一致时保留 aicoin；否则 **`intent` 降级为 `chat`**（普通用户问币价走闲聊，不调 MCP）。
3. `agent_entry._ONCE_HANDLERS["aicoin"]` 调用 `run_aicoin_react(state)`。

## 2. ReAct 子图（通用模板）

实现位置：`server/route_graph/react_subgraph.py` 的 `compile_react_graph()`。

```mermaid
flowchart LR
    START((START)) --> Agent["agent 节点\nbind_tools 的 LLM"]
    Agent --> Route{"tools_condition\n或达到 max_rounds"}
    Route -->|有 tool_calls| Tools["tools 节点\nToolNode 执行 @tool"]
    Route -->|无 tool_calls| END((END))
    Tools --> Agent
```

| 节点 | 职责 |
|------|------|
| **agent** | 首次无 `messages` 时调用 `build_initial_messages(state)` → System + 历史 + 当前 Human；再 `model.invoke`；可返回 `tool_calls` |
| **tools** | 执行 LangChain 工具（如 `coin_info`、`kline`） |
| **条件边** | 有 tool_calls → tools；否则 END；超过 `DEFAULT_MAX_REACT_ROUNDS`（6）强制 END |

`run_aicoin_react` 与 `run_music_react` 的差异仅在：

- `tools=build_aicoin_tools()`（MCP 未开则 `[]`，直接返回提示，不编译图）
- `build_initial_messages` / `subgraph="aicoin"` / 提示词 `intent="aicoin"`

## 3. AiCoin 专用数据流

```mermaid
sequenceDiagram
    participant U as 用户
    participant E as AgentEntry
    participant R as run_aicoin_react
    participant G as ReAct 子图
    participant T as aicoin_agent_tools
    participant M as MCP aicoin

    U->>E: question
    E->>E: intent=aicoin
    E->>R: state
    R->>R: build_aicoin_tools()
    alt MCP 未启用
        R-->>E: final_answer 未开启提示
    else MCP 已启用
        R->>G: graph.invoke(state)
        G->>G: agent 可能调用 coin_info/kline/...
        G->>T: @tool 参数
        T->>T: 组装 arguments
        T->>M: call_tool_sync(tool_name, args)
        M-->>T: 行情/新闻文本
        T-->>G: tool 结果
        G->>G: agent 汇总自然语言
        R->>R: extract_final_answer + save_turn
        R-->>E: final_answer
    end
    E-->>U: 回复 / SSE
```

## 4. 配置与文件

| 文件 | 作用 |
|------|------|
| `config/mcp_servers.json` | `aicoin` stdio：`npx -y @aicoin/aicoin-mcp` |
| `.env` | `AICOIN_MCP_ENABLED=true` |
| `server/tools/aicoin_agent_tools.py` | LangChain 工具封装 → `_call_mcp` |
| `server/route_graph/aicoin_route.py` | `run_aicoin_react` |
| `server/agent_entry.py` | 意图 → handler 表 |
| `server/intent_router.py` | judge + 关键词 `aicoin` |
| `prompt/judge.md` | 路由规则含 aicoin |
| `prompt/skills/aicoin.md` | 子图 system 技能（只读、定投视角） |

## 5. 本地验证

```bash
# MCP
python scripts/probe_mcp.py --list
python scripts/probe_mcp.py aicoin

# 强制走 aicoin 子图（不依赖 judge）
# AgentEntry.run(..., force_intent="aicoin")
```

## 6. 输出形态

| channel | intent | 模式 |
|---------|--------|------|
| web | chat, music | stream（SSE 增量） |
| web | aicoin | **once**（整段返回；也可改为 stream，handler 已具备 `_stream_aicoin`） |
| qq 等 | aicoin | once |

若希望 web 上 aicoin 也流式输出，在 `output_mode_for()` 中加入 `aicoin` 即可。

## 7. 历史消息

`aicoin_route` 默认拉取最近 **4** 轮历史（上限 8），用于「它呢 / 刚才那个币」类指代。  
涉及现价、涨跌幅时，应在 `prompt/skills/aicoin.md` 中要求模型 **必须重新调工具**，避免复述过期数字。
