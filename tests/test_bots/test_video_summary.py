"""Tests for video_summary bot (with mocking)"""

from unittest.mock import patch, MagicMock
from video_summary_bot.bots.video_summary import main


class TestVideoSummaryBot:
    """Tests for the video_summary bot main function"""

    @patch("video_summary_bot.bots.video_summary.Database")
    @patch("video_summary_bot.bots.video_summary.YouTubeHandler")
    @patch("video_summary_bot.bots.video_summary.GeminiHandler")
    @patch("video_summary_bot.bots.video_summary.TelegramHandler")
    def test_main_processes_all_channels(
        self, mock_telegram_cls, mock_gemini_cls, mock_yt_cls, mock_db_cls
    ):
        """Should process all active channels with subscribers"""
        mock_db = MagicMock()
        mock_db.get_all_channels.return_value = [
            {"channel_handle": "@Ch1", "channel_name": "Ch1", "active": 1},
            {"channel_handle": "@Ch2", "channel_name": "Ch2", "active": 1},
        ]
        mock_db.get_channel_subscribers.side_effect = lambda ch: ["user1", "user2"]
        mock_db_cls.return_value = mock_db

        mock_yt = MagicMock()
        mock_yt.get_video_info_with_transcript.return_value = {
            "id": "vid123",
            "title": "Test Video",
            "channel_title": "Test Channel",
            "transcript": "Full transcript text",
        }
        mock_yt_cls.return_value = mock_yt

        mock_gemini = MagicMock()
        mock_gemini.summarize_video.return_value = "Generated summary"
        mock_gemini_cls.return_value = mock_gemini

        mock_telegram = MagicMock()
        mock_telegram_cls.return_value = mock_telegram

        main()

        # Should have called get_video_info_with_transcript for each channel
        assert mock_yt.get_video_info_with_transcript.call_count == 2
        # Should have generated summaries for each channel
        assert mock_gemini.summarize_video.call_count == 2
        # Should have sent messages to users
        assert mock_telegram.send_to_users.call_count == 2

    @patch("video_summary_bot.bots.video_summary.Database")
    @patch("video_summary_bot.bots.video_summary.YouTubeHandler")
    @patch("video_summary_bot.bots.video_summary.GeminiHandler")
    @patch("video_summary_bot.bots.video_summary.TelegramHandler")
    def test_main_skips_channel_without_subscribers(
        self, mock_telegram_cls, mock_gemini_cls, mock_yt_cls, mock_db_cls
    ):
        """Channels with no subscribers should be skipped"""
        mock_db = MagicMock()
        mock_db.get_all_channels.return_value = [
            {"channel_handle": "@EmptyCh", "channel_name": "Empty", "active": 1},
        ]
        mock_db.get_channel_subscribers.return_value = []
        mock_db_cls.return_value = mock_db

        mock_yt = MagicMock()
        mock_yt_cls.return_value = mock_yt

        mock_gemini = MagicMock()
        mock_gemini_cls.return_value = mock_gemini

        mock_telegram = MagicMock()
        mock_telegram_cls.return_value = mock_telegram

        main()

        mock_yt.get_video_info_with_transcript.assert_not_called()
        mock_gemini.summarize_video.assert_not_called()
        mock_telegram.send_to_users.assert_not_called()

    @patch("video_summary_bot.bots.video_summary.Database")
    @patch("video_summary_bot.bots.video_summary.YouTubeHandler")
    @patch("video_summary_bot.bots.video_summary.GeminiHandler")
    @patch("video_summary_bot.bots.video_summary.TelegramHandler")
    def test_main_skips_channel_without_video(
        self, mock_telegram_cls, mock_gemini_cls, mock_yt_cls, mock_db_cls
    ):
        """Channels with no video today should not trigger summarization"""
        mock_db = MagicMock()
        mock_db.get_all_channels.return_value = [
            {"channel_handle": "@Ch1", "channel_name": "Ch1", "active": 1},
        ]
        mock_db.get_channel_subscribers.return_value = ["user1"]
        mock_db_cls.return_value = mock_db

        mock_yt = MagicMock()
        mock_yt.get_video_info_with_transcript.return_value = None
        mock_yt_cls.return_value = mock_yt

        mock_gemini = MagicMock()
        mock_gemini_cls.return_value = mock_gemini

        mock_telegram = MagicMock()
        mock_telegram_cls.return_value = mock_telegram

        main()

        mock_gemini.summarize_video.assert_not_called()
        mock_telegram.send_to_users.assert_not_called()

    @patch("video_summary_bot.bots.video_summary.Database")
    @patch("video_summary_bot.bots.video_summary.YouTubeHandler")
    @patch("video_summary_bot.bots.video_summary.GeminiHandler")
    @patch("video_summary_bot.bots.video_summary.TelegramHandler")
    def test_main_skips_channel_without_transcript(
        self, mock_telegram_cls, mock_gemini_cls, mock_yt_cls, mock_db_cls
    ):
        """Video info without transcript should not trigger summarization"""
        mock_db = MagicMock()
        mock_db.get_all_channels.return_value = [
            {"channel_handle": "@Ch1", "channel_name": "Ch1", "active": 1},
        ]
        mock_db.get_channel_subscribers.return_value = ["user1"]
        mock_db_cls.return_value = mock_db

        mock_yt = MagicMock()
        mock_yt.get_video_info_with_transcript.return_value = {
            "id": "vid123",
            "title": "Test Video",
            "channel_title": "Test Channel",
        }  # No 'transcript' key
        mock_yt_cls.return_value = mock_yt

        mock_gemini = MagicMock()
        mock_gemini_cls.return_value = mock_gemini

        mock_telegram = MagicMock()
        mock_telegram_cls.return_value = mock_telegram

        main()

        mock_gemini.summarize_video.assert_not_called()
        mock_telegram.send_to_users.assert_not_called()

    @patch("video_summary_bot.bots.video_summary.Database")
    @patch("video_summary_bot.bots.video_summary.YouTubeHandler")
    @patch("video_summary_bot.bots.video_summary.TelegramHandler")
    def test_main_no_active_channels(self, mock_telegram_cls, mock_yt_cls, mock_db_cls):
        """Should exit early if no active channels"""
        mock_db = MagicMock()
        mock_db.get_all_channels.return_value = []
        mock_db_cls.return_value = mock_db

        mock_yt = MagicMock()
        mock_yt_cls.return_value = mock_yt

        mock_gemini_cls = MagicMock()

        mock_telegram = MagicMock()
        mock_telegram_cls.return_value = mock_telegram

        with patch("video_summary_bot.bots.video_summary.GeminiHandler", mock_gemini_cls):
            main()

        mock_yt.get_video_info_with_transcript.assert_not_called()
