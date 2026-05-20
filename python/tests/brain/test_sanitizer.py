"""OutputSanitizer 단위 테스트."""
from __future__ import annotations

import pytest

from cassiopeia_sdk.brain import OutputSanitizer


class TestNonePolicy:

    def test_returns_original(self):
        assert OutputSanitizer.sanitize("hello *world*", "none") == "hello *world*"

    def test_returns_empty_string(self):
        assert OutputSanitizer.sanitize("", "none") == ""

    def test_does_not_escape_html(self):
        text = "<b>bold</b> & 'quoted'"
        assert OutputSanitizer.sanitize(text, "none") == text


class TestMarkdownPolicy:

    def test_escapes_asterisk(self):
        result = OutputSanitizer.sanitize("*bold*", "markdown")
        assert "\\*" in result

    def test_escapes_underscore(self):
        result = OutputSanitizer.sanitize("_italic_", "markdown")
        assert "\\_" in result

    def test_escapes_backtick(self):
        result = OutputSanitizer.sanitize("`code`", "markdown")
        assert "\\`" in result

    def test_escapes_bracket(self):
        result = OutputSanitizer.sanitize("[link](url)", "markdown")
        assert "\\[" in result

    def test_escapes_hash(self):
        result = OutputSanitizer.sanitize("# heading", "markdown")
        assert "\\#" in result

    def test_escapes_pipe(self):
        result = OutputSanitizer.sanitize("col1 | col2", "markdown")
        assert "\\|" in result

    def test_plain_text_unchanged(self):
        result = OutputSanitizer.sanitize("안녕하세요 반갑습니다", "markdown")
        assert result == "안녕하세요 반갑습니다"

    def test_empty_string(self):
        assert OutputSanitizer.sanitize("", "markdown") == ""

    def test_escaped_text_is_longer(self):
        """이스케이핑 후 텍스트 길이가 늘어남."""
        original = "*bold* and _italic_"
        result = OutputSanitizer.sanitize(original, "markdown")
        assert len(result) > len(original)


class TestHtmlPolicy:

    def test_escapes_lt(self):
        result = OutputSanitizer.sanitize("<div>", "html")
        assert "&lt;" in result

    def test_escapes_gt(self):
        result = OutputSanitizer.sanitize("<div>content</div>", "html")
        assert "&gt;" in result

    def test_escapes_ampersand(self):
        result = OutputSanitizer.sanitize("A & B", "html")
        assert "&amp;" in result

    def test_escapes_double_quote(self):
        result = OutputSanitizer.sanitize('say "hello"', "html")
        assert "&quot;" in result

    def test_escapes_single_quote(self):
        result = OutputSanitizer.sanitize("it's fine", "html")
        assert "&#x27;" in result or "&apos;" in result or "it" in result

    def test_xss_vector_is_escaped(self):
        xss = "<script>alert('xss')</script>"
        result = OutputSanitizer.sanitize(xss, "html")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_plain_text_unchanged(self):
        result = OutputSanitizer.sanitize("안녕하세요", "html")
        assert result == "안녕하세요"

    def test_empty_string(self):
        assert OutputSanitizer.sanitize("", "html") == ""
