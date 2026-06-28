from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_STORY_CONFIG: dict[str, Any] = {
    "product_name": "网文写作",
    "design_note": "前端只负责常用操作；小说设定、门禁策略、事实 schema 和写作流程在后端配置维护。",
    "story_profile": {
        "title": "",
        "genre": "",
        "target_audience": "",
        "premise": "",
        "style_brief": "",
        "world_summary": "",
        "core_hook": "",
        "first_volume_goal": "",
    },
    "workflow": {
        "lineage": "webnovel-writer agent workflow + tianming state gate",
        "steps": [
            "prewrite_gate",
            "context_agent",
            "drafter",
            "draft_gate",
            "reviewer",
            "repair_once_if_allowed",
            "data_agent_artifacts",
            "precommit_gate",
            "chapter_commit",
            "postcommit_gate",
            "backup_ready",
        ],
        "hard_rule": "blocking 问题、schema 错误、引用严重异常时不写入正式 chapters，不更新 story_state，只保存 drafts/rejected artifacts。",
    },
    "story_rules": {
        "world_rules": [],
        "character_rules": [],
        "faction_rules": [],
        "location_rules": [],
        "plot_rules": [],
        "forbidden_patterns": [
            "不能无声明新增关键角色",
            "不能覆盖已确认角色核心性格",
            "不能让角色瞬移到未解释地点",
            "不能跳过章节蓝图的必达节点",
            "不能为了爽点直接破坏世界规则",
        ],
        "style_rules": [
            "中文网文表达，开局快速进入矛盾",
            "每章至少一次冲突/信息/情绪推进",
            "章末保留追读钩子，但不要机械口号",
        ],
    },
    "gate_policy": {
        "unknown_entity_limit": 5,
        "untracked_extra_limit": 3,
        "require_changes_marker": True,
        "require_blueprint_in_strict_mode": True,
        "allow_manual_risk_accept": False,
        "auto_repair_rounds": 1,
    },
    "entity_schema": {
        "character": ["id", "name", "aliases", "status", "location", "locked_traits", "relations", "history"],
        "location": ["id", "name", "aliases", "status", "features", "history"],
        "faction": ["id", "name", "aliases", "status", "members", "relations", "history"],
        "item": ["id", "name", "aliases", "owner", "status", "history"],
        "foreshadow": ["id", "name", "status", "urgency", "introduced_chapter", "resolved_chapter", "history"],
        "conflict": ["id", "name", "status", "progress", "history"],
    },
}


def default_story_config() -> dict[str, Any]:
    return deepcopy(DEFAULT_STORY_CONFIG)
