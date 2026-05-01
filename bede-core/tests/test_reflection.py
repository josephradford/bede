import os
import pytest
from unittest.mock import patch

from bede_core.reflection import append_correction


class TestReflection:
    def test_creates_file_if_missing(self, tmp_path):
        bede_dir = tmp_path / "Bede"
        bede_dir.mkdir()
        path = str(bede_dir / "reflection-memory.md")

        with patch("bede_core.reflection._git_commit_push"):
            append_correction("Fix the tone", str(tmp_path), "Australia/Sydney")

        assert os.path.isfile(path)
        content = open(path).read()
        assert "Fix the tone" in content
        assert "# Reflection Memory" in content

    def test_appends_to_existing_file(self, tmp_path):
        bede_dir = tmp_path / "Bede"
        bede_dir.mkdir()
        path = bede_dir / "reflection-memory.md"
        path.write_text("# Reflection Memory\n\n## Corrections\n\n- [2026-04-30 21:00] Old correction\n")

        with patch("bede_core.reflection._git_commit_push"):
            append_correction("New correction", str(tmp_path), "Australia/Sydney")

        content = path.read_text()
        assert "Old correction" in content
        assert "New correction" in content

    def test_includes_timestamp(self, tmp_path):
        bede_dir = tmp_path / "Bede"
        bede_dir.mkdir()

        with patch("bede_core.reflection._git_commit_push"):
            append_correction("Something", str(tmp_path), "Australia/Sydney")

        content = (bede_dir / "reflection-memory.md").read_text()
        assert "2026-" in content
