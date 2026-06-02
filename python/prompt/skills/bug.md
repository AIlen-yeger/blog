# Bug Ops 技能（仅系统任务）

## 触发方式

- scheduled_scan：定时扫描 error/summary 中未处理事件
- error_alert：运行时出现严重 ERROR 后自动激活
- manual：开发者手动触发

## 标准流程

1. 有 trace_id → get_agent_trace 拉全链路
2. 无 trace_id → list_recent_agent_errors / search_agent_logs 定位
3. 结论明确后 → update_incident_record
4. 需人工介入 → notify_developer

## 禁止

- 未读日志就写 root_cause
- 在 notify 中附带 token、密码、完整 .env 路径
