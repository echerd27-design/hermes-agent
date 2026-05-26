"""Tests for hermes_cli.jarvis_prime.ledger.

Uses ``tempfile`` directly (rather than the ``tmp_path`` fixture) to
satisfy the wave's explicit acceptance criterion. Pure stdlib — no
third-party imports, no import of ``hermes_cli.jarvis_prime.events``.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

from hermes_cli.jarvis_prime import ledger
from hermes_cli.jarvis_prime.ledger import (
    CorruptLine,
    LedgerRecord,
    ReadResult,
)


@pytest.fixture
def ledger_path() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as raw_dir:
        yield Path(raw_dir) / "ledger.jsonl"


def test_append_then_read_roundtrips_and_auto_stamps_ts(ledger_path: Path) -> None:
    ledger.append(ledger_path, {"type": "decision", "value": 1})

    result = ledger.read(ledger_path)

    assert isinstance(result, ReadResult)
    assert result.corrupt == []
    assert len(result.records) == 1
    record = result.records[0]
    assert record.line_number == 1
    assert record.payload["type"] == "decision"
    assert record.payload["value"] == 1
    assert isinstance(record.payload["ts"], float)


def test_append_preserves_caller_supplied_ts(ledger_path: Path) -> None:
    ledger.append(ledger_path, {"type": "decision", "ts": 12345.0})

    record = ledger.read(ledger_path).records[0]

    assert record.payload["ts"] == 12345.0


def test_append_creates_missing_parent_directories() -> None:
    with tempfile.TemporaryDirectory() as raw_dir:
        nested = Path(raw_dir) / "a" / "b" / "c" / "ledger.jsonl"
        ledger.append(nested, {"type": "decision"})

        assert nested.exists()
        assert len(ledger.read(nested).records) == 1


def test_append_rejects_non_dict_event(ledger_path: Path) -> None:
    with pytest.raises(TypeError):
        ledger.append(ledger_path, ["not", "a", "dict"])  # type: ignore[arg-type]


def test_append_escapes_embedded_newlines_in_string_values(
    ledger_path: Path,
) -> None:
    ledger.append(ledger_path, {"note": "line one\nline two"})
    ledger.append(ledger_path, {"note": "next entry"})

    raw_lines = ledger_path.read_text(encoding="utf-8").splitlines()
    assert len(raw_lines) == 2

    result = ledger.read(ledger_path)
    assert result.corrupt == []
    assert result.records[0].payload["note"] == "line one\nline two"
    assert result.records[1].payload["note"] == "next entry"


def test_read_missing_file_returns_empty_result() -> None:
    with tempfile.TemporaryDirectory() as raw_dir:
        result = ledger.read(Path(raw_dir) / "never-written.jsonl")

    assert result.records == []
    assert result.corrupt == []


def test_read_returns_records_in_append_order(ledger_path: Path) -> None:
    for i in range(5):
        ledger.append(ledger_path, {"type": "decision", "i": i})

    result = ledger.read(ledger_path)

    assert [r.payload["i"] for r in result.records] == [0, 1, 2, 3, 4]
    assert [r.line_number for r in result.records] == [1, 2, 3, 4, 5]


def test_read_skips_blank_lines(ledger_path: Path) -> None:
    ledger.append(ledger_path, {"type": "decision", "i": 0})
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write("\n\n")
    ledger.append(ledger_path, {"type": "decision", "i": 1})

    result = ledger.read(ledger_path)

    assert [r.payload["i"] for r in result.records] == [0, 1]
    assert result.corrupt == []


def test_read_reports_non_json_line_as_corrupt(ledger_path: Path) -> None:
    ledger.append(ledger_path, {"type": "decision", "i": 0})
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write("not json at all\n")
    ledger.append(ledger_path, {"type": "decision", "i": 1})

    result = ledger.read(ledger_path)

    assert [r.payload["i"] for r in result.records] == [0, 1]
    assert len(result.corrupt) == 1
    bad = result.corrupt[0]
    assert isinstance(bad, CorruptLine)
    assert bad.line_number == 2
    assert bad.raw == "not json at all"
    assert bad.error


def test_read_reports_non_dict_json_as_corrupt(ledger_path: Path) -> None:
    ledger.append(ledger_path, {"type": "decision", "i": 0})
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write("42\n")
        fh.write('"a bare string"\n')
        fh.write("[1, 2, 3]\n")

    result = ledger.read(ledger_path)

    assert len(result.records) == 1
    assert result.records[0].payload["i"] == 0
    assert len(result.corrupt) == 3
    for bad in result.corrupt:
        assert "expected JSON object" in bad.error


def test_read_preserves_records_around_corruption(ledger_path: Path) -> None:
    ledger.append(ledger_path, {"type": "decision", "i": 0})
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write("{ broken json\n")
    ledger.append(ledger_path, {"type": "decision", "i": 1})
    ledger.append(ledger_path, {"type": "decision", "i": 2})

    result = ledger.read(ledger_path)

    assert [r.payload["i"] for r in result.records] == [0, 1, 2]
    assert len(result.corrupt) == 1
    assert result.corrupt[0].line_number == 2


def test_tail_returns_last_n_records_in_order(ledger_path: Path) -> None:
    for i in range(5):
        ledger.append(ledger_path, {"type": "decision", "i": i})

    assert [r.payload["i"] for r in ledger.tail(ledger_path, 3)] == [2, 3, 4]
    assert ledger.tail(ledger_path, 0) == []
    assert [r.payload["i"] for r in ledger.tail(ledger_path, 100)] == [
        0,
        1,
        2,
        3,
        4,
    ]


def test_tail_rejects_negative_n(ledger_path: Path) -> None:
    with pytest.raises(ValueError):
        ledger.tail(ledger_path, -1)


def test_filter_by_type_returns_only_matching_records(ledger_path: Path) -> None:
    ledger.append(ledger_path, {"type": "decision", "i": 0})
    ledger.append(ledger_path, {"type": "note", "i": 1})
    ledger.append(ledger_path, {"type": "decision", "i": 2})
    ledger.append(ledger_path, {"i": 3})  # no type at all

    matches = ledger.filter_by_type(ledger_path, "decision")

    assert [r.payload["i"] for r in matches] == [0, 2]
    assert all(isinstance(r, LedgerRecord) for r in matches)


def test_ledger_module_does_not_import_events() -> None:
    """Acceptance criterion: ledger.py must not import events."""
    source = Path(ledger.__file__).read_text(encoding="utf-8")
    # No "from ... events" / "import events" anywhere in the source.
    for line in source.splitlines():
        bare = line.strip()
        if bare.startswith("#"):
            continue
        if bare.startswith("import ") or bare.startswith("from "):
            assert "events" not in bare, (
                f"ledger.py must not import events: {bare!r}"
            )
            assert "job_store" not in bare, (
                f"ledger.py must not import job_store: {bare!r}"
            )


def test_appended_lines_are_valid_json_per_line(ledger_path: Path) -> None:
    """Defence-in-depth: every appended line parses standalone."""
    ledger.append(ledger_path, {"type": "decision", "i": 0})
    ledger.append(ledger_path, {"type": "decision", "i": 1, "nested": {"a": [1, 2]}})

    raw = ledger_path.read_text(encoding="utf-8").splitlines()
    assert len(raw) == 2
    for line in raw:
        parsed = json.loads(line)
        assert isinstance(parsed, dict)
