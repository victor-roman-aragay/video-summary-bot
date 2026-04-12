"""Tests for scheduler (with mocking)

Note: The scheduler creates module-level globals (db, yt_rss, gemini, telegram)
at import time. These tests ensure DATABASE_URL is unset so SQLite is used,
and patch the module-level objects directly.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def force_sqlite_and_clean_scheduler(monkeypatch):
    """Ensure scheduler uses SQLite and clean up module cache"""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("USE_SUPABASE", "false")
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        monkeypatch.setenv("SQLITE_DB_PATH", f.name)
        db_path = f.name
    # Clear scheduler-related modules so they reimport cleanly
    for mod_key in list(sys.modules.keys()):
        if "scheduler" in mod_key:
            del sys.modules[mod_key]
    yield
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestCheckAndSendVideo:
    """Tests for the check_and_send_video function"""

    def test_skips_already_processed_today(self, mocker):
        import video_summary_bot.scheduler as sched
        mock_db = mocker.patch.object(sched, "db")
        mock_db.has_video_been_processed.return_value = True

        sched.check_and_send_video("@Ch1", "UCtest123", ["es"])

        mock_db.has_video_been_processed.assert_called_once()
        mock_db.get_channel_subscribers.assert_not_called()

    def test_skips_channel_without_subscribers(self, mocker):
        import video_summary_bot.scheduler as sched
        mock_db = mocker.patch.object(sched, "db")
        mock_db.has_video_been_processed.return_value = False
        mock_db.get_channel_subscribers.return_value = []

        sched.check_and_send_video("@Ch1", "UCtest123", ["es"])

        mock_db.get_channel_subscribers.assert_called_once_with("@Ch1")

    def test_skips_channel_without_youtube_id(self, mocker):
        import video_summary_bot.scheduler as sched
        mock_db = mocker.patch.object(sched, "db")
        mock_db.has_video_been_processed.return_value = False
        mock_db.get_channel_subscribers.return_value = ["user1"]

        sched.check_and_send_video("@Ch1", None, ["es"])

        mock_db.get_channel_subscribers.assert_called_once()

    def test_processes_video_successfully(self, mocker):
        import video_summary_bot.scheduler as sched
        mock_db = mocker.patch.object(sched, "db")
        mock_yt_rss = mocker.patch.object(sched, "yt_rss")
        mock_gemini = mocker.patch.object(sched, "gemini")
        mock_telegram = mocker.patch.object(sched, "telegram")

        mock_db.has_video_been_processed.return_value = False
        mock_db.get_channel_subscribers.return_value = ["user1", "user2"]
        mock_yt_rss.get_video_info_with_transcript.return_value = {
            "video_id": "vid123",
            "title": "Today's Video",
            "channel_title": "Test Channel",
            "url": "https://youtube.com/watch?v=vid123",
            "transcript": "Full transcript",
        }
        mock_gemini.summarize_video.return_value = "Generated summary"

        sched.check_and_send_video("@Ch1", "UCtest123", ["es"])

        mock_yt_rss.get_video_info_with_transcript.assert_called_once_with("UCtest123", ["es"])
        mock_gemini.summarize_video.assert_called_once()
        mock_telegram.send_to_users.assert_called_once()
        mock_db.add_summary.assert_called_once()

    def test_logs_failed_summary_attempt(self, mocker):
        import video_summary_bot.scheduler as sched
        mock_db = mocker.patch.object(sched, "db")
        mock_yt_rss = mocker.patch.object(sched, "yt_rss")
        mock_gemini = mocker.patch.object(sched, "gemini")

        mock_db.has_video_been_processed.return_value = False
        mock_db.get_channel_subscribers.return_value = ["user1"]
        mock_yt_rss.get_video_info_with_transcript.return_value = {
            "video_id": "vid123",
            "title": "Today's Video",
            "channel_title": "Test Channel",
            "url": "https://youtube.com/watch?v=vid123",
            "transcript": "Transcript",
        }
        mock_gemini.summarize_video.return_value = None

        sched.check_and_send_video("@Ch1", "UCtest123", ["es"])

        mock_db.add_summary.assert_called_once()
        call_kwargs = mock_db.add_summary.call_args[1]
        assert call_kwargs["success"] is False

    def test_no_video_found(self, mocker):
        import video_summary_bot.scheduler as sched
        mock_db = mocker.patch.object(sched, "db")
        mock_yt_rss = mocker.patch.object(sched, "yt_rss")

        mock_db.has_video_been_processed.return_value = False
        mock_db.get_channel_subscribers.return_value = ["user1"]
        mock_yt_rss.get_video_info_with_transcript.return_value = None

        sched.check_and_send_video("@Ch1", "UCtest123", ["es"])

        mock_db.add_summary.assert_not_called()

    def test_handles_exception_gracefully(self, mocker):
        import video_summary_bot.scheduler as sched
        mock_db = mocker.patch.object(sched, "db")
        mock_yt_rss = mocker.patch.object(sched, "yt_rss")

        mock_db.has_video_been_processed.return_value = False
        mock_db.get_channel_subscribers.return_value = ["user1"]
        mock_yt_rss.get_video_info_with_transcript.side_effect = Exception("RSS fetch error")

        # Should not raise
        sched.check_and_send_video("@Ch1", "UCtest123", ["es"])


class TestCheckAllChannels:
    """Tests for the check_all_channels function"""

    def test_processes_channels_within_time_window(self, mocker):
        import video_summary_bot.scheduler as sched
        mock_db = mocker.patch.object(sched, "db")
        mock_check = mocker.patch.object(sched, "check_and_send_video")

        mock_now = MagicMock()
        mock_now.hour = 12
        mock_now.minute = 0
        mocker.patch.object(sched, "datetime")
        sched.datetime.now.return_value = mock_now

        mock_db.get_all_channels.return_value = [
            {
                "channel_handle": "@Ch1",
                "check_start_hour": 10,
                "check_start_minute": 0,
                "check_end_hour": 14,
                "youtube_channel_id": "UC1",
                "language": "es",
            }
        ]
        mock_db.get_channel_subscribers.return_value = ["user1"]

        sched.check_all_channels()

        mock_check.assert_called_once_with("@Ch1", "UC1", ["es"])

    def test_skips_channels_outside_time_window(self, mocker):
        import video_summary_bot.scheduler as sched
        mock_db = mocker.patch.object(sched, "db")
        mock_check = mocker.patch.object(sched, "check_and_send_video")

        mock_now = MagicMock()
        mock_now.hour = 8
        mock_now.minute = 0
        mocker.patch.object(sched, "datetime")
        sched.datetime.now.return_value = mock_now

        mock_db.get_all_channels.return_value = [
            {
                "channel_handle": "@Ch1",
                "check_start_hour": 10,
                "check_start_minute": 0,
                "check_end_hour": 14,
                "youtube_channel_id": "UC1",
                "language": "es",
            }
        ]

        sched.check_all_channels()

        mock_check.assert_not_called()

    def test_skips_channels_without_subscribers(self, mocker):
        import video_summary_bot.scheduler as sched
        mock_db = mocker.patch.object(sched, "db")
        mock_check = mocker.patch.object(sched, "check_and_send_video")

        mock_now = MagicMock()
        mock_now.hour = 12
        mock_now.minute = 0
        mocker.patch.object(sched, "datetime")
        sched.datetime.now.return_value = mock_now

        mock_db.get_all_channels.return_value = [
            {
                "channel_handle": "@EmptyCh",
                "check_start_hour": 10,
                "check_start_minute": 0,
                "check_end_hour": 14,
                "youtube_channel_id": "UC1",
                "language": "es",
            }
        ]
        mock_db.get_channel_subscribers.return_value = []

        sched.check_all_channels()

        mock_check.assert_not_called()
