"""Tests for the Jira Comments mixin."""

from unittest.mock import Mock

import pytest

from mcp_atlassian.jira.comments import CommentsMixin


class TestCommentsMixin:
    """Tests for the CommentsMixin class."""

    @pytest.fixture
    def comments_mixin(self, jira_client):
        """Create a CommentsMixin instance with mocked dependencies."""
        mixin = CommentsMixin(config=jira_client.config)
        mixin.jira = jira_client.jira

        # Set up a mock preprocessor with markdown_to_jira method
        mixin.preprocessor = Mock()
        mixin.preprocessor.markdown_to_jira = Mock(
            return_value="*This* is _Jira_ formatted"
        )

        # Mock the clean_text method
        mixin._clean_text = Mock(side_effect=lambda x: x)

        return mixin

    def test_get_issue_comments_basic(self, comments_mixin):
        """Test get_issue_comments with basic data."""
        # Setup mock response
        comments_mixin.jira.get = Mock(
            return_value={
                "comments": [
                    {
                        "id": "10001",
                        "body": "This is a comment",
                        "created": "2024-01-01T10:00:00.000+0000",
                        "updated": "2024-01-01T11:00:00.000+0000",
                        "author": {"displayName": "John Doe"},
                    }
                ],
                "total": 1,
                "startAt": 0,
                "maxResults": 50,
            }
        )

        # Call the method
        result = comments_mixin.get_issue_comments("TEST-123")

        # Verify
        comments_mixin.jira.get.assert_called_once()
        assert result["returned"] == 1
        assert result["items"][0]["id"] == "10001"
        assert result["items"][0]["body"] == "This is a comment"
        assert result["items"][0]["created"] == "2024-01-01 10:00:00+00:00"
        assert result["items"][0]["author"] == "John Doe"

    def test_get_issue_comments_with_limit(self, comments_mixin):
        """Test get_issue_comments with limit parameter."""
        # Setup mock response — API returns only 2 due to maxResults=2
        comments_mixin.jira.get = Mock(
            return_value={
                "comments": [
                    {
                        "id": "10001",
                        "body": "First comment",
                        "created": "2024-01-01T10:00:00.000+0000",
                        "author": {"displayName": "John Doe"},
                    },
                    {
                        "id": "10002",
                        "body": "Second comment",
                        "created": "2024-01-02T10:00:00.000+0000",
                        "author": {"displayName": "Jane Smith"},
                    },
                ],
                "total": 3,
                "startAt": 0,
                "maxResults": 2,
            }
        )

        # Call the method with limit=2
        result = comments_mixin.get_issue_comments("TEST-123", limit=2)

        # Verify
        comments_mixin.jira.get.assert_called_once()
        assert len(result["items"]) == 2
        assert result["items"][0]["id"] == "10001"
        assert result["items"][1]["id"] == "10002"
        assert result["has_more"] is True
        assert result["total"] == 3

    def test_get_issue_comments_with_missing_fields(self, comments_mixin):
        """Test get_issue_comments with missing fields in the response."""
        # Setup mock response with missing fields
        comments_mixin.jira.get = Mock(
            return_value={
                "comments": [
                    {
                        "id": "10001",
                        # Missing body field
                        "created": "2024-01-01T10:00:00.000+0000",
                        # Missing author field
                    },
                    {
                        # Missing id field
                        "body": "Second comment",
                        # Missing created field
                        "author": {},  # Empty author object
                    },
                    {
                        "id": "10003",
                        "body": "Third comment",
                        "created": "2024-01-03T10:00:00.000+0000",
                        "author": {"name": "user123"},
                    },
                ],
                "total": 3,
                "startAt": 0,
                "maxResults": 50,
            }
        )

        # Call the method
        result = comments_mixin.get_issue_comments("TEST-123")

        # Verify
        assert len(result["items"]) == 3
        assert result["items"][0]["id"] == "10001"
        assert result["items"][0]["body"] == ""  # Should default to empty string
        assert result["items"][0]["author"] == "Unknown"

        assert (
            "id" not in result["items"][1] or not result["items"][1]["id"]
        )  # Should be missing or empty
        assert result["items"][1]["author"] == "Unknown"

        assert (
            result["items"][2]["author"] == "Unknown"
        )  # Should use Unknown when only name is available

    def test_get_issue_comments_with_empty_response(self, comments_mixin):
        """Test get_issue_comments with an empty response."""
        # Setup mock response with no comments
        comments_mixin.jira.get = Mock(
            return_value={
                "comments": [],
                "total": 0,
                "startAt": 0,
                "maxResults": 50,
            }
        )

        # Call the method
        result = comments_mixin.get_issue_comments("TEST-123")

        # Verify
        assert len(result["items"]) == 0
        assert result["total"] == 0
        assert result["has_more"] is False

    def test_get_issue_comments_with_error(self, comments_mixin):
        """Test get_issue_comments with an error response."""
        # Setup mock to raise exception
        comments_mixin.jira.get = Mock(side_effect=Exception("API Error"))

        # Verify it raises the wrapped exception
        with pytest.raises(Exception, match="Error getting comments"):
            comments_mixin.get_issue_comments("TEST-123")

    def test_get_issue_comments_returns_structured_result(self, comments_mixin):
        """get_issue_comments returns dict with items, total, and metadata."""
        comments_mixin.jira.get = Mock(
            return_value={
                "comments": [
                    {
                        "id": "10001",
                        "body": "First comment",
                        "created": "2024-01-01T10:00:00.000+0000",
                        "updated": "2024-01-01T10:00:00.000+0000",
                        "author": {"displayName": "John Doe"},
                    },
                ],
                "total": 5,
                "startAt": 0,
                "maxResults": 10,
            }
        )

        result = comments_mixin.get_issue_comments("TEST-123", limit=10)

        assert isinstance(result, dict)
        assert "items" in result
        assert "total" in result
        assert "returned" in result
        assert "offset" in result
        assert "has_more" in result
        assert "order" in result
        assert len(result["items"]) == 1
        assert result["total"] == 5
        assert result["returned"] == 1
        assert result["offset"] == 0
        assert result["has_more"] is True
        assert result["order"] == "oldest"

    def test_get_issue_comments_newest_cloud(self, comments_mixin):
        """Cloud newest order uses orderBy=-created."""
        comments_mixin.jira.get = Mock(
            return_value={
                "comments": [
                    {
                        "id": "10003",
                        "body": "Third",
                        "created": "2024-01-03T10:00:00.000+0000",
                        "updated": "2024-01-03T10:00:00.000+0000",
                        "author": {"displayName": "User"},
                    },
                    {
                        "id": "10002",
                        "body": "Second",
                        "created": "2024-01-02T10:00:00.000+0000",
                        "updated": "2024-01-02T10:00:00.000+0000",
                        "author": {"displayName": "User"},
                    },
                ],
                "total": 3,
                "startAt": 0,
                "maxResults": 2,
            }
        )

        result = comments_mixin.get_issue_comments("TEST-123", limit=2, order="newest")

        call_args = comments_mixin.jira.get.call_args
        assert call_args.kwargs["params"]["orderBy"] == "-created"
        assert result["items"][0]["id"] == "10003"
        assert result["order"] == "newest"
        assert result["has_more"] is True

    def test_get_issue_comments_with_offset(self, comments_mixin):
        """Offset skips comments."""
        comments_mixin.jira.get = Mock(
            return_value={
                "comments": [
                    {
                        "id": "10003",
                        "body": "Third",
                        "created": "2024-01-03T10:00:00.000+0000",
                        "updated": "2024-01-03T10:00:00.000+0000",
                        "author": {"displayName": "User"},
                    },
                ],
                "total": 3,
                "startAt": 2,
                "maxResults": 10,
            }
        )

        result = comments_mixin.get_issue_comments("TEST-123", limit=10, offset=2)

        call_args = comments_mixin.jira.get.call_args
        assert call_args.kwargs["params"]["startAt"] == 2
        assert result["offset"] == 2
        assert result["has_more"] is False

    def test_get_issue_comments_has_more_true(self, comments_mixin):
        """has_more is True when more comments exist beyond current page."""
        comments_mixin.jira.get = Mock(
            return_value={
                "comments": [
                    {
                        "id": "10001",
                        "body": "First",
                        "created": "2024-01-01T10:00:00.000+0000",
                        "updated": "2024-01-01T10:00:00.000+0000",
                        "author": {"displayName": "User"},
                    },
                ],
                "total": 50,
                "startAt": 0,
                "maxResults": 1,
            }
        )

        result = comments_mixin.get_issue_comments("TEST-123", limit=1)

        assert result["has_more"] is True
        assert result["total"] == 50
        assert result["returned"] == 1

    def test_add_comment_basic(self, comments_mixin):
        """Test add_comment with basic data (Cloud → ADF via v3 API)."""
        # Setup mock response for v3 API path
        mock_response = {
            "id": "10001",
            "body": "This is a comment",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        }
        comments_mixin._post_api3 = Mock(return_value=mock_response)

        # Call the method
        result = comments_mixin.add_comment("TEST-123", "Test comment")

        # On Cloud, ADF goes through _post_api3 (not issue_add_comment)
        comments_mixin._post_api3.assert_called_once()
        call_args = comments_mixin._post_api3.call_args
        assert call_args[0][0] == "issue/TEST-123/comment"
        adf_body = call_args[0][1]["body"]
        assert isinstance(adf_body, dict)
        assert adf_body["version"] == 1
        assert adf_body["type"] == "doc"
        # preprocessor.markdown_to_jira should NOT be called on Cloud
        comments_mixin.preprocessor.markdown_to_jira.assert_not_called()
        assert result["id"] == "10001"
        assert result["body"] == "This is a comment"
        assert result["created"] == "2024-01-01 10:00:00+00:00"
        assert result["author"] == "John Doe"

    def test_add_comment_with_markdown_conversion(self, comments_mixin):
        """Test add_comment with markdown conversion (Cloud → ADF via v3)."""
        # Setup mock response for v3 API path
        mock_response = {
            "id": "10001",
            "body": "Heading and content",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        }
        comments_mixin._post_api3 = Mock(return_value=mock_response)

        markdown_comment = "# Heading 1\n\nThis is **bold** text."

        # Call the method
        result = comments_mixin.add_comment("TEST-123", markdown_comment)

        # On Cloud, should produce ADF via v3 API, not call preprocessor
        call_args = comments_mixin._post_api3.call_args
        adf_body = call_args[0][1]["body"]
        assert isinstance(adf_body, dict)
        assert adf_body["version"] == 1
        comments_mixin.preprocessor.markdown_to_jira.assert_not_called()
        assert result["body"] == "Heading and content"

    def test_add_comment_with_empty_comment(self, comments_mixin):
        """Test add_comment with an empty comment (Cloud → minimal ADF)."""
        # Setup mock response for v3 API path
        mock_response = {
            "id": "10001",
            "body": "",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        }
        comments_mixin._post_api3 = Mock(return_value=mock_response)

        # Call the method with empty comment
        result = comments_mixin.add_comment("TEST-123", "")

        # On Cloud, empty string produces a minimal ADF dict via v3 API
        call_args = comments_mixin._post_api3.call_args
        adf_body = call_args[0][1]["body"]
        assert isinstance(adf_body, dict)
        assert adf_body["version"] == 1
        comments_mixin.preprocessor.markdown_to_jira.assert_not_called()
        assert result["body"] == ""

    def test_add_comment_with_restricted_visibility(self, comments_mixin):
        """Test add_comment with visibility set (Cloud → ADF via v3)."""
        # Setup mock response for v3 API path
        mock_response = {
            "id": "10001",
            "body": "This is a comment",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        }
        comments_mixin._post_api3 = Mock(return_value=mock_response)

        # Call the method
        result = comments_mixin.add_comment(
            "TEST-123", "Test comment", {"type": "group", "value": "restricted"}
        )

        # Verify ADF via v3 API with visibility
        call_args = comments_mixin._post_api3.call_args
        assert call_args[0][0] == "issue/TEST-123/comment"
        payload = call_args[0][1]
        assert isinstance(payload["body"], dict)
        assert payload["body"]["version"] == 1
        assert payload["visibility"] == {"type": "group", "value": "restricted"}
        comments_mixin.preprocessor.markdown_to_jira.assert_not_called()
        assert result["id"] == "10001"
        assert result["body"] == "This is a comment"
        assert result["created"] == "2024-01-01 10:00:00+00:00"
        assert result["author"] == "John Doe"

    def test_add_comment_with_error(self, comments_mixin):
        """Test add_comment with an error response."""
        # Setup mock to raise exception (Cloud uses _post_api3)
        comments_mixin._post_api3 = Mock(side_effect=Exception("API Error"))

        # Verify it raises the wrapped exception
        with pytest.raises(Exception, match="Error adding comment"):
            comments_mixin.add_comment("TEST-123", "Test comment")

    def test_edit_comment_basic(self, comments_mixin):
        """Test edit_comment with basic data (Cloud → ADF via v3)."""
        # Setup mock response for v3 API path
        mock_response = {
            "id": "10001",
            "body": "This is an updated comment",
            "updated": "2024-01-01T12:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        }
        comments_mixin._put_api3 = Mock(return_value=mock_response)

        # Call the method
        result = comments_mixin.edit_comment("TEST-123", "10001", "Updated comment")

        # On Cloud, ADF goes through _put_api3
        comments_mixin._put_api3.assert_called_once()
        call_args = comments_mixin._put_api3.call_args
        assert call_args[0][0] == "issue/TEST-123/comment/10001"
        adf_body = call_args[0][1]["body"]
        assert isinstance(adf_body, dict)
        assert adf_body["version"] == 1
        comments_mixin.preprocessor.markdown_to_jira.assert_not_called()
        assert result["id"] == "10001"
        assert result["body"] == "This is an updated comment"
        assert result["updated"] == "2024-01-01 12:00:00+00:00"
        assert result["author"] == "John Doe"

    def test_edit_comment_with_markdown_conversion(self, comments_mixin):
        """Test edit_comment with markdown conversion (Cloud → ADF via v3)."""
        # Setup mock response for v3 API path
        mock_response = {
            "id": "10001",
            "body": "Updated content",
            "updated": "2024-01-01T12:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        }
        comments_mixin._put_api3 = Mock(return_value=mock_response)

        markdown_comment = "# Updated Heading\n\nThis is **updated** text."

        # Call the method
        result = comments_mixin.edit_comment("TEST-123", "10001", markdown_comment)

        # On Cloud, should produce ADF via v3 API
        call_args = comments_mixin._put_api3.call_args
        adf_body = call_args[0][1]["body"]
        assert isinstance(adf_body, dict)
        assert adf_body["version"] == 1
        comments_mixin.preprocessor.markdown_to_jira.assert_not_called()
        assert result["body"] == "Updated content"

    def test_edit_comment_with_empty_comment(self, comments_mixin):
        """Test edit_comment with an empty comment (Cloud → minimal ADF)."""
        # Setup mock response for v3 API path
        mock_response = {
            "id": "10001",
            "body": "",
            "updated": "2024-01-01T12:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        }
        comments_mixin._put_api3 = Mock(return_value=mock_response)

        # Call the method with empty comment
        result = comments_mixin.edit_comment("TEST-123", "10001", "")

        # On Cloud, empty string produces a minimal ADF dict via v3 API
        call_args = comments_mixin._put_api3.call_args
        adf_body = call_args[0][1]["body"]
        assert isinstance(adf_body, dict)
        assert adf_body["version"] == 1
        comments_mixin.preprocessor.markdown_to_jira.assert_not_called()
        assert result["body"] == ""

    def test_edit_comment_with_restricted_visibility(self, comments_mixin):
        """Test edit_comment with visibility set (Cloud → ADF via v3)."""
        # Setup mock response for v3 API path
        mock_response = {
            "id": "10001",
            "body": "This is an updated comment",
            "updated": "2024-01-01T12:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        }
        comments_mixin._put_api3 = Mock(return_value=mock_response)

        # Call the method
        result = comments_mixin.edit_comment(
            "TEST-123",
            "10001",
            "Updated comment",
            {"type": "group", "value": "restricted"},
        )

        # Verify ADF via v3 API with visibility
        call_args = comments_mixin._put_api3.call_args
        assert call_args[0][0] == "issue/TEST-123/comment/10001"
        payload = call_args[0][1]
        assert isinstance(payload["body"], dict)
        assert payload["body"]["version"] == 1
        assert payload["visibility"] == {"type": "group", "value": "restricted"}
        comments_mixin.preprocessor.markdown_to_jira.assert_not_called()
        assert result["id"] == "10001"
        assert result["body"] == "This is an updated comment"
        assert result["updated"] == "2024-01-01 12:00:00+00:00"
        assert result["author"] == "John Doe"

    def test_edit_comment_with_error(self, comments_mixin):
        """Test edit_comment with an error response."""
        # Setup mock to raise exception (Cloud uses _put_api3)
        comments_mixin._put_api3 = Mock(side_effect=Exception("API Error"))

        # Verify it raises the wrapped exception
        with pytest.raises(Exception, match="Error editing comment"):
            comments_mixin.edit_comment("TEST-123", "10001", "Updated comment")

    def test_markdown_to_jira_cloud(self, comments_mixin):
        """Test _markdown_to_jira returns ADF dict on Cloud."""
        result = comments_mixin._markdown_to_jira("Markdown text")
        # Cloud config → ADF dict
        assert isinstance(result, dict)
        assert result["version"] == 1
        assert result["type"] == "doc"
        comments_mixin.preprocessor.markdown_to_jira.assert_not_called()

    def test_markdown_to_jira_cloud_empty(self, comments_mixin):
        """Test _markdown_to_jira with empty text on Cloud returns ADF."""
        result = comments_mixin._markdown_to_jira("")
        assert isinstance(result, dict)
        assert result["version"] == 1
        comments_mixin.preprocessor.markdown_to_jira.assert_not_called()

    # --- Server/DC path tests ---

    @pytest.fixture
    def server_comments_mixin(self, jira_config_factory):
        """Create a CommentsMixin configured for Server/DC."""
        config = jira_config_factory(url="https://jira.example.com")
        mixin = CommentsMixin(config=config)
        mixin.jira = Mock()
        mixin.preprocessor = Mock()
        mixin.preprocessor.markdown_to_jira = Mock(return_value="h1. Hello")
        mixin._clean_text = Mock(side_effect=lambda x: x)
        return mixin

    def test_markdown_to_jira_server_returns_string(self, server_comments_mixin):
        """Server/DC path returns wiki markup string."""
        result = server_comments_mixin._markdown_to_jira("# Hello")
        assert isinstance(result, str)
        assert result == "h1. Hello"
        server_comments_mixin.preprocessor.markdown_to_jira.assert_called_once()

    def test_add_comment_server_sends_string(self, server_comments_mixin):
        """Server/DC add_comment sends wiki markup string to API."""
        server_comments_mixin.jira.issue_add_comment.return_value = {
            "id": "10001",
            "body": "h1. Hello",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "Test User"},
        }
        result = server_comments_mixin.add_comment("TEST-123", "# Hello")
        call_args = server_comments_mixin.jira.issue_add_comment.call_args
        comment_arg = call_args[0][1]
        assert isinstance(comment_arg, str)
        assert result["body"] == "h1. Hello"

    def test_edit_comment_server_sends_string(self, server_comments_mixin):
        """Server/DC edit_comment sends wiki markup string to API."""
        server_comments_mixin.jira.issue_edit_comment.return_value = {
            "id": "10001",
            "body": "h1. Updated",
            "updated": "2024-01-01T11:00:00.000+0000",
            "author": {"displayName": "Test User"},
        }
        server_comments_mixin.preprocessor.markdown_to_jira.return_value = "h1. Updated"
        result = server_comments_mixin.edit_comment("TEST-123", "10001", "# Updated")
        call_args = server_comments_mixin.jira.issue_edit_comment.call_args
        comment_arg = call_args[0][2]
        assert isinstance(comment_arg, str)
        assert result["body"] == "h1. Updated"

    def test_get_issue_comments_newest_server(self, server_comments_mixin):
        """Server/DC newest order fetches from end and reverses."""
        call_count = [0]

        def mock_get(url, params=None):
            call_count[0] += 1
            if params and params.get("maxResults") == 0:
                return {
                    "comments": [],
                    "total": 5,
                    "startAt": 0,
                    "maxResults": 0,
                }
            return {
                "comments": [
                    {
                        "id": "10004",
                        "body": "Fourth",
                        "created": "2024-01-04T10:00:00.000+0000",
                        "updated": "2024-01-04T10:00:00.000+0000",
                        "author": {"displayName": "User"},
                    },
                    {
                        "id": "10005",
                        "body": "Fifth",
                        "created": "2024-01-05T10:00:00.000+0000",
                        "updated": "2024-01-05T10:00:00.000+0000",
                        "author": {"displayName": "User"},
                    },
                ],
                "total": 5,
                "startAt": 3,
                "maxResults": 2,
            }

        server_comments_mixin.jira.get = Mock(side_effect=mock_get)

        result = server_comments_mixin.get_issue_comments(
            "TEST-123", limit=2, order="newest"
        )

        assert call_count[0] == 2
        assert result["items"][0]["id"] == "10005"
        assert result["items"][1]["id"] == "10004"
        assert result["order"] == "newest"
        assert result["has_more"] is True
        assert result["total"] == 5

    # --- ServiceDesk API (internal/public comments) tests ---

    SERVICEDESK_COMMENT_RESPONSE = {
        "id": 10001,
        "body": "Test comment",
        "public": True,
        "created": {
            "iso8601": "2024-01-01T10:00:00.000+0000",
            "jira": "2024-01-01T10:00:00.000+0000",
            "friendly": "Today 10:00 AM",
            "epochMillis": 1704099600000,
        },
        "author": {
            "accountId": "test-id",
            "displayName": "Test User",
        },
    }

    def test_add_comment_servicedesk_public(self, comments_mixin):
        """public=True routes through ServiceDesk API."""
        response = {**self.SERVICEDESK_COMMENT_RESPONSE, "public": True}
        comments_mixin.jira.post.return_value = response

        result = comments_mixin.add_comment("TEST-123", "Test comment", public=True)

        comments_mixin.jira.post.assert_called_once()
        call_args = comments_mixin.jira.post.call_args
        assert "rest/servicedeskapi/request/TEST-123/comment" in str(call_args)
        assert call_args[1]["data"] == {
            "body": "Test comment",
            "public": True,
        }
        # Verify experimental header is included
        headers = call_args[1]["headers"]
        assert headers["X-ExperimentalApi"] == "opt-in"
        assert result["public"] is True
        assert result["id"] == "10001"
        assert result["author"] == "Test User"

    def test_add_comment_servicedesk_internal(self, comments_mixin):
        """public=False routes through ServiceDesk API as internal."""
        response = {**self.SERVICEDESK_COMMENT_RESPONSE, "public": False}
        comments_mixin.jira.post.return_value = response

        result = comments_mixin.add_comment("TEST-123", "Internal note", public=False)

        call_args = comments_mixin.jira.post.call_args
        assert call_args[1]["data"] == {
            "body": "Internal note",
            "public": False,
        }
        assert result["public"] is False

    def test_add_comment_servicedesk_cloud(self, comments_mixin):
        """public=True on Cloud uses ServiceDesk API, not ADF/v3."""
        response = {**self.SERVICEDESK_COMMENT_RESPONSE}
        comments_mixin.jira.post.return_value = response
        comments_mixin._post_api3 = Mock()

        comments_mixin.add_comment("TEST-123", "Test", public=True)

        # ServiceDesk path should use jira.post, NOT _post_api3
        comments_mixin.jira.post.assert_called_once()
        comments_mixin._post_api3.assert_not_called()

    def test_add_comment_servicedesk_403(self, comments_mixin):
        """public=True on non-JSM project gives clear 403 error."""
        comments_mixin.jira.post.side_effect = Exception("403 Client Error: Forbidden")

        with pytest.raises(Exception, match="not a JSM service desk issue"):
            comments_mixin.add_comment("TEST-123", "Test", public=True)

    def test_add_comment_servicedesk_404(self, comments_mixin):
        """public=True on non-existent issue gives clear 404 error."""
        comments_mixin.jira.post.side_effect = Exception("404 Client Error: Not Found")

        with pytest.raises(Exception, match="not a JSM service desk issue"):
            comments_mixin.add_comment("TEST-123", "Test", public=True)

    def test_add_comment_public_with_visibility_raises(self, comments_mixin):
        """public + visibility together raises ValueError."""
        with pytest.raises(ValueError, match="Cannot use both"):
            comments_mixin.add_comment(
                "TEST-123",
                "Test",
                visibility={"type": "group", "value": "jira-users"},
                public=True,
            )

    def test_delete_comment_cloud(self, comments_mixin):
        """Test delete_comment on Cloud uses DELETE /rest/api/3/."""
        comments_mixin._delete_api3 = Mock(return_value=None)

        result = comments_mixin.delete_comment("TEST-123", "10001")

        comments_mixin._delete_api3.assert_called_once_with(
            "issue/TEST-123/comment/10001"
        )
        assert result["success"] is True
        assert result["issue_key"] == "TEST-123"
        assert result["comment_id"] == "10001"

    def test_delete_comment_server(self, server_comments_mixin):
        """Test delete_comment on Server/DC uses DELETE /rest/api/2/."""
        server_comments_mixin.jira.delete = Mock(return_value=None)

        result = server_comments_mixin.delete_comment("TEST-123", "10001")

        server_comments_mixin.jira.delete.assert_called_once_with(
            "rest/api/2/issue/TEST-123/comment/10001"
        )
        assert result["success"] is True
        assert result["issue_key"] == "TEST-123"
        assert result["comment_id"] == "10001"

    def test_delete_comment_not_found(self, comments_mixin):
        """Test delete_comment raises on 404."""
        comments_mixin._delete_api3 = Mock(
            side_effect=Exception("404 Client Error: Not Found")
        )

        with pytest.raises(Exception, match="not found"):
            comments_mixin.delete_comment("TEST-123", "99999")

    def test_delete_comment_forbidden(self, comments_mixin):
        """Test delete_comment raises on 403."""
        comments_mixin._delete_api3 = Mock(
            side_effect=Exception("403 Client Error: Forbidden")
        )

        with pytest.raises(Exception, match="Permission denied"):
            comments_mixin.delete_comment("TEST-123", "10001")

    def test_delete_comment_generic_error(self, comments_mixin):
        """Test delete_comment wraps generic errors."""
        comments_mixin._delete_api3 = Mock(side_effect=Exception("Connection timeout"))

        with pytest.raises(Exception, match="Error deleting comment"):
            comments_mixin.delete_comment("TEST-123", "10001")

    def test_add_comment_public_none_uses_jira_api(self, comments_mixin):
        """public=None (default) uses normal Jira API path."""
        mock_response = {
            "id": "10001",
            "body": "Normal comment",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        }
        comments_mixin._post_api3 = Mock(return_value=mock_response)

        result = comments_mixin.add_comment("TEST-123", "Normal comment")

        # Should go through normal Jira path (ADF on Cloud)
        comments_mixin._post_api3.assert_called_once()
        # ServiceDesk post should NOT be called
        comments_mixin.jira.post.assert_not_called()
        assert result["id"] == "10001"


class TestInternalCommentPublicParam:
    """Regression tests for add_comment public parameter (internal comments).

    Regression for https://github.com/sooperset/mcp-atlassian/issues/716
    Feature was requested: make comment internal (public: false) via JSM API.
    Already implemented: add_comment(public=False) routes through
    _add_servicedesk_comment which posts to rest/servicedeskapi/request/.../comment.
    """

    SERVICEDESK_COMMENT_RESPONSE = {
        "id": 10001,
        "body": "Test comment",
        "public": True,
        "created": {
            "iso8601": "2024-01-01T10:00:00.000+0000",
            "jira": "2024-01-01T10:00:00.000+0000",
            "friendly": "Today 10:00 AM",
            "epochMillis": 1704099600000,
        },
        "author": {
            "accountId": "test-id",
            "displayName": "Test User",
        },
    }

    @pytest.fixture
    def comments_mixin(self, jira_client):
        """Create a CommentsMixin instance with mocked dependencies."""
        mixin = CommentsMixin(config=jira_client.config)
        mixin.jira = jira_client.jira
        mixin.preprocessor = Mock()
        mixin.preprocessor.markdown_to_jira = Mock(
            return_value="*This* is _Jira_ formatted"
        )
        mixin._clean_text = Mock(side_effect=lambda x: x)
        return mixin

    def test_public_false_calls_servicedesk_comment(self, comments_mixin):
        """add_comment(public=False) routes through _add_servicedesk_comment."""
        captured: list[tuple] = []
        original = comments_mixin._add_servicedesk_comment

        def spy(*args, **kwargs):
            captured.append((args, kwargs))
            return original(*args, **kwargs)

        comments_mixin._add_servicedesk_comment = spy
        response = {**self.SERVICEDESK_COMMENT_RESPONSE, "public": False}
        comments_mixin.jira.post.return_value = response

        comments_mixin.add_comment("ISSUE-1", "Internal note", public=False)

        assert len(captured) == 1
        assert captured[0][0] == ("ISSUE-1", "Internal note", False)  # noqa: FBT003

    def test_public_true_calls_servicedesk_comment(self, comments_mixin):
        """add_comment(public=True) routes through _add_servicedesk_comment."""
        captured: list[tuple] = []
        original = comments_mixin._add_servicedesk_comment

        def spy(*args, **kwargs):
            captured.append((args, kwargs))
            return original(*args, **kwargs)

        comments_mixin._add_servicedesk_comment = spy
        response = {**self.SERVICEDESK_COMMENT_RESPONSE, "public": True}
        comments_mixin.jira.post.return_value = response

        comments_mixin.add_comment("ISSUE-1", "Customer reply", public=True)

        assert len(captured) == 1
        assert captured[0][0] == ("ISSUE-1", "Customer reply", True)  # noqa: FBT003

    def test_public_none_does_not_call_servicedesk_comment(self, comments_mixin):
        """add_comment(public=None default) does NOT call _add_servicedesk_comment."""
        captured: list[tuple] = []

        def spy(*args, **kwargs):
            captured.append((args, kwargs))

        comments_mixin._add_servicedesk_comment = spy
        mock_response = {
            "id": "10001",
            "body": "Normal comment",
            "created": "2024-01-01T10:00:00.000+0000",
            "author": {"displayName": "John Doe"},
        }
        comments_mixin._post_api3 = Mock(return_value=mock_response)

        comments_mixin.add_comment("ISSUE-1", "text")

        assert len(captured) == 0
