"""Tests for Telegram handler (with mocking)"""

from unittest.mock import patch, MagicMock
import requests
from video_summary_bot.handlers.telegram import TelegramHandler


class TestTelegramHandler:
    """Tests for the TelegramHandler class with mocked HTTP calls"""

    def setup_method(self):
        self.handler = TelegramHandler("test_token", "test_chat_id")

    def test_init_builds_correct_url(self):
        assert self.handler.base_url == "https://api.telegram.org/bottest_token"
        assert self.handler.bot_token == "test_token"
        assert self.handler.chat_id == "test_chat_id"

    # --- send_message ---

    @patch("video_summary_bot.handlers.telegram.requests.post")
    def test_send_message_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = self.handler.send_message("Hello", parse_mode=None)
        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["chat_id"] == "test_chat_id"
        assert call_kwargs["json"]["text"] == "Hello"

    @patch("video_summary_bot.handlers.telegram.requests.post")
    def test_send_message_with_parse_mode(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        self.handler.send_message("Hello", parse_mode="Markdown")
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["parse_mode"] == "Markdown"

    @patch("video_summary_bot.handlers.telegram.requests.post")
    def test_send_message_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        result = self.handler.send_message("Hello", parse_mode=None)
        assert result is False

    @patch("video_summary_bot.handlers.telegram.requests.post")
    def test_send_message_exception(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("Network error")
        result = self.handler.send_message("Hello", parse_mode=None)
        assert result is False

    @patch("video_summary_bot.handlers.telegram.requests.post")
    def test_send_long_message_splitting(self, mock_post):
        """Messages longer than 4000 chars should be split"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        long_message = "A" * 5000
        result = self.handler.send_message(long_message, parse_mode=None)
        # Should have been called twice (split into 2 parts)
        assert mock_post.call_count == 2
        assert result is True

    # --- send_photo ---

    @patch("video_summary_bot.handlers.telegram.requests.post")
    def test_send_photo_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = self.handler.send_photo("https://example.com/photo.jpg", caption="Test caption")
        assert result is True
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["photo"] == "https://example.com/photo.jpg"
        assert call_kwargs["json"]["caption"] == "Test caption"

    @patch("video_summary_bot.handlers.telegram.requests.post")
    def test_send_photo_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        result = self.handler.send_photo("https://example.com/photo.jpg")
        assert result is False

    # --- test_connection ---

    @patch.object(TelegramHandler, "send_message")
    def test_test_connection_success(self, mock_send):
        mock_send.return_value = True
        result = self.handler.test_connection()
        assert result is True

    @patch.object(TelegramHandler, "send_message")
    def test_test_connection_failure(self, mock_send):
        mock_send.return_value = False
        result = self.handler.test_connection()
        assert result is False

    # --- get_bot_info ---

    @patch("video_summary_bot.handlers.telegram.requests.get")
    def test_get_bot_info_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"first_name": "TestBot", "username": "test_bot"}}
        mock_get.return_value = mock_response

        result = self.handler.get_bot_info()
        assert result is not None
        assert result["result"]["first_name"] == "TestBot"

    @patch("video_summary_bot.handlers.telegram.requests.get")
    def test_get_bot_info_failure(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = self.handler.get_bot_info()
        assert result is None

    # --- send_to_users ---

    @patch.object(TelegramHandler, "send_message")
    def test_send_to_users_multiple(self, mock_send):
        mock_send.return_value = True
        results = self.handler.send_to_users("Hello", None, ["user1", "user2", "user3"])
        assert mock_send.call_count == 3
        assert results["user1"] is True
        assert results["user2"] is True
        assert results["user3"] is True

    @patch.object(TelegramHandler, "send_message")
    def test_send_to_users_mixed_results(self, mock_send):
        def side_effect(*args, **kwargs):
            # First call succeeds, second fails
            if self.handler.chat_id == "user1":
                return True
            return False

        mock_send.side_effect = side_effect
        results = self.handler.send_to_users("Hello", None, ["user1", "user2"])
        assert results["user1"] is True
        assert results["user2"] is False

    # --- listen_messages / get_last_message ---

    @patch.object(TelegramHandler, "listen_messages")
    def test_get_last_message_success(self, mock_listen):
        mock_listen.return_value = {
            "ok": True,
            "result": [
                {
                    "update_id": 100,
                    "message": {
                        "message_id": 50,
                        "chat": {"id": "123"},
                        "date": 1700000000,
                        "text": "Hello bot",
                    },
                }
            ],
        }

        result = self.handler.get_last_message()
        assert result is not None
        assert result["update_id"] == 100
        assert result["message"]["text"] == "Hello bot"

    @patch.object(TelegramHandler, "listen_messages")
    def test_get_last_message_no_updates(self, mock_listen):
        mock_listen.return_value = {"ok": True, "result": []}
        result = self.handler.get_last_message()
        assert result is None

    @patch.object(TelegramHandler, "listen_messages")
    def test_get_last_message_api_error(self, mock_listen):
        mock_listen.return_value = {"ok": False, "error_code": 401}
        result = self.handler.get_last_message()
        assert result is None

    @patch.object(TelegramHandler, "listen_messages")
    def test_get_last_message_with_offset(self, mock_listen):
        mock_listen.return_value = {
            "ok": True,
            "result": [{"update_id": 101, "message": {"text": "New msg"}}],
        }
        result = self.handler.get_last_message(offset=100)
        assert result["update_id"] == 101
        mock_listen.assert_called_once_with(offset=100)

    @patch.object(TelegramHandler, "listen_messages")
    def test_get_last_message_exception(self, mock_listen):
        mock_listen.side_effect = Exception("Network error")
        result = self.handler.get_last_message()
        assert result is None
