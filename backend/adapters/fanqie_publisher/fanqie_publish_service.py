from __future__ import annotations

from pathlib import Path
from typing import Callable

from backend.adapters.fanqie_publisher.fanqie_publish_models import ChapterPublishResult
from backend.adapters.fanqie_publisher.fanqie_publish_multi_runner import run_multi_chapter_publish as _run_multi_chapter_publish
from backend.shared.app.app_runtime_defaults import DEFAULT_CHAPTER_MANAGE_URL


def run_multi_chapter_publish(
    novel_file: Path,
    chapters: list[int],
    chapter_manage_url: str = DEFAULT_CHAPTER_MANAGE_URL,
    *,
    use_ai: bool = False,
    verify_after_publish: bool = True,
    debug_screenshots: bool = True,
    failure_screenshots: bool = True,
    git_tracking: bool = True,
    clean_before_run: bool = True,
    log: Callable[[str], None] = print,
    stop_requested: Callable[[], bool] | None = None,
) -> list[ChapterPublishResult]:
    return _run_multi_chapter_publish(
        novel_file=novel_file,
        chapters=chapters,
        chapter_manage_url=chapter_manage_url,
        use_ai=use_ai,
        verify_after_publish=verify_after_publish,
        debug_screenshots=debug_screenshots,
        failure_screenshots=failure_screenshots,
        git_tracking=git_tracking,
        clean_before_run=clean_before_run,
        log=log,
        stop_requested=stop_requested,
    )
