from __future__ import annotations


from backend.shared.plain_text.plain_text_formatting import collapse_blank_lines
from backend.models.chapter import Chapter


def format_chapter(chapter: Chapter) -> str:
    body = collapse_blank_lines(chapter.body, max_blank_lines=1).strip()
    return f"{chapter.heading}\n\n{body}\n"


def format_chapters(chapters: list[Chapter]) -> str:
    return "\n".join(format_chapter(chapter).strip() for chapter in chapters).strip() + "\n"


