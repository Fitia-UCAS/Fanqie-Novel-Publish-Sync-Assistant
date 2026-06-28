from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class WriterProjectMeta:
    project_id: str
    title: str
    genre: str = ""
    premise: str = ""
    target_audience: str = ""
    style_brief: str = ""
    project_path: str = ""
    novel_file: str = ""
    story_config_source: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WriterPaths:
    root: str
    meta: str
    settings: str
    story_config: str
    state: str
    outlines: str
    volumes: str
    blueprints: str
    chapters: str
    drafts: str
    rejected: str
    reviews: str
    commits: str
    runtime: str
    artifacts: str
    runs: str
    validation: str
    indexes: str
    exports: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


DEFAULT_STATE: dict[str, Any] = {
    "schema_version": 2,
    "characters": {},
    "locations": {},
    "factions": {},
    "items": {},
    "foreshadows": {},
    "conflicts": {},
    "timeline": [],
    "milestones": [],
    "chapter_summaries": {},
    "chapter_status": {},
    "entity_mentions": [],
    "foreshadow_debts": {},
    "conflict_progress": {},
    "latest_chapter": 0,
}
