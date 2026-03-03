"""Tests for missing attachment content parsing (upstream #667)."""

from __future__ import annotations

import inspect

from mcp_atlassian.confluence import ConfluenceFetcher


class TestAttachmentContentParsing:
    """Attachment content (PDF/Word/Excel) is not parsed.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/667
    Feature requested: parse content from PDF, Word, Excel, and text attachments
    when retrieving Confluence page content.
    """

    def test_get_page_content_includes_attachment_text(self) -> None:
        """get_page_content should support extracting attachment text content."""
        sig = inspect.signature(ConfluenceFetcher.get_page_content)
        has_param = (
            "include_attachment_content" in sig.parameters
            or "parse_attachments" in sig.parameters
            or "include_attachments" in sig.parameters
        )
        assert has_param, (
            "No attachment parsing param in get_page_content — #667 not implemented"
        )

    def test_attachment_parser_exists(self) -> None:
        """An attachment content parser module or class should exist."""
        try:
            from mcp_atlassian.preprocessing import AttachmentParser  # noqa: F401
        except ImportError:
            try:
                from mcp_atlassian.confluence.attachments import (  # noqa: F401
                    parse_attachment_content,
                )
            except ImportError:
                raise AssertionError(
                    "No attachment content parser found — issue #667 not implemented"
                )
