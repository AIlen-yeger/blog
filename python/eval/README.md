# Agent Evaluation Harness

轻量、可重复的 Agent 子系统评测（**零 LLM 调用**，recall 除外且需 Embedding）。

## 部署说明

**不上 GitHub / 云端 CI**：评测仅本地或自建环境使用，仓库内**不配置** GitHub Actions；`reports/eval/*.json` 已 gitignore，无需推到远程。

## 运行

```bash
cd python
python scripts/run_agent_eval.py
python scripts/run_agent_eval.py --suite judge,lore
python scripts/run_agent_eval.py --threshold 0.95 --json reports/eval/latest.json
```

任一套件（非 skipped）pass rate 低于 `--threshold`（默认 0.90）时退出码为 `1`。

## 套件

| 套件 | 被测函数 | Golden |
|------|----------|--------|
| `judge` | `intent_from_question` | `golden/judge_routing.yaml` |
| `lore` | `Lorebook.select_matched_ids` | `golden/lore_trigger.yaml` |
| `orchestrator` | `plan_tasks_rules_only` / `should_orchestrate` 等 | `golden/orchestrator_plan.yaml` |
| `document` | `parse_text_content` + `fixtures/docs/` | `golden/document_ingest.yaml` |
| `recall` | `UserMemory.recall`（临时 Chroma） | `golden/recall_cases.yaml` + `fixtures/recall_seed.json` |

### Recall 跳过条件

未配置 `EMBEDDING_MODEL_NAME`、`EMBEDDING_API_KEY`、`EMBEDDING_BASE_URL` 时，`recall` 套件状态为 `SKIP`，不计入失败。

## 新增用例

1. 在对应 `golden/*.yaml` 增加 `id` 与期望字段。
2. `document` 套件如需新样例，在 `fixtures/docs/` 添加文件并在 yaml 中引用 `fixture`。
3. `recall` 套件在 `fixtures/recall_seed.json` 增加记忆后补充 `query` / `expect_text_substr` 或 `expect_tags`。

## 与旧脚本

- `scripts/test_orchestrator_scenarios.py` → 薄包装 `run_suite("orchestrator")`
- `scripts/test_document_ingest.py` → 薄包装 `run_suite("document")`
- `test_prompt_scenarios.py`、`test_user_memory_scenarios.py` 保留为交互/观测用途

## 报告

终端表格 + JSON（默认 `reports/eval/latest.json`，已 gitignore）。
