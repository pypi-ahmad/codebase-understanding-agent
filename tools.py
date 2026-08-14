"""Filesystem tools: clone GitHub repos, extract zips, scan local folders."""

from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from config import IGNORED_DIR_NAMES, KEY_FILE_PRIORITY

GITHUB_URL_RE = re.compile(
    r"^https://github\.com/[\w.\-]+/[\w.\-]+(?:\.git)?/?$"
)

TEMP_ROOT = Path(tempfile.gettempdir()) / "codebase_understanding_agent"


class ToolError(Exception):
    """Raised for user-facing failures: bad URL, bad zip, missing path."""


def validate_github_url(url: str) -> str:
    url = url.strip()
    if not GITHUB_URL_RE.match(url):
        raise ToolError(
            "Not a valid public GitHub repo URL. Expected: https://github.com/<owner>/<repo>"
        )
    return url


def clone_repo(url: str) -> Path:
    """Shallow-clone a public GitHub repo into a fresh temp dir."""
    import git  # GitPython

    url = validate_github_url(url)
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    dest = Path(tempfile.mkdtemp(prefix="repo_", dir=TEMP_ROOT))
    try:
        git.Repo.clone_from(url, dest, depth=1)
    except git.GitCommandError as e:
        shutil.rmtree(dest, ignore_errors=True)
        stderr = (e.stderr or str(e)).strip()
        if "not found" in stderr.lower() or "repository not found" in stderr.lower():
            raise ToolError(
                f"Repository not found or private: {url}"
            ) from e
        raise ToolError(f"Git clone failed: {stderr[:400]}") from e
    except Exception as e:
        shutil.rmtree(dest, ignore_errors=True)
        raise ToolError(f"Git clone failed: {e}") from e
    return dest


def validate_local_path(path_str: str) -> Path:
    path = Path(path_str.strip().strip('"')).expanduser()
    if not path.exists():
        raise ToolError(f"Path does not exist: {path}")
    if not path.is_dir():
        raise ToolError(f"Path is not a directory: {path}")
    return path.resolve()


def extract_zip(zip_bytes: bytes, original_name: str = "upload.zip") -> Path:
    """Safely extract an uploaded zip into a fresh temp dir (zip-slip guarded)."""
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    dest = Path(tempfile.mkdtemp(prefix="zip_", dir=TEMP_ROOT))
    zip_path = dest / "_upload.zip"
    zip_path.write_bytes(zip_bytes)

    try:
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.infolist():
                member_path = (dest / member.filename).resolve()
                if not str(member_path).startswith(str(dest.resolve())):
                    raise ToolError(f"Unsafe path in zip, aborted: {member.filename}")
            zf.extractall(dest)
    except zipfile.BadZipFile as e:
        shutil.rmtree(dest, ignore_errors=True)
        raise ToolError(f"Not a valid zip file: {original_name}") from e
    finally:
        zip_path.unlink(missing_ok=True)

    # If the zip contains one top-level folder, treat that as the root.
    entries = [p for p in dest.iterdir()]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return dest


def _iter_files(root: Path, max_entries: int):
    count = 0
    for path in sorted(root.rglob("*")):
        if any(part in IGNORED_DIR_NAMES for part in path.relative_to(root).parts[:-1]):
            continue
        if path.is_dir() and path.name in IGNORED_DIR_NAMES:
            continue
        if path.is_file():
            count += 1
            if count > max_entries:
                return
            yield path


def build_file_tree(root: Path, max_depth: int = 4, max_entries: int = 800) -> tuple[str, list[Path]]:
    """Return (rendered tree text, list of file paths considered)."""
    files: list[Path] = []
    lines: list[str] = [root.name + "/"]
    truncated = False

    for path in _iter_files(root, max_entries):
        rel = path.relative_to(root)
        if len(rel.parts) > max_depth:
            continue
        files.append(path)
        indent = "  " * (len(rel.parts) - 1)
        lines.append(f"{indent}{rel.name}")

    if sum(1 for _ in root.rglob("*")) > max_entries:
        truncated = True

    tree_text = "\n".join(lines)
    if truncated:
        tree_text += "\n... (truncated)"
    return tree_text, files


def identify_key_files(files: list[Path], root: Path, max_files: int) -> list[dict]:
    def score(path: Path) -> tuple[int, int, str]:
        rel = path.relative_to(root)
        name = path.name.lower()
        try:
            priority = KEY_FILE_PRIORITY.index(name)
        except ValueError:
            priority = len(KEY_FILE_PRIORITY) + (0 if name.endswith((".md",)) else 5)
        return (priority, len(rel.parts), str(rel).lower())

    candidates = [f for f in files if f.is_file()]
    candidates.sort(key=score)
    top = candidates[:max_files]
    return [{"path": str(f.relative_to(root)), "abs_path": str(f)} for f in top]


def read_file_text(path: Path, max_chars: int = 6000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[unreadable: {e}]"
    if len(text) > max_chars:
        return text[:max_chars] + "\n... (truncated)"
    return text


def cleanup_temp_dir(path: Path | str | None) -> None:
    """Delete a temp clone/extract dir. Refuses to touch anything outside TEMP_ROOT."""
    if not path:
        return
    path = Path(path).resolve()
    try:
        path.relative_to(TEMP_ROOT.resolve())
    except ValueError:
        return  # not one of ours (e.g. a local user folder) -> never delete
    shutil.rmtree(path.parent if path.parent != TEMP_ROOT else path, ignore_errors=True)
