"""Tests for database operations (SQLite)"""

import pytest
from datetime import datetime


class TestDatabaseUsers:
    """Tests for user CRUD operations"""

    def test_add_user(self, sqlite_db):
        db = sqlite_db
        db.add_user(user_id="123", username="Alice")
        user = db.get_user("123")
        assert user is not None
        assert user["user_id"] == "123"
        assert user["username"] == "Alice"
        assert user["active"] == 1

    def test_add_user_without_username(self, sqlite_db):
        sqlite_db.add_user(user_id="456")
        user = sqlite_db.get_user("456")
        assert user is not None
        assert user["user_id"] == "456"
        assert user["username"] is None

    def test_add_user_default_active(self, sqlite_db):
        sqlite_db.add_user(user_id="789")
        user = sqlite_db.get_user("789")
        assert user["active"] == 1

    def test_update_existing_user(self, sqlite_db):
        sqlite_db.add_user(user_id="123", username="Alice", active=True)
        sqlite_db.add_user(user_id="123", username="Alice Updated", active=False)
        user = sqlite_db.get_user("123")
        assert user["username"] == "Alice Updated"
        assert user["active"] == 0

    def test_get_nonexistent_user(self, sqlite_db):
        assert sqlite_db.get_user("nonexistent") is None

    def test_is_user_authorized(self, sqlite_db):
        sqlite_db.add_user(user_id="123", username="Alice", active=True)
        assert sqlite_db.is_user_authorized("123") is True

    def test_is_user_authorized_inactive_user(self, sqlite_db):
        sqlite_db.add_user(user_id="123", username="Alice", active=False)
        assert sqlite_db.is_user_authorized("123") is False

    def test_is_user_authorized_nonexistent(self, sqlite_db):
        assert sqlite_db.is_user_authorized("nonexistent") is False

    def test_deactivate_user(self, sqlite_db):
        sqlite_db.add_user(user_id="123", username="Alice", active=True)
        sqlite_db.deactivate_user("123")
        user = sqlite_db.get_user("123")
        assert user["active"] == 0

    def test_get_all_users_active_only(self, sqlite_db):
        sqlite_db.add_user(user_id="1", username="Active", active=True)
        sqlite_db.add_user(user_id="2", username="Inactive", active=False)
        users = sqlite_db.get_all_users(active_only=True)
        assert len(users) == 1
        assert users[0]["username"] == "Active"

    def test_get_all_users_include_inactive(self, sqlite_db):
        sqlite_db.add_user(user_id="1", username="Active", active=True)
        sqlite_db.add_user(user_id="2", username="Inactive", active=False)
        users = sqlite_db.get_all_users(active_only=False)
        assert len(users) == 2


class TestDatabaseChannels:
    """Tests for channel CRUD operations"""

    def test_add_channel(self, sqlite_db):
        sqlite_db.add_channel(
            channel_handle="@TestChannel",
            channel_name="Test Channel",
            youtube_channel_id="UCtest123",
            language="es",
        )
        channel = sqlite_db.get_channel("@TestChannel")
        assert channel is not None
        assert channel["channel_handle"] == "@TestChannel"
        assert channel["channel_name"] == "Test Channel"
        assert channel["youtube_channel_id"] == "UCtest123"
        assert channel["language"] == "es"

    def test_add_channel_defaults(self, sqlite_db):
        sqlite_db.add_channel(channel_handle="@MinimalChannel")
        channel = sqlite_db.get_channel("@MinimalChannel")
        assert channel is not None
        assert channel["language"] == "es"
        assert channel["check_start_hour"] == 10
        assert channel["check_start_minute"] == 0
        assert channel["check_end_hour"] == 14
        assert channel["check_interval_minutes"] == 5
        assert channel["active"] == 1

    def test_add_duplicate_channel_ignored(self, sqlite_db):
        sqlite_db.add_channel(channel_handle="@DupChannel", channel_name="First")
        sqlite_db.add_channel(channel_handle="@DupChannel", channel_name="Second")
        channel = sqlite_db.get_channel("@DupChannel")
        assert channel["channel_name"] == "First"

    def test_get_nonexistent_channel(self, sqlite_db):
        assert sqlite_db.get_channel("@Nonexistent") is None

    def test_get_all_channels(self, sqlite_db):
        sqlite_db.add_channel(channel_handle="@Ch1", channel_name="Ch1")
        sqlite_db.add_channel(channel_handle="@Ch2", channel_name="Ch2")
        channels = sqlite_db.get_all_channels()
        assert len(channels) == 2

    def test_get_all_channels_active_only(self, sqlite_db):
        sqlite_db.add_channel(channel_handle="@Active", channel_name="Active")
        # Manually add an inactive channel via direct SQL
        with sqlite_db.get_connection() as conn:
            conn.execute(
                "INSERT INTO channels (channel_handle, channel_name, active) VALUES (?, ?, 0)",
                ("@Inactive", "Inactive"),
            )
        channels = sqlite_db.get_all_channels(active_only=True)
        assert len(channels) == 1
        assert channels[0]["channel_handle"] == "@Active"


class TestDatabaseSubscriptions:
    """Tests for user-channel subscription operations"""

    def test_subscribe_user_to_channel(self, sqlite_db):
        sqlite_db.add_user(user_id="123", username="Alice")
        sqlite_db.add_channel(channel_handle="@Ch1")
        sqlite_db.subscribe_user_to_channel("123", "@Ch1")

        user_channels = sqlite_db.get_user_channels("123")
        assert len(user_channels) == 1
        assert user_channels[0]["channel_handle"] == "@Ch1"

    def test_subscribe_user_to_nonexistent_channel_raises(self, sqlite_db):
        sqlite_db.add_user(user_id="123", username="Alice")
        with pytest.raises(ValueError, match="not found"):
            sqlite_db.subscribe_user_to_channel("123", "@Nonexistent")

    def test_duplicate_subscription_ignored(self, sqlite_db):
        sqlite_db.add_user(user_id="123", username="Alice")
        sqlite_db.add_channel(channel_handle="@Ch1")
        sqlite_db.subscribe_user_to_channel("123", "@Ch1")
        sqlite_db.subscribe_user_to_channel("123", "@Ch1")

        user_channels = sqlite_db.get_user_channels("123")
        assert len(user_channels) == 1

    def test_unsubscribe_user_from_channel(self, sqlite_db):
        sqlite_db.add_user(user_id="123", username="Alice")
        sqlite_db.add_channel(channel_handle="@Ch1")
        sqlite_db.subscribe_user_to_channel("123", "@Ch1")
        sqlite_db.unsubscribe_user_from_channel("123", "@Ch1")

        user_channels = sqlite_db.get_user_channels("123")
        assert len(user_channels) == 0

    def test_get_channel_subscribers(self, sqlite_db):
        sqlite_db.add_user(user_id="1", username="Alice")
        sqlite_db.add_user(user_id="2", username="Bob")
        sqlite_db.add_channel(channel_handle="@Ch1")
        sqlite_db.subscribe_user_to_channel("1", "@Ch1")
        sqlite_db.subscribe_user_to_channel("2", "@Ch1")

        subscribers = sqlite_db.get_channel_subscribers("@Ch1")
        assert len(subscribers) == 2
        assert "1" in subscribers
        assert "2" in subscribers

    def test_get_channel_subscribers_excludes_inactive_users(self, sqlite_db):
        sqlite_db.add_user(user_id="1", username="Alice", active=True)
        sqlite_db.add_user(user_id="2", username="Bob", active=False)
        sqlite_db.add_channel(channel_handle="@Ch1")
        sqlite_db.subscribe_user_to_channel("1", "@Ch1")
        sqlite_db.subscribe_user_to_channel("2", "@Ch1")

        subscribers = sqlite_db.get_channel_subscribers("@Ch1")
        assert len(subscribers) == 1
        assert "1" in subscribers


class TestDatabaseSummaries:
    """Tests for summary logging and retrieval"""

    def test_add_summary(self, sqlite_db):
        sqlite_db.add_summary(
            channel_handle="@Ch1",
            video_id="vid123",
            video_title="Test Video",
            video_url="https://youtube.com/watch?v=vid123",
            summary_text="This is a summary.",
            video_date="2025-01-01",
            success=True,
        )
        summary = sqlite_db.get_summary_by_video_id("vid123")
        assert summary is not None
        assert summary["video_id"] == "vid123"
        assert summary["video_title"] == "Test Video"
        assert summary["summary_text"] == "This is a summary."

    def test_add_summary_default_date(self, sqlite_db):
        sqlite_db.add_summary(
            channel_handle="@Ch1",
            video_id="vid123",
            video_title="Test Video",
            video_url="https://youtube.com/watch?v=vid123",
            summary_text="Summary",
        )
        summaries = sqlite_db.get_summaries()
        assert len(summaries) == 1
        assert summaries[0]["video_date"] == datetime.now().strftime("%Y-%m-%d")

    def test_has_video_been_processed(self, sqlite_db):
        sqlite_db.add_summary(
            channel_handle="@Ch1",
            video_id="vid123",
            video_title="Test",
            video_url="https://youtube.com/watch?v=vid123",
            summary_text="Summary",
            video_date="2025-01-01",
            success=True,
        )
        assert sqlite_db.has_video_been_processed("@Ch1", "2025-01-01") is True
        assert sqlite_db.has_video_been_processed("@Ch1", "2025-01-02") is False

    def test_has_video_been_processed_failed_video(self, sqlite_db):
        sqlite_db.add_summary(
            channel_handle="@Ch1",
            video_id="vid123",
            video_title="Test",
            video_url="https://youtube.com/watch?v=vid123",
            summary_text="",
            video_date="2025-01-01",
            success=False,
        )
        # Failed videos should not count as "processed" for the daily check
        assert sqlite_db.has_video_been_processed("@Ch1", "2025-01-01") is False

    def test_has_video_id_been_processed(self, sqlite_db):
        sqlite_db.add_summary(
            channel_handle="@Ch1",
            video_id="vid123",
            video_title="Test",
            video_url="https://youtube.com/watch?v=vid123",
            summary_text="Summary",
            success=True,
        )
        assert sqlite_db.has_video_id_been_processed("vid123") is True
        assert sqlite_db.has_video_id_been_processed("nonexistent") is False

    def test_has_video_id_been_processed_failed_video(self, sqlite_db):
        sqlite_db.add_summary(
            channel_handle="@Ch1",
            video_id="vid123",
            video_title="Test",
            video_url="https://youtube.com/watch?v=vid123",
            summary_text="",
            success=False,
        )
        assert sqlite_db.has_video_id_been_processed("vid123") is False

    def test_get_summaries_filter_by_channel(self, sqlite_db):
        sqlite_db.add_summary(
            channel_handle="@Ch1", video_id="v1", video_title="T1",
            video_url="https://youtube.com/watch?v=v1", summary_text="S1", success=True,
        )
        sqlite_db.add_summary(
            channel_handle="@Ch2", video_id="v2", video_title="T2",
            video_url="https://youtube.com/watch?v=v2", summary_text="S2", success=True,
        )
        summaries = sqlite_db.get_summaries(channel_handle="@Ch1")
        assert len(summaries) == 1
        assert summaries[0]["channel_handle"] == "@Ch1"

    def test_get_summaries_filter_by_date(self, sqlite_db):
        sqlite_db.add_summary(
            channel_handle="@Ch1", video_id="v1", video_title="T1",
            video_url="https://youtube.com/watch?v=v1", summary_text="S1",
            video_date="2025-01-01", success=True,
        )
        sqlite_db.add_summary(
            channel_handle="@Ch1", video_id="v2", video_title="T2",
            video_url="https://youtube.com/watch?v=v2", summary_text="S2",
            video_date="2025-01-02", success=True,
        )
        summaries = sqlite_db.get_summaries(date="2025-01-01")
        assert len(summaries) == 1
        assert summaries[0]["video_date"] == "2025-01-01"

    def test_get_summaries_limit(self, sqlite_db):
        for i in range(5):
            sqlite_db.add_summary(
                channel_handle="@Ch1", video_id=f"v{i}", video_title=f"T{i}",
                video_url=f"https://youtube.com/watch?v=v{i}", summary_text=f"S{i}", success=True,
            )
        summaries = sqlite_db.get_summaries(limit=2)
        assert len(summaries) == 2
