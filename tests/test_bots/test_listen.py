"""Tests for listen bot (with mocking)"""

from unittest.mock import patch, MagicMock
import os
from video_summary_bot.bots.listen import process_video_url, main


class TestProcessVideoUrl:
    """Tests for the process_video_url function"""

    def setup_method(self):
        self.mock_yt = MagicMock()
        self.mock_gemini = MagicMock()
        self.mock_telegram = MagicMock()
        self.mock_db = MagicMock()
        self.user_chat_id = "123456789"

    def test_cached_video_returns_existing_summary(self):
        self.mock_db.has_video_id_been_processed.return_value = True
        self.mock_db.get_summary_by_video_id.return_value = {
            "video_title": "Cached Video",
            "summary_text": "Cached summary text.",
            "video_url": "https://youtube.com/watch?v=cached123",
        }

        result = process_video_url(
            "cached123", self.user_chat_id,
            self.mock_yt, self.mock_gemini, self.mock_telegram, self.mock_db
        )

        assert result is True
        self.mock_yt.get_video_info.assert_not_called()
        self.mock_gemini.summarize_video.assert_not_called()
        self.mock_telegram.send_to_users.assert_called()

    def test_cached_video_not_found_in_db(self):
        """Video was processed before but summary is missing"""
        self.mock_db.has_video_id_been_processed.return_value = True
        self.mock_db.get_summary_by_video_id.return_value = None

        result = process_video_url(
            "cached123", self.user_chat_id,
            self.mock_yt, self.mock_gemini, self.mock_telegram, self.mock_db
        )

        # Should fall through to generating a new summary
        # (because existing_summary is None)
        # The function will try to generate a summary
        self.mock_yt.get_video_info.assert_called()

    def test_new_video_generates_summary(self):
        self.mock_db.has_video_id_been_processed.return_value = False
        self.mock_yt.get_video_info.return_value = {
            "id": "newVid123",
            "title": "New Video",
            "channel_title": "Test Channel",
        }
        self.mock_yt.get_transcript.return_value = "Full transcript text"
        self.mock_gemini.summarize_video.return_value = "Generated summary"

        result = process_video_url(
            "newVid123", self.user_chat_id,
            self.mock_yt, self.mock_gemini, self.mock_telegram, self.mock_db
        )

        assert result is True
        self.mock_gemini.summarize_video.assert_called_once()
        self.mock_db.add_summary.assert_called_once()
        self.mock_telegram.send_to_users.assert_called()

    def test_new_video_no_video_info(self):
        self.mock_db.has_video_id_been_processed.return_value = False
        self.mock_yt.get_video_info.return_value = None

        result = process_video_url(
            "badVid", self.user_chat_id,
            self.mock_yt, self.mock_gemini, self.mock_telegram, self.mock_db
        )

        assert result is False
        self.mock_gemini.summarize_video.assert_not_called()
        self.mock_db.add_summary.assert_not_called()

    def test_new_video_no_transcript(self):
        self.mock_db.has_video_id_been_processed.return_value = False
        self.mock_yt.get_video_info.return_value = {
            "id": "noTranscriptVid",
            "title": "Video Without Transcript",
            "channel_title": "Test Channel",
        }
        self.mock_yt.get_transcript.return_value = None

        result = process_video_url(
            "noTranscriptVid", self.user_chat_id,
            self.mock_yt, self.mock_gemini, self.mock_telegram, self.mock_db
        )

        assert result is False
        self.mock_gemini.summarize_video.assert_not_called()

    def test_new_video_gemini_fails(self):
        self.mock_db.has_video_id_been_processed.return_value = False
        self.mock_yt.get_video_info.return_value = {
            "id": "geminiFailVid",
            "title": "Video",
            "channel_title": "Test Channel",
        }
        self.mock_yt.get_transcript.return_value = "Transcript"
        self.mock_gemini.summarize_video.return_value = None

        result = process_video_url(
            "geminiFailVid", self.user_chat_id,
            self.mock_yt, self.mock_gemini, self.mock_telegram, self.mock_db
        )

        assert result is False
        self.mock_db.add_summary.assert_not_called()


class TestListenBotMain:
    """Tests for the main listen bot loop"""

    @patch("video_summary_bot.bots.listen.get_database")
    @patch("video_summary_bot.bots.listen.YouTubeHandler")
    @patch("video_summary_bot.bots.listen.GeminiHandler")
    @patch("video_summary_bot.bots.listen.TelegramHandler")
    def test_main_authorizes_known_user(
        self, mock_telegram_cls, mock_gemini_cls, mock_yt_cls, mock_get_db
    ):
        """A user in the database should be authorized to use the bot"""
        mock_db = MagicMock()
        mock_db.is_user_authorized.return_value = True
        mock_db.get_user.return_value = {"user_id": "123", "username": "Alice", "active": 1}
        mock_get_db.return_value = mock_db
        mock_db.get_all_users.return_value = [{"user_id": "123", "username": "Alice"}]

        mock_telegram = MagicMock()
        mock_telegram.get_last_message.side_effect = [
            {
                "update_id": 1,
                "message": {
                    "chat": {"id": "123", "first_name": "Alice", "username": "alice"},
                    "text": "https://www.youtube.com/watch?v=test123",
                },
            },
            None,  # Second call returns None to break the loop via our custom logic
        ]
        mock_telegram_cls.return_value = mock_telegram

        mock_yt = MagicMock()
        mock_yt.get_video_info.return_value = {
            "id": "test123", "title": "Test Video", "channel_title": "Ch",
        }
        mock_yt.get_transcript.return_value = "Transcript"
        mock_yt_cls.return_value = mock_yt

        mock_gemini = MagicMock()
        mock_gemini.summarize_video.return_value = "Summary"
        mock_gemini_cls.return_value = mock_gemini

        # Run main but break after first message to avoid infinite loop
        # We test the authorization flow by patching process_video_url and keyboard interrupt
        with patch("video_summary_bot.bots.listen.process_video_url") as mock_process:
            # Make get_last_message return None after first message to stop the loop
            call_count = [0]
            def message_side_effect(offset=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    return {
                        "update_id": 1,
                        "message": {
                            "chat": {"id": "123", "first_name": "Alice", "username": "alice"},
                            "text": "https://www.youtube.com/watch?v=test123",
                        },
                    }
                raise KeyboardInterrupt

            mock_telegram.get_last_message.side_effect = message_side_effect

            try:
                main()
            except KeyboardInterrupt:
                pass

            # Verify authorization was checked
            mock_db.is_user_authorized.assert_called_with("123")

    @patch("video_summary_bot.bots.listen.get_database")
    @patch("video_summary_bot.bots.listen.YouTubeHandler")
    @patch("video_summary_bot.bots.listen.GeminiHandler")
    @patch("video_summary_bot.bots.listen.TelegramHandler")
    def test_main_unauthorized_user_gets_registration_prompt(
        self, mock_telegram_cls, mock_gemini_cls, mock_yt_cls, mock_get_db
    ):
        """An unknown user should get a registration prompt"""
        mock_db = MagicMock()
        mock_db.is_user_authorized.return_value = False
        mock_db.get_all_users.return_value = []
        mock_get_db.return_value = mock_db

        mock_telegram = MagicMock()
        mock_telegram_cls.return_value = mock_telegram

        call_count = [0]
        def message_side_effect(offset=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return {
                    "update_id": 1,
                    "message": {
                        "chat": {"id": "999", "first_name": "Stranger", "username": "stranger"},
                        "text": "Hello bot",
                    },
                }
            raise KeyboardInterrupt
        mock_telegram.get_last_message.side_effect = message_side_effect

        try:
            main()
        except KeyboardInterrupt:
            pass

        mock_db.is_user_authorized.assert_called_with("999")
        mock_telegram.send_to_users.assert_called()
        call_args = mock_telegram.send_to_users.call_args[0][0]
        assert "not yet registered" in call_args.lower()
