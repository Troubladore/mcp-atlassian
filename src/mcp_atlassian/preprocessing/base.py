"""Base preprocessing module."""

import logging
import re
import urllib.parse
import warnings
from collections.abc import Callable
from typing import Any, Protocol

from bs4 import BeautifulSoup, Tag
from markdownify import markdownify as md

logger = logging.getLogger("mcp-atlassian")

# Pseudo-link scheme for encoding Confluence user mentions in markdown.
# Read path (base.py) writes these; write path (confluence.py) parses them.
CONFLUENCE_USER_SCHEME = "confluence-user"


def _extract_blocks(
    text: str,
    pattern: str,
    transform_fn: Callable[[re.Match[str]], str],
    storage: list[str],
    prefix: str,
    flags: int = 0,
) -> str:
    """Extract blocks matching pattern, transform, store, and replace with placeholders.

    Args:
        text: Input text to process.
        pattern: Regex pattern to match blocks.
        transform_fn: Function to transform the match into the target format.
        storage: List to store transformed blocks.
        prefix: Placeholder prefix (e.g., "CODEBLOCK").
        flags: Regex flags to pass to ``re.sub``.

    Returns:
        Text with blocks replaced by placeholders.
    """

    def _replacer(match: re.Match[str]) -> str:
        transformed = transform_fn(match)
        placeholder = f"\x00{prefix}{len(storage)}\x00"
        storage.append(transformed)
        return placeholder

    return re.sub(pattern, _replacer, text, flags=flags)


def _restore_blocks(text: str, storage: list[str], prefix: str) -> str:
    """Restore blocks from placeholders.

    Replaces in reverse order (highest index first) to avoid
    index collisions when placeholder text contains digits.

    Args:
        text: Text with placeholders.
        storage: List of stored blocks.
        prefix: Placeholder prefix used during extraction.

    Returns:
        Text with placeholders replaced by stored blocks.
    """
    for i in range(len(storage) - 1, -1, -1):
        text = text.replace(f"\x00{prefix}{i}\x00", storage[i])
    return text


class ConfluenceClient(Protocol):
    """Protocol for Confluence client."""

    def get_user_details_by_accountid(self, account_id: str) -> dict[str, Any]:
        """Get user details by account ID."""
        ...

    def get_user_details_by_username(self, username: str) -> dict[str, Any]:
        """Get user details by username (for Server/DC compatibility)."""
        ...


class BasePreprocessor:
    """Base class for text preprocessing operations."""

    def __init__(self, base_url: str = "") -> None:
        """
        Initialize the base text preprocessor.

        Args:
            base_url: Base URL for API server
        """
        self.base_url = base_url.rstrip("/") if base_url else ""

    def process_html_content(
        self,
        html_content: str,
        space_key: str = "",
        confluence_client: ConfluenceClient | None = None,
        content_id: str = "",
        attachments: list[dict[str, Any]] | None = None,
    ) -> tuple[str, str]:
        """
        Process HTML content to replace user refs and page links.

        Args:
            html_content: The HTML content to process
            space_key: Optional space key for context
            confluence_client: Optional Confluence client for user lookups
            content_id: Optional page/content ID for attachment URL
                construction
            attachments: Optional list of attachment dicts from
                Confluence API for URL lookup

        Returns:
            Tuple of (processed_html, processed_markdown)
        """
        try:
            # Parse the HTML content
            soup = BeautifulSoup(html_content, "html.parser")

            # Process user mentions
            self._process_user_mentions_in_soup(soup, confluence_client)
            self._process_user_profile_macros_in_soup(soup, confluence_client)

            # Process Confluence image tags
            self._process_images_in_soup(soup, content_id, attachments)

            # Convert to string and markdown
            processed_html = str(soup)
            processed_markdown = md(processed_html)

            return processed_html, processed_markdown

        except Exception as e:
            logger.error(f"Error in process_html_content: {str(e)}")
            raise

    def _process_user_mentions_in_soup(
        self, soup: BeautifulSoup, confluence_client: ConfluenceClient | None = None
    ) -> None:
        """
        Process user mentions in BeautifulSoup object.

        Args:
            soup: BeautifulSoup object containing HTML
            confluence_client: Optional Confluence client for user lookups
        """
        # Find all ac:link elements that might contain user mentions
        user_mentions = soup.find_all("ac:link")

        for user_element in user_mentions:
            user_ref = user_element.find("ri:user")
            if user_ref and user_ref.get("ri:account-id"):
                # Case 1a: Direct user reference with account-id (Cloud)
                account_id = user_ref.get("ri:account-id")
                if isinstance(account_id, str):
                    self._replace_user_mention(
                        user_element, account_id, confluence_client
                    )
                    continue

            if user_ref and user_ref.get("ri:userkey"):
                # Case 1b: Server/DC user reference with userkey
                userkey = user_ref.get("ri:userkey")
                if isinstance(userkey, str):
                    self._replace_user_mention_by_userkey(
                        user_element, userkey, confluence_client
                    )
                    continue

            # Case 2: User reference with link-body containing @
            link_body = user_element.find("ac:link-body")
            if link_body and "@" in link_body.get_text(strip=True):
                user_ref = user_element.find("ri:user")
                if user_ref and user_ref.get("ri:account-id"):
                    account_id = user_ref.get("ri:account-id")
                    if isinstance(account_id, str):
                        self._replace_user_mention(
                            user_element, account_id, confluence_client
                        )
                        continue
                if user_ref and user_ref.get("ri:userkey"):
                    userkey = user_ref.get("ri:userkey")
                    if isinstance(userkey, str):
                        self._replace_user_mention_by_userkey(
                            user_element, userkey, confluence_client
                        )

    def _process_user_profile_macros_in_soup(
        self, soup: BeautifulSoup, confluence_client: ConfluenceClient | None = None
    ) -> None:
        """
        Process Confluence User Profile macros in BeautifulSoup object.
        Replaces <ac:structured-macro ac:name="profile">...</ac:structured-macro>
        with the user's display name, typically formatted as @DisplayName.

        Args:
            soup: BeautifulSoup object containing HTML
            confluence_client: Optional Confluence client for user lookups
        """
        profile_macros = soup.find_all(
            "ac:structured-macro", attrs={"ac:name": "profile"}
        )

        for macro_element in profile_macros:
            user_param = macro_element.find("ac:parameter", attrs={"ac:name": "user"})
            if not user_param:
                logger.debug(
                    "User profile macro found without a 'user' parameter. Replacing with placeholder."
                )
                macro_element.replace_with("[User Profile Macro (Malformed)]")
                continue

            user_ref = user_param.find("ri:user")
            if not user_ref:
                logger.debug(
                    "User profile macro's 'user' parameter found without 'ri:user' tag. Replacing with placeholder."
                )
                macro_element.replace_with("[User Profile Macro (Malformed)]")
                continue

            account_id = user_ref.get("ri:account-id")
            userkey = user_ref.get("ri:userkey")  # Fallback for Confluence Server/DC

            user_identifier_for_log = account_id or userkey
            display_name = None

            if confluence_client and user_identifier_for_log:
                try:
                    if account_id and isinstance(account_id, str):
                        user_details = confluence_client.get_user_details_by_accountid(
                            account_id
                        )
                        display_name = user_details.get("displayName")
                    elif userkey and isinstance(userkey, str):
                        # For Confluence Server/DC, userkey might be the username
                        user_details = confluence_client.get_user_details_by_username(
                            userkey
                        )
                        display_name = user_details.get("displayName")
                except Exception as e:
                    logger.warning(
                        f"Error fetching user details for profile macro (user: {user_identifier_for_log}): {e}"
                    )
            elif not confluence_client:
                logger.warning(
                    "Confluence client not available for User Profile Macro processing."
                )

            id_type = "accountId" if account_id else "userKey"
            identifier = account_id or userkey

            if display_name and identifier:
                macro_element.replace_with(
                    self._create_user_link_tag(id_type, identifier, display_name)
                )
            elif identifier:
                macro_element.replace_with(
                    self._create_user_link_tag(id_type, identifier, identifier)
                )
                logger.debug(f"Using fallback for user profile macro: {identifier}")
            else:
                macro_element.replace_with("[User Profile Macro (Unknown)]")

    @staticmethod
    def _create_user_link_tag(id_type: str, id_value: str, display_text: str) -> Tag:
        """Create a user mention pseudo-link tag.

        Args:
            id_type: "accountId" or "userKey"
            id_value: The user's identifier
            display_text: Text to display (without @ prefix)
        """
        link_tag = Tag(
            name="a",
            attrs={"href": f"{CONFLUENCE_USER_SCHEME}:{id_type}/{id_value}"},
        )
        link_tag.string = f"@{display_text}"
        return link_tag

    def _replace_user_mention(
        self,
        user_element: Tag,
        account_id: str,
        confluence_client: ConfluenceClient | None = None,
    ) -> None:
        """Replace a user mention (Cloud account-id) with a pseudo-link."""
        try:
            if confluence_client is not None:
                user_details = confluence_client.get_user_details_by_accountid(
                    account_id
                )
                display_name = user_details.get("displayName", "")
                if display_name:
                    user_element.replace_with(
                        self._create_user_link_tag(
                            "accountId", account_id, display_name
                        )
                    )
                    return
            user_element.replace_with(
                self._create_user_link_tag(
                    "accountId", account_id, f"user_{account_id}"
                )
            )
        except Exception as e:
            logger.warning(f"Error processing user mention: {str(e)}")
            user_element.replace_with(
                self._create_user_link_tag(
                    "accountId", account_id, f"user_{account_id}"
                )
            )

    def _replace_user_mention_by_userkey(
        self,
        user_element: Tag,
        userkey: str,
        confluence_client: ConfluenceClient | None = None,
    ) -> None:
        """Replace a user mention (Server/DC userkey) with a pseudo-link."""
        try:
            display_name = None
            if confluence_client is not None:
                user_details = confluence_client.get_user_details_by_username(userkey)
                display_name = user_details.get("displayName", "")

            name = display_name if display_name else f"user_{userkey}"
            user_element.replace_with(
                self._create_user_link_tag("userKey", userkey, name)
            )
        except Exception as e:
            logger.warning(f"Error processing user mention: {str(e)}")
            user_element.replace_with(
                self._create_user_link_tag("userKey", userkey, f"user_{userkey}")
            )

    def _find_attachment_url(
        self,
        filename: str,
        attachments: list[dict[str, Any]] | None,
    ) -> str | None:
        """Find an attachment's download URL by filename.

        Args:
            filename: The attachment filename to look up
            attachments: List of attachment dicts from Confluence API

        Returns:
            The download URL if found, None otherwise
        """
        if not attachments:
            return None
        for att in attachments:
            if att.get("title") == filename:
                download = att.get("_links", {}).get("download")
                if download:
                    return str(download)
        return None

    def _process_images_in_soup(
        self,
        soup: BeautifulSoup,
        content_id: str = "",
        attachments: list[dict[str, Any]] | None = None,
    ) -> None:
        """Convert Confluence ac:image tags to standard HTML img tags.

        Args:
            soup: BeautifulSoup object containing HTML
            content_id: Optional page/content ID for fallback URL
            attachments: Optional attachment list for URL lookup
        """
        for ac_image in soup.find_all("ac:image"):
            src = ""
            alt = ""

            # Case 1: ri:attachment (file attached to the page)
            ri_att = ac_image.find("ri:attachment")
            if ri_att:
                filename = ri_att.get("ri:filename", "")
                alt = filename

                # Check if this references a different page
                is_cross_page = ri_att.find("ri:page") is not None

                # Try attachment list lookup first
                url = self._find_attachment_url(filename, attachments)
                if url:
                    # Prepend base_url if relative path
                    if url.startswith("/") and self.base_url:
                        src = f"{self.base_url}{url}"
                    else:
                        src = url
                elif content_id and not is_cross_page:
                    encoded = urllib.parse.quote(filename, safe="")
                    src = f"{self.base_url}/download/attachments/{content_id}/{encoded}"
                else:
                    src = filename
            else:
                # Case 2: ri:url (external URL)
                ri_url = ac_image.find("ri:url")
                if ri_url:
                    src = ri_url.get("ri:value", "")
                    # Extract filename from URL path for alt text
                    path = urllib.parse.urlparse(src).path
                    alt = path.rsplit("/", 1)[-1] if "/" in path else src
                else:
                    # Unknown inner element
                    logger.warning(
                        "ac:image tag with unsupported child: %s",
                        ac_image,
                    )
                    ac_image.replace_with("[unsupported image]")
                    continue

            # Build a standard <img> tag
            img_tag = soup.new_tag("img", src=src, alt=alt)

            # Preserve dimension attributes
            width = ac_image.get("ac:width")
            if width:
                img_tag["width"] = width
            height = ac_image.get("ac:height")
            if height:
                img_tag["height"] = height

            ac_image.replace_with(img_tag)

    def _convert_html_to_markdown(self, text: str) -> str:
        """Convert HTML content to markdown if needed.

        Protects markdown code spans (fenced and inline) from being
        interpreted as HTML by BeautifulSoup before conversion.
        """
        # Protect fenced code blocks and inline code from HTML parsing
        code_blocks: list[str] = []
        inline_codes: list[str] = []

        text = _extract_blocks(
            text,
            r"```[^\n]*\n[\s\S]*?\n```",
            lambda m: m.group(0),
            code_blocks,
            "HTMLCVTBLOCK",
        )
        text = _extract_blocks(
            text,
            r"`[^`]+`",
            lambda m: m.group(0),
            inline_codes,
            "HTMLCVTINLINE",
        )

        if re.search(r"<[^>]+>", text):
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=UserWarning)
                    soup = BeautifulSoup(f"<div>{text}</div>", "html.parser")
                    html = str(soup.div.decode_contents()) if soup.div else text
                    text = md(html)
            except Exception as e:
                logger.warning(f"Error converting HTML to markdown: {str(e)}")

        # Restore in reverse order: inline first, then blocks
        text = _restore_blocks(text, inline_codes, "HTMLCVTINLINE")
        text = _restore_blocks(text, code_blocks, "HTMLCVTBLOCK")
        return text
