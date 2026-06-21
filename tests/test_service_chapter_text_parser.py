from __future__ import annotations

from pathlib import Path

from tests.test_backend_smoke import ChapterParserTest
from backend.services.novel_text.text_splitter import NovelSplitOptions, split_novel_text


def _write_novel(path: Path, chapter_numbers: list[int]) -> None:
    parts = ["《测试小说》\n作者：测试\n"]
    for number in chapter_numbers:
        parts.append(f"第{number}章 测试标题{number}\n\n正文{number}\n")
    path.write_text("\n".join(parts), encoding="utf-8")


def test_chapter_count_split_uses_source_name_and_chapter_number_width(tmp_path: Path) -> None:
    source = tmp_path / "测试小说.txt"
    _write_novel(source, [1, 2, 593, 1208])

    result = split_novel_text(
        NovelSplitOptions(
            input_file=source,
            output_dir=tmp_path / "out",
            split_mode="chapter_count",
            chapters_per_file=2,
        )
    )

    assert [item.path.name for item in result.files] == [
        "测试小说_0001-0002.txt",
        "测试小说_0593-1208.txt",
    ]


def test_size_split_uses_source_name_and_part_index(tmp_path: Path) -> None:
    source = tmp_path / "测试小说.txt"
    _write_novel(source, [1, 2, 3])

    result = split_novel_text(
        NovelSplitOptions(
            input_file=source,
            output_dir=tmp_path / "out",
            split_mode="size",
            max_size_mb=0.00001,
        )
    )

    assert [item.path.name for item in result.files] == [
        "测试小说_001.txt",
        "测试小说_002.txt",
        "测试小说_003.txt",
    ]


def test_legacy_split_modes_fall_back_to_chapter_count(tmp_path: Path) -> None:
    source = tmp_path / "测试小说.txt"
    _write_novel(source, [1, 2, 3, 4])

    result = split_novel_text(
        NovelSplitOptions(
            input_file=source,
            output_dir=tmp_path / "out",
            split_mode="line",
            chapters_per_file=2,
        )
    )

    assert result.mode == "chapter_count"
    assert [item.path.name for item in result.files] == ["测试小说_1-2.txt", "测试小说_3-4.txt"]
