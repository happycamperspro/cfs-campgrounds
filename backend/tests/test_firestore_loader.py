"""
Tests for the FirestoreLoader class.

All Firebase/Firestore interactions are mocked so tests run without
a live backend.
"""

import sys
from pathlib import Path

_backend_root = str(Path(__file__).resolve().parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from datetime import datetime, timezone
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest


@pytest.fixture()
def loader():
    """Return a FirestoreLoader instance with a fully mocked Firestore backend."""
    with patch.dict(sys.modules, {
        "firebase_admin": MagicMock(_apps={"[DEFAULT]": True}),
        "firebase_admin.credentials": MagicMock(),
        "firebase_admin.firestore": MagicMock(),
    }):
        # Re-import to get fresh module with mocked deps
        if "loaders.firestore_loader" in sys.modules:
            del sys.modules["loaders.firestore_loader"]

        from loaders.firestore_loader import FirestoreLoader

        # Mock the Firestore client returned during __init__
        with patch("loaders.firestore_loader.firestore") as mock_fs_module:
            mock_db = MagicMock()
            mock_fs_module.client.return_value = mock_db

            # Patch firebase_admin._apps so _init_firebase is a no-op
            with patch("loaders.firestore_loader.firebase_admin") as mock_fa:
                mock_fa._apps = {"[DEFAULT]": True}

                loader_instance = FirestoreLoader(
                    collection_name="test_campgrounds"
                )
                # Attach mocks for assertions
                loader_instance._mock_db = mock_db
                yield loader_instance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(doc_id, name="Test Camp"):
    """Create a minimal normalized campground record."""
    return {
        "_doc_id": doc_id,
        "name": name,
        "source": "test",
        "ratings": {"avgRating": 4.5, "totalReviews": 100},
        "metadata": {
            "createdAt": datetime(2024, 1, 1, tzinfo=timezone.utc),
            "updatedAt": datetime(2024, 6, 1, tzinfo=timezone.utc),
            "isActive": True,
        },
    }


def _mock_existing_docs(mock_db, doc_ids):
    """Configure mock_db so that get_existing_doc_ids returns *doc_ids*."""
    mock_docs = []
    for did in doc_ids:
        doc = MagicMock()
        doc.id = did
        mock_docs.append(doc)

    mock_collection = mock_db.collection.return_value
    mock_collection.select.return_value.stream.return_value = mock_docs


# ===================================================================
# upsert_batch – new records (creates)
# ===================================================================

class TestUpsertBatchCreate:
    """Test upsert_batch when records are new (not yet in Firestore)."""

    def test_creates_new_records(self, loader):
        _mock_existing_docs(loader._mock_db, [])  # nothing exists
        mock_batch = MagicMock()
        loader._mock_db.batch.return_value = mock_batch

        records = [_make_record("rec_1"), _make_record("rec_2")]
        stats = loader.upsert_batch(records)

        assert stats["created"] == 2
        assert stats["updated"] == 0
        assert stats["skipped"] == 0
        assert mock_batch.set.call_count == 2
        mock_batch.commit.assert_called_once()

    def test_ratings_kept_for_new_records(self, loader):
        """New records should keep their ratings field."""
        _mock_existing_docs(loader._mock_db, [])
        mock_batch = MagicMock()
        loader._mock_db.batch.return_value = mock_batch

        records = [_make_record("new_1")]
        loader.upsert_batch(records)

        # Check the data passed to batch.set contains ratings
        set_call = mock_batch.set.call_args_list[0]
        written_data = set_call[0][1]  # second positional arg is the data dict
        assert "ratings" in written_data


# ===================================================================
# upsert_batch – existing records (updates)
# ===================================================================

class TestUpsertBatchUpdate:
    """Test upsert_batch when records already exist (updates)."""

    def test_updates_existing_records(self, loader):
        _mock_existing_docs(loader._mock_db, ["rec_1", "rec_2"])
        mock_batch = MagicMock()
        loader._mock_db.batch.return_value = mock_batch

        records = [_make_record("rec_1"), _make_record("rec_2")]
        stats = loader.upsert_batch(records)

        assert stats["updated"] == 2
        assert stats["created"] == 0
        mock_batch.set.call_count == 2
        mock_batch.commit.assert_called_once()

    def test_ratings_stripped_for_updates(self, loader):
        """Existing records should have ratings stripped to protect user data."""
        _mock_existing_docs(loader._mock_db, ["existing_1"])
        mock_batch = MagicMock()
        loader._mock_db.batch.return_value = mock_batch

        records = [_make_record("existing_1")]
        loader.upsert_batch(records)

        set_call = mock_batch.set.call_args_list[0]
        written_data = set_call[0][1]
        assert "ratings" not in written_data

    def test_created_at_stripped_for_updates(self, loader):
        """Existing records should have metadata.createdAt stripped."""
        _mock_existing_docs(loader._mock_db, ["existing_1"])
        mock_batch = MagicMock()
        loader._mock_db.batch.return_value = mock_batch

        records = [_make_record("existing_1")]
        loader.upsert_batch(records)

        set_call = mock_batch.set.call_args_list[0]
        written_data = set_call[0][1]
        metadata = written_data.get("metadata", {})
        assert "createdAt" not in metadata

    def test_mixed_creates_and_updates(self, loader):
        """A batch with both new and existing records is handled correctly."""
        _mock_existing_docs(loader._mock_db, ["existing_1"])
        mock_batch = MagicMock()
        loader._mock_db.batch.return_value = mock_batch

        records = [_make_record("existing_1"), _make_record("new_1")]
        stats = loader.upsert_batch(records)

        assert stats["created"] == 1
        assert stats["updated"] == 1


# ===================================================================
# upsert_batch – dry_run
# ===================================================================

class TestUpsertBatchDryRun:
    """Test upsert_batch with dry_run=True."""

    def test_no_writes_in_dry_run(self, loader):
        _mock_existing_docs(loader._mock_db, [])
        mock_batch = MagicMock()
        loader._mock_db.batch.return_value = mock_batch

        records = [_make_record("dry_1"), _make_record("dry_2")]
        stats = loader.upsert_batch(records, dry_run=True)

        # Counts should still be tracked
        assert stats["created"] == 2

        # But no actual writes should happen
        mock_batch.set.assert_not_called()
        mock_batch.commit.assert_not_called()

    def test_dry_run_updates_also_no_writes(self, loader):
        _mock_existing_docs(loader._mock_db, ["dry_1"])
        mock_batch = MagicMock()
        loader._mock_db.batch.return_value = mock_batch

        records = [_make_record("dry_1")]
        stats = loader.upsert_batch(records, dry_run=True)

        assert stats["updated"] == 1
        mock_batch.set.assert_not_called()
        mock_batch.commit.assert_not_called()


# ===================================================================
# upsert_batch – records missing _doc_id
# ===================================================================

class TestUpsertBatchMissingDocId:
    """Test that records without _doc_id are skipped."""

    def test_missing_doc_id_skipped(self, loader):
        _mock_existing_docs(loader._mock_db, [])
        mock_batch = MagicMock()
        loader._mock_db.batch.return_value = mock_batch

        records = [
            {"name": "No ID Camp", "source": "test"},  # no _doc_id
            _make_record("valid_1"),
        ]
        stats = loader.upsert_batch(records)

        assert stats["skipped"] == 1
        assert stats["created"] == 1
        # Only the valid record should be written
        assert mock_batch.set.call_count == 1

    def test_none_doc_id_skipped(self, loader):
        _mock_existing_docs(loader._mock_db, [])
        mock_batch = MagicMock()
        loader._mock_db.batch.return_value = mock_batch

        records = [{"_doc_id": None, "name": "Null ID Camp"}]
        stats = loader.upsert_batch(records)

        assert stats["skipped"] == 1
        assert stats["created"] == 0
        mock_batch.set.assert_not_called()

    def test_empty_string_doc_id_skipped(self, loader):
        _mock_existing_docs(loader._mock_db, [])
        mock_batch = MagicMock()
        loader._mock_db.batch.return_value = mock_batch

        records = [{"_doc_id": "", "name": "Empty ID Camp"}]
        stats = loader.upsert_batch(records)

        assert stats["skipped"] == 1
        mock_batch.set.assert_not_called()

    def test_all_invalid_records(self, loader):
        _mock_existing_docs(loader._mock_db, [])
        mock_batch = MagicMock()
        loader._mock_db.batch.return_value = mock_batch

        records = [
            {"name": "Bad 1"},
            {"_doc_id": None, "name": "Bad 2"},
            {"_doc_id": "", "name": "Bad 3"},
        ]
        stats = loader.upsert_batch(records)

        assert stats["skipped"] == 3
        assert stats["created"] == 0
        mock_batch.set.assert_not_called()


# ===================================================================
# _remove_none_values
# ===================================================================

class TestRemoveNoneValues:
    """Test the _remove_none_values static helper."""

    def test_removes_top_level_none(self, loader):
        from loaders.firestore_loader import FirestoreLoader

        data = {"a": 1, "b": None, "c": "hello"}
        result = FirestoreLoader._remove_none_values(data)
        assert result == {"a": 1, "c": "hello"}

    def test_removes_nested_none(self, loader):
        from loaders.firestore_loader import FirestoreLoader

        data = {
            "top": "value",
            "nested": {
                "keep": 42,
                "drop": None,
                "deep": {
                    "also_keep": True,
                    "also_drop": None,
                },
            },
        }
        result = FirestoreLoader._remove_none_values(data)
        assert result == {
            "top": "value",
            "nested": {
                "keep": 42,
                "deep": {
                    "also_keep": True,
                },
            },
        }

    def test_empty_nested_dict_removed(self, loader):
        """A nested dict that becomes empty after pruning is removed."""
        from loaders.firestore_loader import FirestoreLoader

        data = {"a": 1, "b": {"only_none": None}}
        result = FirestoreLoader._remove_none_values(data)
        assert result == {"a": 1}

    def test_non_dict_returned_as_is(self, loader):
        from loaders.firestore_loader import FirestoreLoader

        assert FirestoreLoader._remove_none_values("hello") == "hello"
        assert FirestoreLoader._remove_none_values(42) == 42
        assert FirestoreLoader._remove_none_values([1, None, 3]) == [1, None, 3]

    def test_empty_dict(self, loader):
        from loaders.firestore_loader import FirestoreLoader

        result = FirestoreLoader._remove_none_values({})
        assert result == {}

    def test_all_none_values(self, loader):
        from loaders.firestore_loader import FirestoreLoader

        data = {"a": None, "b": None}
        result = FirestoreLoader._remove_none_values(data)
        assert result == {}

    def test_lists_inside_dict_preserved(self, loader):
        """Lists are not recursed into -- None values inside lists remain."""
        from loaders.firestore_loader import FirestoreLoader

        data = {"items": [1, None, 3], "name": "test"}
        result = FirestoreLoader._remove_none_values(data)
        assert result == {"items": [1, None, 3], "name": "test"}


# ===================================================================
# get_existing_doc_ids
# ===================================================================

class TestGetExistingDocIds:
    """Test get_existing_doc_ids."""

    def test_returns_set_of_ids(self, loader):
        mock_docs = []
        for doc_id in ["doc_a", "doc_b", "doc_c"]:
            doc = MagicMock()
            doc.id = doc_id
            mock_docs.append(doc)

        mock_collection = loader._mock_db.collection.return_value
        mock_collection.select.return_value.stream.return_value = mock_docs

        result = loader.get_existing_doc_ids()

        assert isinstance(result, set)
        assert result == {"doc_a", "doc_b", "doc_c"}

    def test_empty_collection(self, loader):
        mock_collection = loader._mock_db.collection.return_value
        mock_collection.select.return_value.stream.return_value = []

        result = loader.get_existing_doc_ids()

        assert result == set()

    def test_uses_select_empty_for_efficiency(self, loader):
        """Verify select([]) is called for a metadata-only query."""
        mock_collection = loader._mock_db.collection.return_value
        mock_collection.select.return_value.stream.return_value = []

        loader.get_existing_doc_ids()

        mock_collection.select.assert_called_once_with([])


# ===================================================================
# delete_stale_records
# ===================================================================

class TestDeleteStaleRecords:
    """Test delete_stale_records (soft-delete)."""

    def test_deactivates_stale_records(self, loader):
        """Records not in active_doc_ids are soft-deleted."""
        # Existing: a, b, c.  Active: a, b.  Stale: c.
        _mock_existing_docs(loader._mock_db, ["rec_a", "rec_b", "rec_c"])
        mock_batch = MagicMock()
        loader._mock_db.batch.return_value = mock_batch

        count = loader.delete_stale_records(
            active_doc_ids={"rec_a", "rec_b"}
        )

        assert count == 1
        # batch.update should be called for the stale record
        mock_batch.update.assert_called_once()
        update_args = mock_batch.update.call_args
        update_data = update_args[0][1]
        assert update_data["metadata.isActive"] is False
        assert "metadata.deactivatedAt" in update_data
        mock_batch.commit.assert_called_once()

    def test_no_stale_records(self, loader):
        """When all records are active, nothing is deactivated."""
        _mock_existing_docs(loader._mock_db, ["rec_a", "rec_b"])
        mock_batch = MagicMock()
        loader._mock_db.batch.return_value = mock_batch

        count = loader.delete_stale_records(
            active_doc_ids={"rec_a", "rec_b"}
        )

        assert count == 0
        mock_batch.update.assert_not_called()

    def test_dry_run_no_writes(self, loader):
        """dry_run=True logs but does not write."""
        _mock_existing_docs(loader._mock_db, ["rec_a", "rec_stale"])
        mock_batch = MagicMock()
        loader._mock_db.batch.return_value = mock_batch

        count = loader.delete_stale_records(
            active_doc_ids={"rec_a"},
            dry_run=True,
        )

        assert count == 1  # still counted
        mock_batch.update.assert_not_called()
        mock_batch.commit.assert_not_called()

    def test_multiple_stale_records(self, loader):
        """Multiple stale records are all soft-deleted."""
        _mock_existing_docs(loader._mock_db, ["a", "b", "c", "d", "e"])
        mock_batch = MagicMock()
        loader._mock_db.batch.return_value = mock_batch

        count = loader.delete_stale_records(active_doc_ids={"a", "b"})

        assert count == 3
        assert mock_batch.update.call_count == 3
        mock_batch.commit.assert_called()


# ===================================================================
# upsert_batch – empty record list
# ===================================================================

class TestUpsertBatchEmpty:
    """Test upsert_batch with an empty list."""

    def test_empty_records_returns_zero_stats(self, loader):
        stats = loader.upsert_batch([])

        assert stats == {
            "created": 0,
            "updated": 0,
            "failed": 0,
            "skipped": 0,
        }
