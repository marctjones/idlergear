"""Tests for wiki synchronization."""

from unittest.mock import patch


from idlergear.wiki import SyncResult, WikiPage, WikiSync


class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_str_empty(self):
        """Empty result shows no changes."""
        result = SyncResult(pushed=[], pulled=[], conflicts=[], errors=[])
        output = str(result)
        assert "No changes" in output or output == ""

    def test_str_with_pushed(self):
        """Result shows pushed items."""
        result = SyncResult(pushed=["Page1", "Page2"], pulled=[], conflicts=[], errors=[])
        output = str(result)
        assert "Pushed" in output
        assert "Page1" in output
        assert "Page2" in output

    def test_str_with_pulled(self):
        """Result shows pulled items."""
        result = SyncResult(pushed=[], pulled=["Page3"], conflicts=[], errors=[])
        output = str(result)
        assert "Pulled" in output
        assert "Page3" in output

    def test_str_with_conflicts(self):
        """Result shows conflicts."""
        result = SyncResult(pushed=[], pulled=[], conflicts=["Page4"], errors=[])
        output = str(result)
        assert "Conflict" in output or "conflict" in output
        assert "Page4" in output


class TestWikiSync:
    """Tests for WikiSync class."""

    def test_sync_bidirectional_references_as_dicts(self, temp_project):
        """Test that sync_bidirectional handles references returned as dicts."""
        # This tests the fix for issue #185
        # list_references() returns dicts, not objects with .title attribute

        wiki_sync = WikiSync(temp_project)

        # Mock the wiki directory to exist (so clone is not called)
        wiki_sync.wiki_dir.mkdir(parents=True, exist_ok=True)

        # Mock list_references to return dicts (the actual return type)
        mock_refs = [
            {"id": 1, "title": "Test Reference", "body": "Test content"},
            {"id": 2, "title": "Another Reference", "body": "More content"},
        ]

        # Mock list_wiki_pages to return empty (no wiki pages yet)
        with patch("idlergear.wiki.list_references", return_value=mock_refs):
            with patch.object(wiki_sync, "list_wiki_pages", return_value=[]):
                with patch.object(wiki_sync, "pull_wiki", return_value=True):
                    with patch.object(wiki_sync, "push_wiki", return_value=True):
                        with patch("idlergear.wiki.get_reference") as mock_get_ref:
                            mock_get_ref.return_value = {"body": "Test content"}

                            # This should NOT raise AttributeError: 'dict' object has no attribute 'title'
                            result = wiki_sync.sync_bidirectional()

                            # Should have pushed the references
                            assert isinstance(result, SyncResult)
                            assert "Test Reference" in result.pushed
                            assert "Another Reference" in result.pushed

    def test_sync_bidirectional_pull_from_wiki(self, temp_project):
        """Test pulling pages from wiki to references."""
        from datetime import datetime

        wiki_sync = WikiSync(temp_project)

        # Mock wiki directory to exist (so clone is not called)
        wiki_sync.wiki_dir.mkdir(parents=True, exist_ok=True)

        # Mock no local references
        mock_refs = []

        # Mock wiki pages
        mock_pages = [
            WikiPage(
                title="Wiki Page",
                content="Wiki content",
                path=wiki_sync.wiki_dir / "Wiki-Page.md",
                modified=datetime.now(),
            )
        ]

        with patch("idlergear.wiki.list_references", return_value=mock_refs):
            with patch.object(wiki_sync, "list_wiki_pages", return_value=mock_pages):
                with patch.object(wiki_sync, "pull_wiki", return_value=True):
                    with patch("idlergear.wiki.add_reference") as mock_add:
                        result = wiki_sync.sync_bidirectional()

                        # Should have pulled the wiki page
                        assert "Wiki Page" in result.pulled
                        mock_add.assert_called_once_with("Wiki Page", "Wiki content")

    def test_sync_bidirectional_conflict_detection(self, temp_project):
        """Test conflict detection when both local and remote differ."""
        from datetime import datetime

        wiki_sync = WikiSync(temp_project)

        # Mock wiki directory to exist (so clone is not called)
        wiki_sync.wiki_dir.mkdir(parents=True, exist_ok=True)

        # Local reference
        mock_refs = [{"id": 1, "title": "Shared Doc", "body": "Local version"}]

        # Wiki page with different content
        mock_pages = [
            WikiPage(
                title="Shared Doc",
                content="Remote version",
                path=wiki_sync.wiki_dir / "Shared-Doc.md",
                modified=datetime.now(),
            )
        ]

        with patch("idlergear.wiki.list_references", return_value=mock_refs):
            with patch.object(wiki_sync, "list_wiki_pages", return_value=mock_pages):
                with patch.object(wiki_sync, "pull_wiki", return_value=True):
                    with patch("idlergear.wiki.get_reference") as mock_get:
                        mock_get.return_value = {"body": "Local version"}

                        # Default conflict resolution is "manual"
                        result = wiki_sync.sync_bidirectional()

                        # Should detect conflict
                        assert "Shared Doc" in result.conflicts


class TestWikiPage:
    """Tests for WikiPage dataclass."""

    def test_wiki_page_creation(self, temp_project):
        """Test WikiPage can be created with required fields."""
        from datetime import datetime

        page = WikiPage(
            title="Test Page",
            content="Some content",
            path=temp_project / "test.md",
            modified=datetime.now(),
        )

        assert page.title == "Test Page"
        assert page.content == "Some content"
        assert page.path == temp_project / "test.md"
