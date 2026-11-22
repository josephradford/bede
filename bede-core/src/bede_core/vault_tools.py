# bede-core/src/bede_core/vault_tools.py
import subprocess
from collections.abc import Callable
from pathlib import Path

MAX_READ_CHARS = 20000
MAX_SEARCH_RESULTS = 50


class VaultError(Exception):
    pass


class Vault:
    """File access confined to a vault directory. There is no delete operation."""

    def __init__(self, root: str):
        self._root = Path(root).resolve()

    def _resolve(self, rel: str) -> Path:
        path = (self._root / rel).resolve()
        if path != self._root and self._root not in path.parents:
            raise VaultError(f"Path escapes the vault: {rel}")
        if ".git" in path.relative_to(self._root).parts:
            raise VaultError("Access to .git is not allowed")
        return path

    def list_dir(self, rel: str = ".") -> list[str]:
        path = self._resolve(rel)
        if not path.is_dir():
            raise VaultError(f"Not a directory: {rel}")
        return [
            p.name + ("/" if p.is_dir() else "")
            for p in sorted(path.iterdir())
            if p.name != ".git"
        ]

    def read_file(self, rel: str) -> str:
        path = self._resolve(rel)
        if not path.is_file():
            raise VaultError(f"Not a file: {rel}")
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > MAX_READ_CHARS:
            return text[:MAX_READ_CHARS] + f"\n[truncated at {MAX_READ_CHARS} chars]"
        return text

    def write_file(self, rel: str, content: str) -> str:
        path = self._resolve(rel)
        if path == self._root or path.is_dir():
            raise VaultError(f"Not a file path: {rel}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to {rel}"

    def search(self, query: str, rel: str = ".") -> list[str]:
        base = self._resolve(rel)
        needle = query.lower()
        hits: list[str] = []
        for path in sorted(base.rglob("*.md")):
            if ".git" in path.relative_to(self._root).parts:
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for number, line in enumerate(lines, start=1):
                if needle in line.lower():
                    where = path.relative_to(self._root)
                    hits.append(f"{where}:{number}: {line.strip()}")
                    if len(hits) >= MAX_SEARCH_RESULTS:
                        return hits
        return hits

    def commit_and_push(self, message: str) -> str:
        def git(*args: str) -> subprocess.CompletedProcess:
            return subprocess.run(
                ["git", "-C", str(self._root), *args],
                capture_output=True,
                text=True,
                timeout=60,
            )

        git("add", "-A")
        if not git("status", "--porcelain").stdout.strip():
            return "Nothing to commit"
        commit = git("commit", "-m", message)
        if commit.returncode != 0:
            raise VaultError(f"git commit failed: {commit.stderr.strip()}")
        push = git("push")
        if push.returncode != 0:
            raise VaultError(f"git push failed: {push.stderr.strip()}")
        return f"Committed and pushed: {message}"


def build_vault_tools(vault: Vault) -> list[Callable]:
    """Plain functions for the agent. Errors come back as text so the model can recover."""

    def guarded(fn: Callable[[], str]) -> str:
        try:
            return fn()
        except (VaultError, OSError) as e:
            return f"Error: {e}"

    def list_dir(path: str = ".") -> str:
        """List files and folders in a vault directory (folders end with /)."""
        return guarded(lambda: "\n".join(vault.list_dir(path)) or "(empty)")

    def read_file(path: str) -> str:
        """Read a text file from the vault."""
        return guarded(lambda: vault.read_file(path))

    def write_file(path: str, content: str) -> str:
        """Create or overwrite a text file in the vault. Parent folders are created."""
        return guarded(lambda: vault.write_file(path, content))

    def search(query: str, path: str = ".") -> str:
        """Case-insensitive text search over markdown files. Returns file:line: text."""
        return guarded(lambda: "\n".join(vault.search(query, path)) or "No matches")

    def commit_and_push(message: str) -> str:
        """Commit all vault changes with the given message and push them."""
        return guarded(lambda: vault.commit_and_push(message))

    return [list_dir, read_file, write_file, search, commit_and_push]
