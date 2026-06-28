from __future__ import annotations

from typing import Any


SYSTEM_BASE = """
你是一个专业中文长篇网文创作系统。你的目标不是一次性写完，而是维持数百章仍然稳定的故事状态。
你必须遵循：
1. 尊重已有设定、角色状态、地点、势力、伏笔和时间线。
2. 输出内容要有网文可读性：明确目标、冲突推进、爽点/情绪点、章末钩子。
3. 不凭空改写已确认事实；需要新增事实时要在结构化变更里声明。
4. 中文输出，避免解释你在遵循规则，直接给结果。
""".strip()


PLANNER_SYSTEM = SYSTEM_BASE + """

你现在是“总编/责编/设定统筹”。输出要结构化、可落地、方便后续章节生成。
如果生成章节蓝图，优先输出严格 JSON，不要夹杂解释。
"""


CONTEXT_SYSTEM = SYSTEM_BASE + """

你现在是“context-agent / 写作任务书编辑”。
你只负责把程序检索到的设定、状态、蓝图、近期摘要整理成可直接写作的任务书。
不得新增事实，不得改设定，不得替作者决定大纲之外的大转折。
输出 Markdown，固定包含：本章硬性约束、必达节点、禁区、角色状态、场景写法、伏笔债务、结尾钩子。
"""


DRAFTER_SYSTEM = SYSTEM_BASE + """

你现在是“章节写手”。你必须输出两部分：
第一部分：章节正文。
第二部分：使用分隔符 ---CHANGES--- 后输出 JSON 变更声明。
JSON 必须包含：summary, characters, locations, factions, items, foreshadows, conflicts, timeline, hooks, quality_notes。
不要把 JSON 混入正文。字段缺失会被系统打回，章节不会正式入账。
"""


REVIEWER_SYSTEM = SYSTEM_BASE + """

你现在是“审稿与门禁校验员”。只审查，不重写全文。输出 JSON：
{
  "score": 0-100,
  "pass": true/false,
  "blocking_issues": [],
  "warnings": [],
  "fix_suggestions": [],
  "strengths": []
}
重点检查：人设一致性、设定一致性、时间线、冲突推进、爽点/节奏、章末钩子、事实声明完整性。
"""


FACT_SYSTEM = SYSTEM_BASE + """

你现在是“data-agent / 事实提取与状态回写员”。从章节正文和变更声明中提取可持久化事实。
只输出 JSON，格式必须是：
{
  "fulfillment_result": {"chapter_no": 1, "completed_nodes": [], "missed_nodes": [], "notes": []},
  "disambiguation_result": {"new_entities": [], "ambiguous_entities": [], "pending": []},
  "extraction_result": {
    "summary": "本章简述",
    "characters": {"角色名": {"status": "", "location": "", "emotion": "", "ability": "", "relations": []}},
    "locations": {"地点": {"status": "", "features": []}},
    "factions": {"势力": {"status": "", "members": [], "relations": []}},
    "items": {"物品": {"owner": "", "status": ""}},
    "foreshadows": {"伏笔名": {"status": "新增/推进/回收", "note": "", "urgency": "低/中/高"}},
    "conflicts": {"冲突名": {"status": "", "progress": ""}},
    "timeline": [],
    "milestones": [],
    "hooks": []
  }
}
"""


def project_brief(meta: dict[str, Any], story_config: dict[str, Any] | None = None) -> str:
    profile = (story_config or {}).get("story_profile") or {}
    return f"""
【书名】{profile.get('title') or meta.get('title') or ''}
【题材】{profile.get('genre') or meta.get('genre') or ''}
【核心创意】{profile.get('premise') or meta.get('premise') or ''}
【目标读者】{profile.get('target_audience') or meta.get('target_audience') or ''}
【文风要求】{profile.get('style_brief') or meta.get('style_brief') or ''}
【世界概要】{profile.get('world_summary') or ''}
【核心钩子】{profile.get('core_hook') or ''}
【第一卷目标】{profile.get('first_volume_goal') or ''}
""".strip()


def build_outline_prompt(meta: dict[str, Any], *, scope: str = "full", story_config: dict[str, Any] | None = None) -> str:
    label = {"full": "全书大纲", "volume": "分卷大纲", "blueprint": "章节蓝图"}.get(scope, "规划")
    cfg = story_config or {}
    return f"""
请为下面的小说生成【{label}】。

{project_brief(meta, cfg)}

【后端写作规则】
{cfg.get('story_rules') or {}}

要求：
- 保留网文商业节奏，开局强钩子，阶段目标清晰。
- 输出 Markdown，分层明确。
- 包含主线、反派压力、成长线、爽点、伏笔、阶段性高潮。
- 不要覆盖后端 story_config.json 中的硬规则。
""".strip()



def build_context_agent_prompt(context_pack: str, blueprint_json: dict[str, Any], story_config: dict[str, Any]) -> str:
    return f"""
请把下面的程序上下文包整理成第 N 章可直接执行的写作任务书。

【后端 story_config】
{story_config}

【结构化蓝图】
{blueprint_json or {}}

【程序上下文包】
{context_pack}

输出 Markdown。必须按以下顺序：
1. 本章硬性约束：goal / time_anchor / chapter_span / ending_hook。
2. 必达节点：must_cover_nodes。
3. 本章禁区：forbidden_zones。
4. 角色状态与出场强度。
5. 场景、冲突、爽点、伏笔债务。
6. 正文起草注意事项。
""".strip()


def build_blueprint_json_prompt(meta: dict[str, Any], state: dict[str, Any], outline_text: str, recent: list[dict[str, str]], chapter_no: int, story_config: dict[str, Any]) -> str:
    return f"""
请生成第 {chapter_no} 章结构化章节蓝图。只输出 JSON，不要 Markdown，不要解释。

{project_brief(meta, story_config)}

【后端规则】
{story_config.get('story_rules') or {}}

【已有大纲】
{outline_text or '暂无'}

【故事状态】
{state}

【近期章节摘要】
{recent}

JSON schema：
{{
  "chapter_no": {chapter_no},
  "title": "章节标题",
  "goal": "本章核心目标",
  "time_anchor": "时间锚点",
  "chapter_span": "本章覆盖时间/地点范围",
  "pov": "视角角色",
  "scene": "主场景",
  "required_characters": [],
  "required_locations": [],
  "required_factions": [],
  "must_cover_nodes": [],
  "forbidden_zones": [],
  "conflict": "本章冲突",
  "payoff": "本章爽点/情绪点",
  "foreshadows": [],
  "ending_hook": "章末钩子",
  "state_writeback_hint": []
}}
""".strip()


def build_context_pack(meta: dict[str, Any], state: dict[str, Any], outline_text: str, blueprint_text: str, recent_chapters: list[dict[str, str]], chapter_no: int, story_config: dict[str, Any] | None = None) -> str:
    recent_text = "\n\n".join(
        f"第 {item.get('chapter_no')} 章《{item.get('title') or ''}》摘要：{item.get('summary') or item.get('preview') or ''}"
        for item in recent_chapters
    ).strip()
    return f"""
{project_brief(meta, story_config)}

【当前目标章节】第 {chapter_no} 章

【全书/分卷规划】
{outline_text or '暂无规划，请保持主线自然推进。'}

【本章蓝图】
{blueprint_text or '暂无章节蓝图，请根据当前故事状态生成合理推进。'}

【故事状态快照】
{_compact_state(state)}

【最近章节摘要】
{recent_text or '暂无。'}
""".strip()


def build_draft_prompt(context_pack: str, *, chapter_no: int, chapter_title: str, target_words: int, strictness: str) -> str:
    return f"""
请根据上下文创作第 {chapter_no} 章《{chapter_title or '未命名章节'}》。

【目标字数】约 {target_words} 字。
【门禁强度】{strictness}

【上下文包】
{context_pack}

正文要求：
- 第一段快速进入矛盾或悬念。
- 每 800-1200 字至少有一次信息推进、情绪推进或冲突升级。
- 人设和世界规则必须服从故事状态快照。
- 章末留下可追读钩子，但不要机械喊口号。

输出格式：
先输出章节正文。
然后单独一行输出：---CHANGES---
然后输出 JSON 变更声明。
""".strip()


def build_review_prompt(context_pack: str, chapter_text: str, changes: dict[str, Any]) -> str:
    return f"""
请审查以下章节是否可以落地。

【上下文包】
{context_pack}

【章节正文】
{chapter_text}

【AI 声明的变更】
{changes}
""".strip()


def build_fact_prompt(chapter_no: int, chapter_title: str, chapter_text: str, changes: dict[str, Any]) -> str:
    return f"""
请从下面章节中提取可写入故事状态的事实。

【章节】第 {chapter_no} 章《{chapter_title}》

【正文】
{chapter_text}

【变更声明】
{changes}
""".strip()


def _compact_state(state: dict[str, Any]) -> str:
    parts = []
    for key, label in [
        ("characters", "角色"),
        ("locations", "地点"),
        ("factions", "势力"),
        ("items", "物品"),
        ("foreshadows", "伏笔"),
        ("conflicts", "冲突"),
    ]:
        value = state.get(key) or {}
        if value:
            parts.append(f"【{label}】{value}")
    summaries = state.get("chapter_summaries") or {}
    if summaries:
        tail = dict(list(summaries.items())[-8:])
        parts.append(f"【近期摘要】{tail}")
    return "\n".join(parts) if parts else "暂无已确认事实。"
