from __future__ import annotations

from dataclasses import dataclass

from backend.shared.app.app_runtime_defaults import DEFAULT_CHAPTER_MANAGE_URL


@dataclass(slots=True)
class ChapterPublishOptions:
    chapter_manage_url: str = DEFAULT_CHAPTER_MANAGE_URL
    use_ai: bool = False
    verify_after_publish: bool = True
    debug_screenshots: bool = True
    failure_screenshots: bool = True
    git_tracking: bool = True
    clean_before_run: bool = True


def make_chapter_publish_options(
    *,
    chapter_manage_url: str = DEFAULT_CHAPTER_MANAGE_URL,
    use_ai: bool = False,
    verify_after_publish: bool = True,
    debug_screenshots: bool = True,
    failure_screenshots: bool = True,
    git_tracking: bool = True,
    clean_before_run: bool = True,
) -> ChapterPublishOptions:
    return ChapterPublishOptions(
        chapter_manage_url=chapter_manage_url,
        use_ai=use_ai,
        verify_after_publish=verify_after_publish,
        debug_screenshots=debug_screenshots,
        failure_screenshots=failure_screenshots,
        git_tracking=git_tracking,
        clean_before_run=clean_before_run,
    )
