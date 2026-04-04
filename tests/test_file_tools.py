from typing import Any
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from vnag.tools import file_tools


class FileToolsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()
        self.old_read_paths = file_tools.ALL_READ_PATHS.copy()
        self.old_write_paths = file_tools.WRITE_ALLOWED_PATHS.copy()
        file_tools.ALL_READ_PATHS = {self.root}
        file_tools.WRITE_ALLOWED_PATHS = {self.root}

    def tearDown(self) -> None:
        file_tools.ALL_READ_PATHS = self.old_read_paths
        file_tools.WRITE_ALLOWED_PATHS = self.old_write_paths
        self.temp_dir.cleanup()

    def test_read_file_snippet_returns_line_numbers(self) -> None:
        path = self.root / "sample.txt"
        path.write_text("alpha\nbeta\ngamma\ndelta\n", encoding="utf-8")

        result = file_tools.read_file_snippet(str(path), offset=1, limit=2)

        self.assertEqual(result, "     2\tbeta\n     3\tgamma")

    def test_read_file_snippet_rejects_binary_file(self) -> None:
        path = self.root / "data.bin"
        path.write_bytes(b"\x00\x01\x02")

        result = file_tools.read_file_snippet(str(path))

        self.assertEqual(result, "错误：二进制文件不可读（或包含空字节）。")

    def test_replace_content_rejects_mismatched_occurrences(self) -> None:
        path = self.root / "replace.txt"
        path.write_text("foo\nbar\nfoo\n", encoding="utf-8")

        result = file_tools.replace_content(
            str(path),
            "foo",
            "baz",
            expected_occurrences=1,
        )

        self.assertIn("预期为 1 处", result)
        self.assertEqual(path.read_text(encoding="utf-8"), "foo\nbar\nfoo\n")

    def test_replace_content_replaces_only_first_match(self) -> None:
        path = self.root / "replace_once.txt"
        path.write_text("foo\nbar\nfoo\n", encoding="utf-8")

        result = file_tools.replace_content(
            str(path),
            "foo",
            "baz",
            replace_all=False,
            expected_occurrences=2,
        )

        self.assertIn("仅替换第一处", result)
        self.assertEqual(path.read_text(encoding="utf-8"), "baz\nbar\nfoo\n")

    def test_replace_line_block_replaces_closed_interval(self) -> None:
        path = self.root / "lines.txt"
        path.write_text("1\n2\n3\n4\n5\n", encoding="utf-8")

        result = file_tools.replace_line_block(str(path), 2, 4, "A\nB")

        self.assertIn("第 2 到 4 行", result)
        self.assertEqual(path.read_text(encoding="utf-8"), "1\nA\nB\n5")

    def test_glob_files_requires_directory_path(self) -> None:
        path = self.root / "sample.txt"
        path.write_text("text", encoding="utf-8")

        result = file_tools.glob_files(str(path), "*.txt")

        self.assertEqual(result, f"错误：路径 '{path}' 不是一个有效的目录。")

    def test_search_content_reports_skipped_files(self) -> None:
        good_file = self.root / "good.txt"
        bad_file = self.root / "bad.txt"
        good_file.write_text("needle", encoding="utf-8")
        bad_file.write_text("ignored", encoding="utf-8")
        original_read_text = Path.read_text

        def fake_read_text(
            path_obj: Path,
            *args: Any,
            **kwargs: Any,
        ) -> str:
            if path_obj == bad_file:
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "bad")
            return original_read_text(path_obj, *args, **kwargs)

        with patch.object(Path, "read_text", autospec=True, side_effect=fake_read_text):
            result = file_tools.search_content(str(self.root), "needle")

        self.assertIn(str(good_file.resolve()), result)
        self.assertIn("已跳过 1 个不可读文件。", result)


if __name__ == "__main__":
    unittest.main()
