"""将 test_prompt_scenarios 结果渲染为 HTML / Markdown 报告。"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _esc(text: str) -> str:
    return html.escape(text or "", quote=True)


def _badge(text: str, css: str = "tag") -> str:
    return f'<span class="{css}">{_esc(text)}</span>'


def _bool_badge(value: bool, yes: str = "是", no: str = "否") -> str:
    return _badge(yes if value else no, "ok" if value else "muted")


def render_html(
    reports: list[dict[str, Any]],
    *,
    dry_run: bool,
    generated_at: str | None = None,
) -> str:
    ts = generated_at or datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    mode = "dry-run（未调 LLM）" if dry_run else "完整运行（含 LLM）"

    ok_count = sum(1 for r in reports if not r.get("error") and r.get("llm_status") != "error")
    err_count = len(reports) - ok_count

    rows_summary = []
    for r in reports:
        if r.get("error"):
            rows_summary.append(
                f"<tr class='err'><td>{_esc(r.get('scenario_id',''))}</td>"
                f"<td>{_esc(r.get('title',''))}</td>"
                f"<td colspan='8' class='error'>{_esc(r['error'])}</td></tr>"
            )
            continue
        a = r.get("assemble") or {}
        ovt = r.get("openclaw_vs_tavern") or {}
        mp = r.get("memory_pipeline") or {}
        rows_summary.append(
            "<tr>"
            f"<td><code>{_esc(r.get('scenario_id',''))}</code></td>"
            f"<td>{_esc(r.get('title',''))}</td>"
            f"<td>{_esc(r.get('force_intent',''))}</td>"
            f"<td>{_esc(r.get('channel',''))}</td>"
            f"<td class='num'>{r.get('total_ms', 0)}</td>"
            f"<td class='num'>{a.get('system_tokens', 0)}</td>"
            f"<td>{_bool_badge(ovt.get('tavern_lore_injected'))}</td>"
            f"<td>{_bool_badge(ovt.get('tavern_recall_injected'))}</td>"
            f"<td>{_esc(r.get('llm_status',''))}</td>"
            f"<td class='num'>{r.get('llm_ms', 0)}</td>"
            "</tr>"
        )

    sections = []
    for r in reports:
        if r.get("error"):
            sections.append(
                f"<section class='card err'><h2>{_esc(r.get('scenario_id',''))} · "
                f"{_esc(r.get('title',''))}</h2><pre class='error'>{_esc(r['error'])}</pre></section>"
            )
            continue

        a = r.get("assemble") or {}
        ovt = r.get("openclaw_vs_tavern") or {}
        mp = r.get("memory_pipeline") or {}
        timings = a.get("timings_ms") or {}
        timing_rows = "".join(
            f"<tr><td>{_esc(k)}</td><td class='num'>{v}</td></tr>"
            for k, v in sorted(timings.items())
        )
        layer_rows = "".join(
            "<tr>"
            f"<td>{_esc(l.get('category',''))}</td>"
            f"<td>{_esc(l.get('name',''))}</td>"
            f"<td class='num'>{l.get('tokens',0)}</td>"
            f"<td class='num'>{l.get('chars',0)}</td>"
            f"<td><code>{_esc(l.get('source',''))}</code></td>"
            "</tr>"
            for l in (a.get("layers") or [])
        )
        openclaw_li = "".join(
            f"<li>{_esc(x)}</li>" for x in (ovt.get("openclaw_loaded") or [])
        )
        optional = ovt.get("tavern_optional_core") or []
        optional_li = "".join(f"<li><code>{_esc(x)}</code></li>" for x in optional) or "<li class='muted'>（未触发）</li>"

        tags = " ".join(_badge(t) for t in (r.get("tags") or []))
        ae = r.get("agent_entry") or {}
        ae_block = ""
        if ae:
            ae_block = (
                "<h3>AgentEntry</h3><ul>"
                f"<li>handler: <code>{_esc(str(ae.get('handler','')))}</code></li>"
                f"<li>output_mode: {_esc(str(ae.get('output_mode','')))}</li>"
                f"<li>intent: {_esc(str(ae.get('intent_resolved','')))}</li>"
                f"</ul>"
            )

        sp = a.get("system_prompt") or r.get("system_prompt") or ""
        sp_block = ""
        if sp:
            sp_block = (
                "<details class='sys'><summary>展开完整 system prompt "
                f"（{len(sp)} 字 · ~{a.get('system_tokens', 0)} tok）</summary>"
                f"<pre class='sys-body'>{_esc(sp)}</pre></details>"
            )

        llm_ans = (r.get("llm_answer") or "").strip()

        sections.append(
            f"""
<section class="card" id="{_esc(r.get('scenario_id',''))}">
  <h2>{_esc(r.get('scenario_id',''))} · {_esc(r.get('title',''))}</h2>
  <p class="meta">{tags}</p>
  <div class="grid2">
    <div>
      <h3>路由与输入</h3>
      <table class="kv">
        <tr><th>拼装路径</th><td><code>{_esc(a.get('route_path',''))}</code></td></tr>
        <tr><th>intent / channel</th><td>{_esc(r.get('force_intent',''))} / {_esc(r.get('channel',''))}</td></tr>
        <tr><th>跳过记忆子图</th><td>{_bool_badge(a.get('skip_memory_pipeline'), '是', '否')}</td></tr>
        <tr><th>跳过 recall</th><td>{_bool_badge(a.get('skip_recall'), '是', '否')}</td></tr>
        <tr><th>记忆子图</th><td>ran={_esc(str(mp.get('ran')))} · {mp.get('ms',0)}ms · {_esc(str(mp.get('status')))}</td></tr>
        <tr><th>episode 摘要</th><td>{_esc(a.get('episode_summary_preview') or '（空）')}</td></tr>
        <tr><th>总耗时</th><td><strong>{r.get('total_ms',0)} ms</strong></td></tr>
      </table>
    </div>
    <div>
      <h3>Token 与耗时</h3>
      <table class="kv">
        <tr><th>system 字符</th><td>{a.get('system_chars',0)}</td></tr>
        <tr><th>system tokens</th><td><strong>~{a.get('system_tokens',0)}</strong> ({_esc(a.get('token_method',''))})</td></tr>
        <tr><th>LLM</th><td>{_esc(r.get('llm_status',''))} · {r.get('llm_ms',0)}ms · ~{r.get('llm_tokens_est',0)} tok</td></tr>
      </table>
      <table class="small"><thead><tr><th>拼装步骤</th><th>ms</th></tr></thead><tbody>{timing_rows}</tbody></table>
    </div>
  </div>
  <div class="grid2">
    <div>
      <h3>OpenClaw · 能力提示词</h3>
      <p class="hint">permanent → channel → capabilities/*.md</p>
      <ul>{openclaw_li}</ul>
    </div>
    <div>
      <h3>酒馆 · 角色设定</h3>
      <p class="hint">optional core（按需）· lore YAML · Chroma recall</p>
      <ul>
        <li>optional_core: <ul>{optional_li}</ul></li>
        <li>lore 注入: {_bool_badge(ovt.get('tavern_lore_injected'))}</li>
        <li>recall 注入: {_bool_badge(ovt.get('tavern_recall_injected'))}</li>
      </ul>
    </div>
  </div>
  <h3>分层明细</h3>
  <table><thead><tr><th>类别</th><th>层</th><th>tokens</th><th>chars</th><th>来源</th></tr></thead>
  <tbody>{layer_rows}</tbody></table>
  {ae_block}
  <h3>用户输入</h3>
  <pre class="q">{_esc(r.get('question',''))}</pre>
  {sp_block}
  <h3>LLM 回复</h3>
  <div class="answer">{_esc(llm_ans) if llm_ans else '<span class="muted">（无）</span>'}</div>
</section>
"""
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Prompt 场景测试报告</title>
  <style>
    :root {{
      --bg: #0f1419; --card: #1a2332; --text: #e7ecf3; --muted: #8b9cb3;
      --accent: #6eb5ff; --ok: #3dd68c; --warn: #f0c14d; --err: #ff6b6b;
      --border: #2a3a52;
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: "Segoe UI", system-ui, sans-serif; background: var(--bg);
      color: var(--text); margin: 0; padding: 24px; line-height: 1.5; }}
    h1 {{ font-size: 1.5rem; margin: 0 0 8px; }}
    .sub {{ color: var(--muted); margin-bottom: 24px; }}
    .stats {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }}
    .stat {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
      padding: 12px 20px; min-width: 120px; }}
    .stat b {{ font-size: 1.4rem; color: var(--accent); display: block; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    th, td {{ border: 1px solid var(--border); padding: 8px 10px; text-align: left; }}
    th {{ background: #243044; }}
    tr.err td {{ color: var(--err); }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px;
      padding: 20px; margin-bottom: 24px; }}
    .card h2 {{ margin-top: 0; font-size: 1.15rem; color: var(--accent); }}
    .card h3 {{ font-size: 0.95rem; margin: 16px 0 8px; color: var(--muted); }}
    .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    @media (max-width: 900px) {{ .grid2 {{ grid-template-columns: 1fr; }} }}
    .kv th {{ width: 38%; font-weight: 500; color: var(--muted); }}
    .kv td, .kv th {{ border: none; border-bottom: 1px solid var(--border); padding: 6px 8px; }}
    .tag {{ display: inline-block; background: #2a3a52; color: var(--accent);
      padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; margin-right: 6px; }}
    .tag.ok {{ background: #1e3d32; color: var(--ok); }}
    .tag.muted {{ background: #252525; color: var(--muted); }}
    pre.q {{ background: #0d1117; padding: 12px; border-radius: 8px; white-space: pre-wrap;
      font-size: 0.85rem; max-height: 120px; overflow: auto; }}
    .answer {{ background: #152238; border-left: 4px solid var(--ok); padding: 14px 16px;
      border-radius: 0 8px 8px 0; white-space: pre-wrap; }}
    .hint {{ font-size: 0.8rem; color: var(--muted); margin: 0 0 8px; }}
    code {{ font-size: 0.85em; background: #0d1117; padding: 2px 6px; border-radius: 4px; }}
    .toc {{ margin-bottom: 24px; }}
    .toc a {{ color: var(--accent); margin-right: 12px; }}
    .flow {{ background: #0d1117; padding: 14px; border-radius: 8px; font-size: 0.85rem;
      margin-bottom: 24px; }}
    details.sys summary {{ cursor: pointer; color: var(--accent); margin: 12px 0 8px; }}
    pre.sys-body {{ background: #0d1117; padding: 12px; border-radius: 8px; max-height: 400px;
      overflow: auto; font-size: 0.75rem; white-space: pre-wrap; }}
  </style>
</head>
<body>
  <h1>Prompt 场景测试报告</h1>
  <p class="sub">生成时间：{_esc(ts)} · 模式：{_esc(mode)}</p>
  <div class="stats">
    <div class="stat"><b>{len(reports)}</b>场景</div>
    <div class="stat"><b>{ok_count}</b>正常</div>
    <div class="stat"><b>{err_count}</b>异常</div>
  </div>
  <div class="flow">
    <strong>拼装顺序：</strong>记忆子图（chat）→ permanent → optional core（酒馆）
    → channel → capabilities（OpenClaw）→ lore → recall → LLM
  </div>
  <nav class="toc">跳转：
    {''.join(f'<a href="#{_esc(r.get("scenario_id",""))}">{_esc(r.get("scenario_id",""))}</a>' for r in reports if r.get("scenario_id"))}
  </nav>
  <h2>总览</h2>
  <table>
    <thead><tr>
      <th>场景</th><th>标题</th><th>intent</th><th>channel</th>
      <th>总 ms</th><th>system tok</th><th>lore</th><th>recall</th><th>LLM</th><th>LLM ms</th>
    </tr></thead>
    <tbody>{rows_summary}</tbody>
  </table>
  {''.join(sections)}
</body>
</html>
"""


def write_report_bundle(
    reports: list[dict[str, Any]],
    out_dir: Path,
    *,
    dry_run: bool,
    stem: str | None = None,
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = stem or f"prompt_scenarios_{stamp}"
    html_path = out_dir / f"{base}.html"
    json_path = out_dir / f"{base}.json"

    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    html_path.write_text(
        render_html(reports, dry_run=dry_run, generated_at=generated_at),
        encoding="utf-8",
    )
    payload = {
        "generated_at": generated_at,
        "dry_run": dry_run,
        "scenario_count": len(reports),
        "scenarios": reports,
    }
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return html_path, json_path
