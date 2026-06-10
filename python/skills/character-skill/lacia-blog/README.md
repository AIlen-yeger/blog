# lacia-blog · 蕾西亚（合并后角色包）

**单一真相源**：人设、功能 skill、运维、lore 均在本目录。

## 结构

| 目录 | 内容 |
|------|------|
| `core/` | 人设 permanent + 关系 + hIE 背景（按需） |
| `capabilities/` | 按 intent 加载的功能清单（原 `prompt/skills/`） |
| `ops/` | Bug Ops（原 `bug_ops_system.md`） |
| `lore/` | 酒馆式 YAML（原 `prompt/lore/`） |

## 运行时

```python
from server.prompt_skills import build_system_prompt, character_lore_path

build_system_prompt(intent="chat", channel="web")
character_lore_path()  # → .../lore/lacia_static.yaml
```

## 旧路径

原 `prompt/system.md`、`prompt/skills/*`、`prompt/bug_ops_system.md`、`prompt/lore/*` 已删除；请只编辑本角色包。

## 后续接入（你来写代码）

- OpenClaw `skill_registry`：扫描 `manifest.json` → `capabilities`
- Lorebook：读 `character_lore_path()` 或 `lore/*.yaml`
- 多角色：改 `CHARACTER_SLUG` 或配置切换 `character_root`
