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


def make_remote_and_clone(tmp_path, name="work"):
    """A bare remote seeded with one commit, plus a configured clone of it."""
    remote = tmp_path / "remote.git"
    if not remote.exists():
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
        seed = tmp_path / "seed"
        subprocess.run(["git", "clone", "-q", str(remote), str(seed)], check=True)
        configure_git(seed)
        (seed / "README.md").write_text("seed")
        subprocess.run(["git", "-C", str(seed), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(seed), "commit", "-q", "-m", "seed"], check=True
        )
        subprocess.run(["git", "-C", str(seed), "push", "-q"], check=True)
    clone = tmp_path / name
    subprocess.run(["git", "clone", "-q", str(remote), str(clone)], check=True)
    configure_git(clone)
    return remote, clone


def configure_git(path):
    for key, value in [("user.email", "t@example.com"), ("user.name", "t")]:
        subprocess.run(["git", "-C", str(path), "config", key, value], check=True)


def git_out(path, *args):
    return subprocess.run(
        ["git", "-C", str(path), *args], capture_output=True, text=True, check=True
    ).stdout


def test_push_succeeds_when_remote_is_ahead(tmp_path):
    remote, work = make_remote_and_clone(tmp_path, "work")
    _, other = make_remote_and_clone(tmp_path, "other")
    (other / "from-mac.md").write_text("mac")
    git_out(other, "add", "-A")
    git_out(other, "commit", "-q", "-m", "mac edit")
    git_out(other, "push", "-q")

    v = Vault(str(work))
    v.write_file("from-bede.md", "bede")
    assert "Committed" in v.commit_and_push("bede edit")

    log = git_out(remote, "log", "--oneline")
    assert "mac edit" in log and "bede edit" in log
    assert (work / "from-mac.md").exists()


def test_commit_stages_only_files_written_through_the_vault(tmp_path):
    _, work = make_remote_and_clone(tmp_path)
    v = Vault(str(work))
    v.write_file("mine.md", "mine")
    (work / "stray.txt").write_text("someone else's half-written file")

    v.commit_and_push("mine only")

    assert git_out(work, "show", "--name-only", "--format=", "HEAD").split() == [
        "mine.md"
    ]
    assert "stray.txt" in git_out(work, "status", "--porcelain")


def test_concurrent_commits_all_land(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    remote, work = make_remote_and_clone(tmp_path)
    v = Vault(str(work))

    def job(i):
        v.write_file(f"note-{i}.md", str(i))
        return v.commit_and_push(f"note {i}")

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(job, range(4)))

    assert all(not r.startswith("Error") for r in results)
    landed = git_out(remote, "ls-tree", "-r", "--name-only", "HEAD").split()
    assert {f"note-{i}.md" for i in range(4)} <= set(landed)


def test_failed_push_is_retried_on_the_next_call(tmp_path):
    remote, work = make_remote_and_clone(tmp_path)
    v = Vault(str(work))
    git_out(work, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    v.write_file("a.md", "a")
    with pytest.raises(VaultError):
        v.commit_and_push("first try")

    git_out(work, "remote", "set-url", "origin", str(remote))
    assert "Committed" in v.commit_and_push("second try")
    assert "first try" in git_out(remote, "log", "--oneline")
