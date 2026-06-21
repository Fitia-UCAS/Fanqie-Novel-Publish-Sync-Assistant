from __future__ import annotations

from backend.adapters.fanqie_syncer.fanqie_sync_models import ChapterSyncOptions


def make_chapter_sync_options(
    *,
    chapter_manage_url: str,
    use_ai: bool,
    check_only: bool,
    direction: str,
    verify_after_publish: bool,
    debug_screenshots: bool,
    failure_screenshots: bool,
    git_tracking: bool,
    clean_before_run: bool,
) -> ChapterSyncOptions:
    return ChapterSyncOptions(
        chapter_manage_url=chapter_manage_url,
        use_ai=use_ai,
        check_only=check_only,
        direction=direction,
        verify_after_publish=verify_after_publish,
        debug_screenshots=debug_screenshots,
        failure_screenshots=failure_screenshots,
        git_tracking=git_tracking,
        clean_before_run=clean_before_run,
    )
