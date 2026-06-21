from __future__ import annotations

from backend.adapters.fanqie_publisher.fanqie_publish_creator import create_remote_chapter_editor
from backend.adapters.fanqie_publisher.fanqie_publish_submitter import publish_after_save
from backend.adapters.fanqie_publisher.fanqie_publish_models import ChapterPublishResult
from backend.adapters.fanqie_web.models import RemoteChapterEditor
from backend.adapters.fanqie_publisher.fanqie_publish_service import run_multi_chapter_publish

__all__ = [
    "RemoteChapterEditor",
    "create_remote_chapter_editor",
    "publish_after_save",
    "ChapterPublishResult",
    "run_multi_chapter_publish",
]
