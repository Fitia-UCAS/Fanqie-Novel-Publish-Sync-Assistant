from __future__ import annotations

from pathlib import Path

from backend.shared.app.app_paths import CHAPTER_SYNC_BACKUP_DIR
from backend.services.novel_text.chapter_parser import ChapterBlock, chapters_by_number, parse_chapter_blocks, parse_chapters_file
from backend.shared.text_file.text_file_storage import numbered_backup_path, read_text_and_encoding, write_text
from backend.services.novel_text.text_normalizer import chinese_to_int, format_novel_text, normalize_chapter_line_breaks, same_text, strip_chapter_prefix as common_strip_chapter_prefix

Chapter = ChapterBlock


def cn_to_int(s: str) -> int:
    value = chinese_to_int(s)
    if value is None:
        raise ValueError(f"无法识别章节数字：{s}")
    return value


def read_text_with_fallback(path: Path) -> str:
    text, _encoding = read_text_and_encoding(path)
    return text


def parse_chapters(novel_file: Path) -> list[Chapter]:
    return parse_chapters_file(novel_file)


def get_local_chapter(novel_file: Path, no: int) -> Chapter:
    by_number = chapters_by_number(parse_chapters(novel_file), "本地 txt")
    chapter = by_number.get(no)
    if chapter is None:
        raise RuntimeError(f"本地 txt 中没有找到第 {no} 章")
    return chapter


def strip_chapter_prefix(title: str, no: int) -> str:
    return common_strip_chapter_prefix(title)


def format_chapter_block(title_line: str, body: str) -> str:
    raw = f"{(title_line or '').strip()}\n\n{body or ''}\n"
    return format_novel_text(raw, use_separator=False).rstrip() + "\n"


def backup_local_file(novel_file: Path, no: int, chapter_text: str, encoding: str) -> Path:
    CHAPTER_SYNC_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = numbered_backup_path(
        novel_file,
        CHAPTER_SYNC_BACKUP_DIR,
        label=f"第{no:03d}章",
        suffix=f"{novel_file.suffix}.bak",
    )
    write_text(backup_path, format_novel_text(chapter_text, use_separator=False), encoding=encoding)
    return backup_path


def replace_local_chapter(novel_file: Path, no: int, title: str, content: str) -> Path:
    raw_text, encoding = read_text_and_encoding(novel_file)





    text = normalize_chapter_line_breaks(raw_text)
    chapters = parse_chapter_blocks(text)
    if not chapters:
        raise RuntimeError("没有解析到章节标题。请确认格式类似：第1章 标题")
    by_number = chapters_by_number(chapters, "本地 txt")
    target = by_number.get(no)
    if target is None:
        raise RuntimeError(f"本地 txt 中没有找到第 {no} 章，无法写回平台内容。")

    old_header = target.title.rstrip()
    old_chapter_block = text[target.start : target.end]
    clean_title = strip_chapter_prefix(title, no)
    header = old_header if same_text(target.subtitle, clean_title) else f"第{no}章 {clean_title}".rstrip()


    new_block = format_chapter_block(header, content)
    if target.end < len(text):
        new_block += "\n"

    backup_path = backup_local_file(novel_file, no, old_chapter_block, encoding)
    new_text = text[: target.start] + new_block + text[target.end :]
    write_text(novel_file, new_text, encoding=encoding)
    return backup_path


def full_title(no: int, title: str) -> str:
    clean_title = common_strip_chapter_prefix(title)
    return f"第{no}章 {clean_title}".strip()
