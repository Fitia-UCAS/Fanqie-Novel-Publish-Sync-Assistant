from __future__ import annotations

from pathlib import Path

from backend.services.novel_text.chapter_parser import ChapterBlock, chapters_by_number, parse_chapters_file

Chapter = ChapterBlock


def parse_chapters(novel_file: Path) -> list[Chapter]:
    return parse_chapters_file(novel_file)


def load_local_chapters_by_number(novel_file: Path, chapters: list[int]) -> dict[int, Chapter]:
    local_chapters = chapters_by_number(parse_chapters(novel_file), "本地 txt")
    missing_local = [no for no in chapters if no not in local_chapters]
    if missing_local:
        raise RuntimeError(f"本地 txt 中没有找到章节：{', '.join(str(no) for no in missing_local)}")
    return {no: local_chapters[no] for no in chapters}
