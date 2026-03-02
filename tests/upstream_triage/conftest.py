"""Upstream issue triage test configuration.

Provides fixtures for reproducing upstream bug reports against a real
Confluence Cloud instance. Uses the same credentials as the MCP server
(CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN).

Run with: uv run pytest tests/upstream_triage/ --upstream-triage -xvs
"""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

import pytest
from dotenv import load_dotenv

from mcp_atlassian.confluence import ConfluenceFetcher
from mcp_atlassian.confluence.config import ConfluenceConfig

logger = logging.getLogger(__name__)

# Load .env from project root if it exists (before fixtures read env vars)
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")


# --- Pytest Plugin ---


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --upstream-triage command-line option."""
    parser.addoption(
        "--upstream-triage",
        action="store_true",
        default=False,
        help="Run upstream issue triage/reproduction tests",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Auto-skip upstream_triage tests unless --upstream-triage is passed."""
    if config.getoption("--upstream-triage"):
        return
    skip_triage = pytest.mark.skip(reason="need --upstream-triage option to run")
    for item in items:
        if "upstream_triage" in item.keywords:
            item.add_marker(skip_triage)


TRIAGE_SPACE_KEY = os.environ.get("TRIAGE_SPACE_KEY", "MCPTEST")


@dataclass
class TriageInstanceInfo:
    """Connection info for triage tests, loaded from MCP server env vars."""

    confluence_url: str = ""
    username: str = ""
    api_token: str = ""
    space_key: str = TRIAGE_SPACE_KEY

    @classmethod
    def from_env(cls) -> TriageInstanceInfo:
        return cls(
            confluence_url=os.environ.get("CONFLUENCE_URL", ""),
            username=os.environ.get("CONFLUENCE_USERNAME", ""),
            api_token=os.environ.get("CONFLUENCE_API_TOKEN", ""),
            space_key=os.environ.get("TRIAGE_SPACE_KEY", TRIAGE_SPACE_KEY),
        )

    def has_credentials(self) -> bool:
        return bool(self.confluence_url and self.username and self.api_token)


class TriageResourceTracker:
    """Tracks resources created during triage tests for cleanup."""

    def __init__(self) -> None:
        self.confluence_pages: list[str] = []

    def add_page(self, page_id: str) -> None:
        self.confluence_pages.append(page_id)

    def cleanup(self, confluence_client: ConfluenceFetcher | None = None) -> None:
        if not confluence_client:
            return
        for page_id in reversed(self.confluence_pages):
            try:
                confluence_client.delete_page(page_id)
                logger.info("Cleaned up triage page %s", page_id)
            except Exception:
                logger.warning("Failed to clean up triage page %s", page_id)


@pytest.fixture(scope="session")
def triage_instance() -> TriageInstanceInfo:
    """Load triage connection info from environment."""
    info = TriageInstanceInfo.from_env()
    if not info.has_credentials():
        pytest.skip(
            "Triage tests require CONFLUENCE_URL, CONFLUENCE_USERNAME, "
            "CONFLUENCE_API_TOKEN environment variables"
        )
    return info


@pytest.fixture(scope="session")
def triage_confluence(triage_instance: TriageInstanceInfo) -> ConfluenceFetcher:
    """Session-scoped Confluence client for triage tests."""
    config = ConfluenceConfig(
        url=triage_instance.confluence_url,
        auth_type="basic",
        username=triage_instance.username,
        api_token=triage_instance.api_token,
    )
    return ConfluenceFetcher(config=config)


@pytest.fixture
def triage_tracker(
    triage_confluence: ConfluenceFetcher,
) -> Generator[TriageResourceTracker, None, None]:
    """Function-scoped resource tracker with auto-cleanup."""
    tracker = TriageResourceTracker()
    yield tracker
    tracker.cleanup(triage_confluence)


@pytest.fixture
def unique_id() -> str:
    """Short unique ID for test page titles."""
    return uuid.uuid4().hex[:8]
