"""Tests for hermes_cli.context.context_engine.

Covers each ``compress_*`` rule plus the acceptance-mandated guarantees:

- Stack traces preserve every frame and recursive runs are collapsed.
- Test ids are preserved in payload and evidence.
- Obvious secrets never leak into payload, evidence, or warnings.
"""

import json

import pytest

from hermes_cli.context import (
    COMPRESSORS,
    ContextPacket,
    compress_diff,
    compress_json,
    compress_log,
    compress_markdown,
    compress_stack_trace,
    compress_test_output,
    compress_text,
)


# ---------------------------------------------------------------------------
# compress_text
# ---------------------------------------------------------------------------

class TestCompressText:
    def test_short_input_passes_through(self):
        p = compress_text("hello world")
        assert isinstance(p, ContextPacket)
        assert p.source_type == "text"
        assert p.payload == "hello world"
        assert p.compressed_length == len("hello world")

    def test_long_input_truncated_with_marker(self):
        text = "abcdefghij\n" * 600  # ~6.6k chars
        p = compress_text(text, max_chars=1000)
        assert "[... " in p.payload and "chars elided ...]" in p.payload
        assert any("truncated" in w for w in p.warnings)

    def test_blank_line_runs_collapsed(self):
        p = compress_text("line1\n\n\n\n\nline2")
        assert p.payload == "line1\n\nline2"

    def test_evidence_extracted_from_file_path_and_line_ref(self):
        p = compress_text("see hermes_cli/foo.py:42 in def bar():\n  pass")
        kinds = {kind for kind, _ in p.preserved_evidence}
        assert "line_ref" in kinds
        assert "function_name" in kinds

    def test_artifact_ref_round_trips(self):
        p = compress_text("hi", artifact_ref="stash://abc")
        assert p.artifact_ref == "stash://abc"

    def test_empty_input(self):
        p = compress_text("")
        assert p.payload == ""
        assert p.original_length == 0
        assert p.compression_ratio == 1.0


# ---------------------------------------------------------------------------
# compress_markdown
# ---------------------------------------------------------------------------

class TestCompressMarkdown:
    def test_headings_preserved(self):
        md = "# Title\n## Sub\n### Deep"
        p = compress_markdown(md)
        assert "# Title" in p.payload
        assert "## Sub" in p.payload
        assert "### Deep" in p.payload

    def test_fenced_code_block_preserved_verbatim(self):
        md = (
            "# Title\n\n"
            "```python\n"
            "def foo():\n"
            "    return 42\n"
            "```\n"
        )
        p = compress_markdown(md)
        assert "def foo():" in p.payload
        assert "return 42" in p.payload
        # Function name surfaces as evidence too.
        kinds = {kind for kind, _ in p.preserved_evidence}
        assert "function_name" in kinds

    def test_long_prose_paragraph_collapsed(self):
        prose = "\n".join(f"prose-line-{i}" for i in range(20))
        md = f"# Title\n\n{prose}\n"
        p = compress_markdown(md)
        assert "prose-line-0" in p.payload
        assert "prose-line-19" in p.payload
        assert "[... " in p.payload and "lines elided ...]" in p.payload
        assert "prose-line-10" not in p.payload


# ---------------------------------------------------------------------------
# compress_json
# ---------------------------------------------------------------------------

class TestCompressJSON:
    def test_accepts_str_and_dict(self):
        d = {"a": 1, "b": "x"}
        p_dict = compress_json(d)
        p_str = compress_json(json.dumps(d))
        assert json.loads(p_dict.payload) == d
        assert json.loads(p_str.payload) == d

    def test_large_array_summarized(self):
        big = {"items": list(range(50))}
        p = compress_json(big)
        parsed = json.loads(p.payload)
        assert len(parsed["items"]) == 4  # first, second, marker, last
        assert any("elided" in str(item) for item in parsed["items"])

    def test_error_string_in_nested_dict_preserved_as_evidence(self):
        data = {
            "result": "failure",
            "detail": {"error": "RuntimeError: bad path /etc/foo.conf:12"},
        }
        p = compress_json(data)
        kinds = {kind for kind, _ in p.preserved_evidence}
        assert "line_ref" in kinds

    def test_invalid_json_str_falls_back_to_text(self):
        p = compress_json("{not valid json,")
        assert p.source_type == "json"
        assert any("json parse failed" in w for w in p.warnings)


# ---------------------------------------------------------------------------
# compress_log
# ---------------------------------------------------------------------------

class TestCompressLog:
    def test_ansi_stripped(self):
        log = "\x1b[31mERROR\x1b[0m something broke"
        p = compress_log(log)
        assert "\x1b" not in p.payload
        assert "ERROR" in p.payload

    def test_repeated_lines_collapsed_with_count_marker(self):
        log = "spam\nspam\nspam\nspam\ndone"
        p = compress_log(log)
        assert "spam (× 4)" in p.payload
        assert "done" in p.payload
        assert any("deduplicated" in w for w in p.warnings)

    def test_error_lines_kept_verbatim_even_if_repeated(self):
        log = "INFO ok\nERROR boom\nERROR boom\nERROR boom\nINFO ok"
        p = compress_log(log)
        # Each ERROR line must appear individually — they are never deduped.
        assert p.payload.count("ERROR boom") == 3

    def test_warn_critical_traceback_lines_preserved(self):
        for hot in ("WARN x", "WARNING y", "CRITICAL z", "FATAL boom", "Traceback (most recent call last):"):
            p = compress_log(f"{hot}\n{hot}")
            assert p.payload.count(hot) == 2, hot


# ---------------------------------------------------------------------------
# compress_diff
# ---------------------------------------------------------------------------

class TestCompressDiff:
    def test_diff_headers_preserved(self):
        diff = (
            "diff --git a/foo.py b/foo.py\n"
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "@@ -1,3 +1,3 @@\n"
            " unchanged-1\n"
            " unchanged-2\n"
            " unchanged-3\n"
            " unchanged-4\n"
            "-old line\n"
            "+new line\n"
        )
        p = compress_diff(diff)
        for header in ("diff --git a/foo.py b/foo.py", "--- a/foo.py", "+++ b/foo.py", "@@ -1,3 +1,3 @@"):
            assert header in p.payload
        assert "-old line" in p.payload
        assert "+new line" in p.payload

    def test_unchanged_context_runs_collapsed(self):
        diff = (
            "@@ -1,7 +1,7 @@\n"
            " ctx-a\n"
            " ctx-b\n"
            " ctx-c\n"
            " ctx-d\n"
            " ctx-e\n"
            "-old\n"
            "+new\n"
        )
        p = compress_diff(diff)
        assert "[... " in p.payload and "unchanged lines ...]" in p.payload
        assert any("collapsed" in w for w in p.warnings)


# ---------------------------------------------------------------------------
# compress_test_output
# ---------------------------------------------------------------------------

class TestCompressTestOutput:
    _SAMPLE = (
        "============================= test session starts ==============================\n"
        "collected 3 items\n\n"
        "tests/test_foo.py::test_one PASSED                                       [ 33%]\n"
        "tests/test_foo.py::test_two FAILED                                       [ 66%]\n"
        "..F.                                                                     [100%]\n\n"
        "=================================== FAILURES ===================================\n"
        "_________________________________ test_two _____________________________________\n"
        "Traceback (most recent call last):\n"
        '  File "tests/test_foo.py", line 12, in test_two\n'
        "    assert 1 == 2\n"
        "AssertionError: 1 != 2\n\n"
        "FAILED tests/test_foo.py::test_two - AssertionError: 1 != 2\n"
        "PASSED tests/test_foo.py::test_one\n"
    )

    def test_failed_test_ids_preserved_in_payload(self):
        p = compress_test_output(self._SAMPLE)
        assert "FAILED tests/test_foo.py::test_two" in p.payload
        assert "PASSED tests/test_foo.py::test_one" in p.payload

    def test_failed_test_ids_preserved_in_evidence_as_test_id_kind(self):
        p = compress_test_output(self._SAMPLE)
        test_ids = {snippet for kind, snippet in p.preserved_evidence if kind == "test_id"}
        assert "tests/test_foo.py::test_two" in test_ids
        assert "tests/test_foo.py::test_one" in test_ids

    def test_traceback_block_preserved_verbatim(self):
        p = compress_test_output(self._SAMPLE)
        for chunk in (
            "Traceback (most recent call last):",
            'File "tests/test_foo.py", line 12, in test_two',
            "assert 1 == 2",
            "AssertionError: 1 != 2",
        ):
            assert chunk in p.payload, chunk

    def test_progress_dots_dropped(self):
        p = compress_test_output(self._SAMPLE)
        assert "..F." not in p.payload


# ---------------------------------------------------------------------------
# compress_stack_trace — acceptance-mandated coverage
# ---------------------------------------------------------------------------

class TestCompressStackTrace:
    _RECURSIVE = (
        "Traceback (most recent call last):\n"
        '  File "app.py", line 12, in main\n'
        "    return recurse(0)\n"
        '  File "app.py", line 5, in recurse\n'
        "    return recurse(n + 1)\n"
        '  File "app.py", line 5, in recurse\n'
        "    return recurse(n + 1)\n"
        '  File "app.py", line 5, in recurse\n'
        "    return recurse(n + 1)\n"
        '  File "app.py", line 5, in recurse\n'
        "    return recurse(n + 1)\n"
        "RecursionError: maximum recursion depth exceeded"
    )

    _MULTI_FRAME = (
        "Traceback (most recent call last):\n"
        '  File "a.py", line 1, in outer\n'
        "    inner()\n"
        '  File "b.py", line 2, in inner\n'
        "    deeper()\n"
        '  File "c.py", line 3, in deeper\n'
        "    raise ValueError('boom')\n"
        "ValueError: boom"
    )

    def test_every_file_line_frame_preserved_verbatim(self):
        p = compress_stack_trace(self._MULTI_FRAME)
        for frame in (
            'File "a.py", line 1, in outer',
            'File "b.py", line 2, in inner',
            'File "c.py", line 3, in deeper',
        ):
            assert frame in p.payload, frame

    def test_recursive_frames_collapsed_with_count_marker(self):
        p = compress_stack_trace(self._RECURSIVE)
        assert 'File "app.py", line 5, in recurse' in p.payload
        assert "(frame repeated " in p.payload
        assert "more time" in p.payload
        assert any("collapsed" in w for w in p.warnings)

    def test_final_exception_line_preserved(self):
        p = compress_stack_trace(self._RECURSIVE)
        assert "RecursionError: maximum recursion depth exceeded" in p.payload
        kinds = {kind for kind, _ in p.preserved_evidence}
        assert "error_message" in kinds
        assert "stack_frame" in kinds

    def test_unique_frames_not_collapsed(self):
        p = compress_stack_trace(self._MULTI_FRAME)
        assert "frame repeated" not in p.payload


# ---------------------------------------------------------------------------
# Secrets-never-leak — acceptance-mandated coverage (42 cases)
# ---------------------------------------------------------------------------

_SECRET_SAMPLES = [
    ("openai_sk", "sk-abcdef0123456789xyz"),
    ("github_pat", "ghp_0123456789abcdefXYZ"),
    ("aws_key", "AKIAIOSFODNN7EXAMPLE"),
    (
        "jwt",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NSJ9.SflKxwRJSMeKKF2QT4fwpMeJf36",
    ),
    ("auth_bearer", "Authorization: Bearer opaque-token-1234567890ABC"),
    (
        "private_key",
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHH\n"
        "-----END RSA PRIVATE KEY-----",
    ),
]


def _all_compressor_pairs():
    """Yield (compressor_name, compressor_fn, secret_label, secret_value)."""

    for name, fn in COMPRESSORS:
        for label, value in _SECRET_SAMPLES:
            yield pytest.param(name, fn, label, value, id=f"{name}-{label}")


class TestSecretsNeverLeak:
    @pytest.mark.parametrize("name,fn,label,value", list(_all_compressor_pairs()))
    def test_secret_value_never_in_payload(self, name, fn, label, value):
        host = (
            "context line 1\n"
            f"leak={value}\n"
            "context line 2\n"
        )
        if name == "json":
            packet = fn(f'{{"data": "{value.replace(chr(10), " ")}"}}')
        else:
            packet = fn(host)
        # The raw secret value must NOT appear in the compressed payload.
        # We compare against the longest distinctive run of the secret to
        # avoid false negatives from short overlapping substrings; the
        # primary signal is "raw token absent + redacted-count warning".
        distinct = value.splitlines()[0]
        assert distinct not in packet.payload, f"{name}/{label} leaked: {distinct!r}"

    @pytest.mark.parametrize("name,fn,label,value", list(_all_compressor_pairs()))
    def test_redaction_warning_emitted(self, name, fn, label, value):
        host = (
            "context line 1\n"
            f"leak={value}\n"
            "context line 2\n"
        )
        if name == "json":
            packet = fn(f'{{"data": "{value.replace(chr(10), " ")}"}}')
        else:
            packet = fn(host)
        assert any("redacted" in w for w in packet.warnings), (
            f"{name}/{label} missing redaction warning. warnings={packet.warnings!r}"
        )

    @pytest.mark.parametrize("name,fn,label,value", list(_all_compressor_pairs()))
    def test_secret_value_never_in_evidence(self, name, fn, label, value):
        host = (
            "context line 1\n"
            f"leak={value}\n"
            "context line 2\n"
        )
        if name == "json":
            packet = fn(f'{{"data": "{value.replace(chr(10), " ")}"}}')
        else:
            packet = fn(host)
        distinct = value.splitlines()[0]
        for kind, snippet in packet.preserved_evidence:
            assert distinct not in snippet, (
                f"{name}/{label} leaked into evidence kind={kind} snippet={snippet!r}"
            )


# ---------------------------------------------------------------------------
# Cross-cutting invariants
# ---------------------------------------------------------------------------

class TestCrossCuttingInvariants:
    @pytest.mark.parametrize("name,fn", list(COMPRESSORS))
    def test_compressed_length_matches_payload_length(self, name, fn):
        sample = "hello world\nfile.py:1\nfoo"
        if name == "json":
            p = fn('{"x": 1}')
        else:
            p = fn(sample)
        assert p.compressed_length == len(p.payload)

    @pytest.mark.parametrize("name,fn", list(COMPRESSORS))
    def test_packet_is_frozen(self, name, fn):
        sample = "hello"
        if name == "json":
            p = fn('{"x": 1}')
        else:
            p = fn(sample)
        with pytest.raises(Exception):
            p.payload = "tampered"  # type: ignore[misc]
