"""Module for Jira comment operations."""

import logging
from typing import Any

from ..models.jira.adf import adf_to_text
from ..utils import parse_date
from .client import JiraClient

logger = logging.getLogger("mcp-jira")


class CommentsMixin(JiraClient):
    """Mixin for Jira comment operations."""

    def get_issue_comments(
        self,
        issue_key: str,
        limit: int = 50,
        offset: int = 0,
        order: str = "oldest",
    ) -> dict[str, Any]:
        """Get comments for a specific issue with pagination and ordering.

        Args:
            issue_key: The issue key (e.g. 'PROJ-123')
            limit: Maximum number of comments to return
            offset: Number of comments to skip (after ordering)
            order: Comment order — "oldest" or "newest"

        Returns:
            Dict with items, total, returned, offset, has_more, order

        Raises:
            Exception: If there is an error getting comments
        """
        try:
            if order == "newest" and not self.config.is_cloud:
                return self._get_comments_newest_server(issue_key, limit, offset)

            # Build query params for the comments endpoint
            params: dict[str, Any] = {
                "startAt": offset,
                "maxResults": limit,
            }
            if self.config.is_cloud and order == "newest":
                params["orderBy"] = "-created"
            elif self.config.is_cloud:
                params["orderBy"] = "created"

            api_version = "3" if self.config.is_cloud else "2"
            url = f"rest/api/{api_version}/issue/{issue_key}/comment"
            response = self.jira.get(url, params=params)

            if not isinstance(response, dict):
                msg = f"Unexpected return value type from comment API: {type(response)}"
                logger.error(msg)
                raise TypeError(msg)

            raw_comments = response.get("comments", [])
            total = response.get("total", len(raw_comments))

            processed = []
            for comment in raw_comments:
                processed.append(
                    {
                        "id": comment.get("id"),
                        "body": self._clean_text(comment.get("body", "")),
                        "created": str(parse_date(comment.get("created"))),
                        "updated": str(parse_date(comment.get("updated"))),
                        "author": comment.get("author", {}).get(
                            "displayName", "Unknown"
                        ),
                    }
                )

            returned = len(processed)
            has_more = (offset + returned) < total

            return {
                "items": processed,
                "total": total,
                "returned": returned,
                "offset": offset,
                "has_more": has_more,
                "order": order,
            }
        except Exception as e:
            logger.error(f"Error getting comments for issue {issue_key}: {str(e)}")
            raise Exception(f"Error getting comments: {str(e)}") from e

    def _get_comments_newest_server(
        self,
        issue_key: str,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        """Get newest comments on Server/DC (no orderBy support).

        Server/DC API returns oldest-first only. To get newest-first:
        1. Fetch total count with maxResults=0
        2. Compute the correct startAt for the window we want
        3. Fetch that window and reverse
        """
        try:
            url = f"rest/api/2/issue/{issue_key}/comment"
            count_response = self.jira.get(url, params={"startAt": 0, "maxResults": 0})
            if not isinstance(count_response, dict):
                msg = (
                    "Unexpected return value type from "
                    f"comment API: {type(count_response)}"
                )
                logger.error(msg)
                raise TypeError(msg)
            total = count_response.get("total", 0)

            if total == 0:
                return {
                    "items": [],
                    "total": 0,
                    "returned": 0,
                    "offset": offset,
                    "has_more": False,
                    "order": "newest",
                }

            start_at = max(0, total - offset - limit)
            fetch_count = min(limit, total - offset)
            if fetch_count <= 0:
                return {
                    "items": [],
                    "total": total,
                    "returned": 0,
                    "offset": offset,
                    "has_more": False,
                    "order": "newest",
                }

            response = self.jira.get(
                url,
                params={
                    "startAt": start_at,
                    "maxResults": fetch_count,
                },
            )
            if not isinstance(response, dict):
                msg = f"Unexpected return value type from comment API: {type(response)}"
                logger.error(msg)
                raise TypeError(msg)

            raw_comments = response.get("comments", [])
            processed = []
            for comment in raw_comments:
                processed.append(
                    {
                        "id": comment.get("id"),
                        "body": self._clean_text(comment.get("body", "")),
                        "created": str(parse_date(comment.get("created"))),
                        "updated": str(parse_date(comment.get("updated"))),
                        "author": comment.get("author", {}).get(
                            "displayName", "Unknown"
                        ),
                    }
                )

            processed.reverse()
            returned = len(processed)
            has_more = (offset + returned) < total

            return {
                "items": processed,
                "total": total,
                "returned": returned,
                "offset": offset,
                "has_more": has_more,
                "order": "newest",
            }
        except Exception as e:
            logger.error(f"Error getting comments for issue {issue_key}: {str(e)}")
            raise Exception(f"Error getting comments: {str(e)}") from e

    def add_comment(
        self,
        issue_key: str,
        comment: str,
        visibility: dict[str, str] | None = None,
        public: bool | None = None,
    ) -> dict[str, Any]:
        """Add a comment to an issue.

        Args:
            issue_key: The issue key (e.g. 'PROJ-123')
            comment: Comment text to add (in Markdown format)
            visibility: (optional) Restrict comment visibility
                (e.g. {"type":"group","value":"jira-users"})
            public: (optional) For JSM issues only. True for
                customer-visible, False for internal/agent-only.
                Uses ServiceDesk API (plain text, not Markdown).
                Cannot be combined with visibility.

        Returns:
            The created comment details

        Raises:
            ValueError: If both public and visibility are set
            Exception: If there is an error adding the comment
        """
        # ServiceDesk API path for internal/public comments
        if public is not None:
            if visibility is not None:
                raise ValueError(
                    "Cannot use both 'public' and 'visibility'. "
                    "'public' uses the ServiceDesk API which "
                    "does not support Jira visibility "
                    "restrictions."
                )
            return self._add_servicedesk_comment(issue_key, comment, public)

        try:
            # Convert Markdown to Jira's markup format
            jira_formatted_comment = self._markdown_to_jira(comment)

            # Use v3 API on Cloud for ADF comments
            if isinstance(jira_formatted_comment, dict) and self.config.is_cloud:
                data: dict[str, Any] = {"body": jira_formatted_comment}
                if visibility:
                    data["visibility"] = visibility
                result = self._post_api3(f"issue/{issue_key}/comment", data)
            else:
                result = self.jira.issue_add_comment(
                    issue_key, jira_formatted_comment, visibility
                )
            if not isinstance(result, dict):
                msg = f"Unexpected return value type from `jira.issue_add_comment`: {type(result)}"
                logger.error(msg)
                raise TypeError(msg)

            body_raw = result.get("body", "")
            body_text = (
                adf_to_text(body_raw) if isinstance(body_raw, dict) else body_raw
            )
            return {
                "id": result.get("id"),
                "body": self._clean_text(body_text or ""),
                "created": str(parse_date(result.get("created"))),
                "author": result.get("author", {}).get("displayName", "Unknown"),
            }
        except Exception as e:
            logger.error(f"Error adding comment to issue {issue_key}: {str(e)}")
            raise Exception(f"Error adding comment: {str(e)}") from e

    def _add_servicedesk_comment(
        self,
        issue_key: str,
        comment: str,
        public: bool,
    ) -> dict[str, Any]:
        """Add a comment via the ServiceDesk API.

        Supports internal (agent-only) and public (customer-visible)
        comments on JSM issues. Uses plain text, not ADF or wiki
        markup.

        Args:
            issue_key: The issue key (e.g. 'PROJ-123')
            comment: Comment text (plain text, not Markdown)
            public: True for customer-visible, False for internal

        Returns:
            The created comment details

        Raises:
            Exception: If the issue is not a JSM issue or API fails
        """
        try:
            url = f"rest/servicedeskapi/request/{issue_key}/comment"
            data = {"body": comment, "public": public}
            headers = {
                **self.jira.default_headers,
                "X-ExperimentalApi": "opt-in",
            }
            response = self.jira.post(
                url,
                data=data,
                headers=headers,
            )
            if not isinstance(response, dict):
                msg = (
                    "Unexpected return value type from "
                    f"ServiceDesk API: {type(response)}"
                )
                logger.error(msg)
                raise TypeError(msg)

            body_text = response.get("body", "")
            # ServiceDesk API returns DateDTO format
            created_dto = response.get("created", {})
            created_str = (
                created_dto.get("iso8601", "")
                if isinstance(created_dto, dict)
                else str(created_dto)
            )
            author_data = response.get("author", {})
            author_name = author_data.get("displayName", "Unknown")

            return {
                "id": str(response.get("id", "")),
                "body": self._clean_text(body_text),
                "created": (str(parse_date(created_str)) if created_str else ""),
                "author": author_name,
                "public": response.get("public", public),
            }
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg or "forbidden" in error_msg.lower():
                raise Exception(
                    f"Issue {issue_key} is not a JSM service "
                    f"desk issue or you lack permission: "
                    f"{error_msg}"
                ) from e
            if "404" in error_msg or "not found" in error_msg.lower():
                raise Exception(
                    f"Issue {issue_key} is not a JSM service "
                    f"desk issue or does not exist: {error_msg}"
                ) from e
            raise Exception(
                f"Error adding ServiceDesk comment to {issue_key}: {error_msg}"
            ) from e

    def edit_comment(
        self,
        issue_key: str,
        comment_id: str,
        comment: str,
        visibility: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Edit an existing comment on an issue.

        Args:
            issue_key: The issue key (e.g. 'PROJ-123')
            comment_id: The ID of the comment to edit
            comment: Updated comment text (in Markdown format)
            visibility: (optional) Restrict comment visibility (e.g. {"type":"group","value":"jira-users"})

        Returns:
            The updated comment details

        Raises:
            Exception: If there is an error editing the comment
        """
        try:
            # Convert Markdown to Jira's markup format
            jira_formatted_comment = self._markdown_to_jira(comment)

            # Use v3 API on Cloud for ADF comments
            if isinstance(jira_formatted_comment, dict) and self.config.is_cloud:
                data: dict[str, Any] = {"body": jira_formatted_comment}
                if visibility:
                    data["visibility"] = visibility
                result = self._put_api3(f"issue/{issue_key}/comment/{comment_id}", data)
            else:
                result = self.jira.issue_edit_comment(
                    issue_key, comment_id, jira_formatted_comment, visibility
                )
            if not isinstance(result, dict):
                msg = f"Unexpected return value type from `jira.issue_edit_comment`: {type(result)}"
                logger.error(msg)
                raise TypeError(msg)

            body_raw = result.get("body", "")
            body_text = (
                adf_to_text(body_raw) if isinstance(body_raw, dict) else body_raw
            )
            return {
                "id": result.get("id"),
                "body": self._clean_text(body_text or ""),
                "updated": str(parse_date(result.get("updated"))),
                "author": result.get("author", {}).get("displayName", "Unknown"),
            }
        except Exception as e:
            logger.error(
                f"Error editing comment {comment_id} on issue {issue_key}: {str(e)}"
            )
            raise Exception(f"Error editing comment: {str(e)}") from e

    def delete_comment(self, issue_key: str, comment_id: str) -> dict[str, Any]:
        """Delete a comment from an issue.

        Args:
            issue_key: The issue key (e.g. 'PROJ-123')
            comment_id: The ID of the comment to delete

        Returns:
            Confirmation dict with success status, issue_key, and comment_id

        Raises:
            Exception: If there is an error deleting the comment
        """
        try:
            if self.config.is_cloud:
                self._delete_api3(f"issue/{issue_key}/comment/{comment_id}")
            else:
                url = f"rest/api/2/issue/{issue_key}/comment/{comment_id}"
                self.jira.delete(url)
            return {
                "success": True,
                "issue_key": issue_key,
                "comment_id": comment_id,
            }
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg or "not found" in error_msg.lower():
                raise Exception(
                    f"Comment {comment_id} not found on issue {issue_key}: {error_msg}"
                ) from e
            if "403" in error_msg or "forbidden" in error_msg.lower():
                raise Exception(
                    f"Permission denied deleting comment {comment_id} "
                    f"on issue {issue_key}: {error_msg}"
                ) from e
            logger.error(
                f"Error deleting comment {comment_id} on issue {issue_key}: {error_msg}"
            )
            raise Exception(f"Error deleting comment: {error_msg}") from e
