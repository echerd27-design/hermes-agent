"""Repo-aware code map for the Hermes Native Engineer.

Walks a repository root, classifies files (source / test / doc / config /
android / risky / other), and extracts top-level Python symbols via the
stdlib ``ast`` module. Stdlib only.
"""
from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from typing import Iterable

DEFAULT_IGNORE: tuple[str, ...] = (
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
)

_RISKY_BASENAMES: frozenset[str] = frozenset({
    "pyproject.toml",
    "uv.lock",
    "poetry.lock",
    "gradle.properties",
})

_RISKY_PREFIXES: tuple[str, ...] = (
    ".github/",
)

_RISKY_NAME_SUBSTRINGS: tuple[str, ...] = (
    "credential",
    "secret",
)

_RISKY_NAME_STARTSWITH: tuple[str, ...] = (
    "dockerfile",
    ".env",
    "settings.gradle",
    "build.gradle",
)

_ANDROID_EXTS: frozenset[str] = frozenset({".kt", ".kts", ".gradle"})
_DOC_EXTS: frozenset[str] = frozenset({".md", ".rst", ".txt"})
_CONFIG_EXTS: frozenset[str] = frozenset({".toml", ".yaml", ".yml", ".cfg", ".ini", ".json"})
_SOURCE_EXTS: frozenset[str] = frozenset(
    {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"}
)

_LANGUAGE_BY_EXT: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".gradle": "gradle",
    ".md": "markdown",
    ".rst": "rst",
    ".txt": "text",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".cfg": "ini",
    ".ini": "ini",
    ".json": "json",
}


@dataclass(frozen=True)
class FileEntry:
    path: str
    kind: str
    language: str
    imports: tuple[str, ...] = ()
    classes: tuple[str, ...] = ()
    functions: tuple[str, ...] = ()
    size_bytes: int = 0


@dataclass(frozen=True)
class RepoMap:
    root: str
    entries: tuple[FileEntry, ...]
    risky: tuple[str, ...] = field(default_factory=tuple)


def classify(rel_path: str) -> str:
    """Return the kind label for a repo-relative path."""
    norm = rel_path.replace("\\", "/")
    basename = norm.rsplit("/", 1)[-1]
    lower_base = basename.lower()
    ext = ""
    if "." in basename:
        ext = "." + basename.rsplit(".", 1)[-1].lower()

    if basename == "AndroidManifest.xml":
        return "android"

    if lower_base in _RISKY_BASENAMES:
        return "risky"
    for prefix in _RISKY_PREFIXES:
        if norm.startswith(prefix):
            return "risky"
    for needle in _RISKY_NAME_SUBSTRINGS:
        if needle in lower_base:
            return "risky"
    for prefix in _RISKY_NAME_STARTSWITH:
        if lower_base.startswith(prefix):
            return "risky"

    if norm.startswith("apps/android/") or ext in _ANDROID_EXTS:
        return "android"

    if basename.startswith("test_") and ext == ".py":
        return "test"
    if norm.startswith("tests/"):
        return "test"

    if ext in _DOC_EXTS or norm.startswith("docs/"):
        return "doc"

    if ext in _CONFIG_EXTS:
        return "config"

    if ext in _SOURCE_EXTS:
        return "source"

    return "other"


def extract_python_symbols(
    source: str,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Return (imports, classes, functions). Never raises on bad source."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return ((), (), ())

    imports: list[str] = []
    classes: list[str] = []
    functions: list[str] = []

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                imports.append(f"{mod}.{alias.name}" if mod else alias.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)

    return (tuple(imports), tuple(classes), tuple(functions))


def _language_for(ext: str) -> str:
    return _LANGUAGE_BY_EXT.get(ext, "")


def _should_ignore_dir(name: str, ignore: Iterable[str]) -> bool:
    return name in set(ignore)


def scan(root: str, ignore: Iterable[str] = DEFAULT_IGNORE) -> RepoMap:
    """Walk ``root`` and produce a RepoMap. Stdlib only."""
    root_abs = os.path.abspath(root)
    entries: list[FileEntry] = []
    risky: list[str] = []
    ignore_set = set(ignore)

    for dirpath, dirnames, filenames in os.walk(root_abs):
        # Prune ignored directories in-place.
        dirnames[:] = [d for d in dirnames if not _should_ignore_dir(d, ignore_set)]

        for fname in filenames:
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root_abs).replace(os.sep, "/")
            ext = ""
            if "." in fname:
                ext = "." + fname.rsplit(".", 1)[-1].lower()
            kind = classify(rel)

            imports: tuple[str, ...] = ()
            classes: tuple[str, ...] = ()
            functions: tuple[str, ...] = ()

            if ext == ".py":
                try:
                    with open(full, "r", encoding="utf-8", errors="replace") as fh:
                        source = fh.read()
                    imports, classes, functions = extract_python_symbols(source)
                except OSError:
                    pass

            try:
                size = os.path.getsize(full)
            except OSError:
                size = 0

            entry = FileEntry(
                path=rel,
                kind=kind,
                language=_language_for(ext),
                imports=imports,
                classes=classes,
                functions=functions,
                size_bytes=size,
            )
            entries.append(entry)
            if kind == "risky":
                risky.append(rel)

    entries.sort(key=lambda e: e.path)
    risky.sort()
    return RepoMap(root=root_abs, entries=tuple(entries), risky=tuple(risky))
