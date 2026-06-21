from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class ChapterSyncResult:
    ok: bool
    changed: bool
    published: bool
    message: str
    diff_path: Optional[Path] = None
    git_repo: Optional[Path] = None
    trace_dir: Optional[Path] = None
    error_stage: str = ""


@dataclass(slots=True)
class ChapterSyncOptions:
    chapter_manage_url: str
    use_ai: bool = False
    check_only: bool = False
    direction: str = "local_to_remote"
    verify_after_publish: bool = True
    debug_screenshots: bool = True
    failure_screenshots: bool = True
    git_tracking: bool = True
    clean_before_run: bool = True

    @property
    def is_publish_to_remote(self) -> bool:
        return self.direction == "local_to_remote" and not self.check_only

    @property
    def should_final_list_verify(self) -> bool:
        return bool(self.verify_after_publish) and self.is_publish_to_remote
