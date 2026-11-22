# bede-core/tests/test_vault_tools.py
import subprocess

import pytest

from bede_core.vault_tools import Vault, VaultError, build_vault_tools


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "vault"
    root.mkdir()
    (root / "note.md").write_text("hello World\nsecond line\n")
    return Vault(str(root))


def tools(vault):
    return {f.__name__: f for f in build_vault_tools(vault)}


@pytest.mark.parametrize("bad", ["../x", "/etc/passwd", ".git/config"])
def test_escape_and_git_blocked(vault, bad):
    with pytest.raises(VaultError):
        vault.read_file(bad)


def test_symlink_escape_blocked(vault, tmp_path):
    outside = tmp_path / "secret.txt"
    outside.write_text("secret")
    (tmp_path / "vault" / "link.md").symlink_to(outside)
    with pytest.raises(VaultError):
        vault.read_file("link.md")


def test_list_and_search(vault):
    assert vault.list_dir() == ["note.md"]
    assert vault.search("WORLD") == ["note.md:1: hello World"]


def test_write_creates_parents(vault):
    vault.write_file("Journal/2026-01-01.md", "hi")
    assert vault.read_file("Journal/2026-01-01.md") == "hi"


def test_write_under_a_file_returns_error_text(vault):
    assert tools(vault)["write_file"]("note.md/child.md", "x").startswith("Error:")


def test_tool_errors_are_text_not_exceptions(vault):
    assert tools(vault)["read_file"]("../x").startswith("Error:")


def test_read_truncates_and_tolerates_binary(vault, tmp_path):
    (tmp_path / "vault" / "big.md").write_text("a" * 30000)
    (tmp_path / "vault" / "bin.md").write_bytes(b"\xff\xfe\x00bad")
    assert "[truncated at 20000 chars]" in vault.read_file("big.md")
    assert vault.read_file("bin.md")


def test_no_delete_tool(vault):
    assert set(tools(vault)) == {
        "list_dir",
        "read_file",
        "write_file",
        "search",
        "commit_and_push",
    }


def test_commit_and_push(tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(remote), str(work)], check=True)
    for key, value in [("user.email", "t@example.com"), ("user.name", "t")]:
        subprocess.run(["git", "-C", str(work), "config", key, value], check=True)
    v = Vault(str(work))
    assert v.commit_and_push("nothing") == "Nothing to commit"
    v.write_file("a/b.md", "hi")
    assert "Committed" in v.commit_and_push("add b")
    log = subprocess.run(
        ["git", "-C", str(remote), "log", "--oneline"], capture_output=True, text=True
    )
    assert "add b" in log.stdout
