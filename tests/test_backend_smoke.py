from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.services.service_chapter_formatter import format_chapters
from backend.services.service_chapter_text_parser import parse_chapters, read_chapters
from backend.shared.app.app_paths import get_state_paths


class ChapterParserTest(unittest.TestCase):
    def test_parse_complete_txt_with_emojis(self) -> None:
        text = "第1章 (⌐■_■)五位是来相亲的，谁先介绍自己？\n\n正文一。\n\n第2章 (′?w?)他说的好有道理啊，但我总觉得哪里不对劲\n\n正文二。\n"
        chapters = parse_chapters(text)
        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0].number, 1)
        self.assertIn("(⌐■_■)", chapters[0].title)
        self.assertIn("正文二", chapters[1].body)

    def test_parse_chinese_chapter_numbers(self) -> None:
        chapters = parse_chapters("第一章 风起\n\nA\n\n第十二章 云动\n\nB\n")
        self.assertEqual([chapter.number for chapter in chapters], [1, 12])

    def test_format_chapters_keeps_titles(self) -> None:
        chapters = parse_chapters("第1章 标题？！\n\nA\n")
        self.assertIn("第1章 标题？！", format_chapters(chapters))


class ProjectStructureTest(unittest.TestCase):
    def test_state_paths_exist(self) -> None:
        paths = get_state_paths()
        self.assertIn("chapter_sync_compare", paths)


if __name__ == "__main__":
    unittest.main()
