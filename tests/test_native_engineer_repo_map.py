"""Tests for hermes_cli.native_engineer.repo_map."""
from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.native_engineer.repo_map import (
    classify,
    extract_python_symbols,
    scan,
)


def test_classify_risky_pyproject():
    assert classify("pyproject.toml") == "risky"
    assert classify("uv.lock") == "risky"
    assert classify("poetry.lock") == "risky"


def test_classify_risky_github_workflows():
    assert classify(".github/workflows/ci.yml") == "risky"


def test_classify_risky_env_and_credentials():
    assert classify(".env") == "risky"
    assert classify(".env.local") == "risky"
    assert classify("config/aws_credentials.json") == "risky"
    assert classify("my_secret_token.txt") == "risky"


def test_classify_risky_gradle():
    assert classify("settings.gradle.kts") == "risky"
    assert classify("app/build.gradle") == "risky"


def test_classify_android_by_path_and_ext():
    assert classify("apps/android/foo.kt") == "android"
    assert classify("foo.kts") == "android"
    assert classify("app/src/main/AndroidManifest.xml") == "android"


def test_classify_test_paths():
    assert classify("tests/test_foo.py") == "test"
    assert classify("subdir/test_bar.py") == "test"


def test_classify_doc_and_config():
    assert classify("docs/index.md") == "doc"
    assert classify("README.rst") == "doc"
    assert classify("config/app.yaml") == "config"


def test_classify_source_and_other():
    assert classify("hermes_cli/foo.py") == "source"
    assert classify("frontend/app.tsx") == "source"
    assert classify("assets/logo.png") == "other"


def test_extract_python_symbols_returns_imports_classes_functions():
    src = (
        "import os\n"
        "from collections import OrderedDict\n"
        "class Foo:\n"
        "    pass\n"
        "def bar():\n"
        "    return 1\n"
        "async def baz():\n"
        "    return 2\n"
    )
    imports, classes, functions = extract_python_symbols(src)
    assert "os" in imports
    assert "collections.OrderedDict" in imports
    assert classes == ("Foo",)
    assert "bar" in functions and "baz" in functions


def test_extract_python_symbols_handles_syntax_error():
    imports, classes, functions = extract_python_symbols("def broken(:\n")
    assert imports == ()
    assert classes == ()
    assert functions == ()


def test_scan_classifies_curated_tree(tmp_path: Path):
    (tmp_path / "hermes_cli").mkdir()
    (tmp_path / "hermes_cli" / "mod.py").write_text("import sys\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("# guide\n", encoding="utf-8")
    (tmp_path / "config.yaml").write_text("k: v\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / ".env").write_text("X=1\n", encoding="utf-8")
    (tmp_path / "apps" / "android").mkdir(parents=True)
    (tmp_path / "apps" / "android" / "App.kt").write_text("// kt\n", encoding="utf-8")

    rmap = scan(str(tmp_path))
    by_path = {e.path: e for e in rmap.entries}

    assert by_path["hermes_cli/mod.py"].kind == "source"
    assert by_path["tests/test_x.py"].kind == "test"
    assert by_path["docs/guide.md"].kind == "doc"
    assert by_path["config.yaml"].kind == "config"
    assert by_path["pyproject.toml"].kind == "risky"
    assert by_path[".env"].kind == "risky"
    assert by_path["apps/android/App.kt"].kind == "android"

    assert "pyproject.toml" in rmap.risky
    assert ".env" in rmap.risky
    assert "sys" in by_path["hermes_cli/mod.py"].imports


def test_scan_skips_default_ignored_dirs(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref:\n", encoding="utf-8")
    (tmp_path / "src.py").write_text("x = 1\n", encoding="utf-8")
    rmap = scan(str(tmp_path))
    paths = {e.path for e in rmap.entries}
    assert "src.py" in paths
    assert not any(p.startswith(".git/") for p in paths)
