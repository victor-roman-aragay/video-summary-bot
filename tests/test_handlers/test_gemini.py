"""Tests for Gemini handler (with mocking)"""

from unittest.mock import patch, MagicMock
from video_summary_bot.handlers.gemini import GeminiHandler


class TestGeminiHandler:
    """Tests for the GeminiHandler class with mocked API calls"""

    def setup_method(self):
        self.handler = GeminiHandler("test_gemini_key")

    @patch("video_summary_bot.handlers.gemini.genai")
    def test_init_configures_genai(self, mock_genai):
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        handler = GeminiHandler("test_key")

        mock_genai.configure.assert_called_once_with(api_key="test_key")
        mock_genai.GenerativeModel.assert_called_once_with("gemini-3.1-flash-lite-preview")

    # --- summarize_video ---

    @patch.object(GeminiHandler, "__init__", lambda self, key: None)
    def test_summarize_video_success(self):
        self.handler.model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "This is the generated summary."
        self.handler.model.generate_content.return_value = mock_response

        result = self.handler.summarize_video(
            transcript="Test transcript content",
            video_title="Test Video",
            channel_name="Test Channel",
        )
        assert result == "This is the generated summary."

    @patch.object(GeminiHandler, "__init__", lambda self, key: None)
    def test_summarize_video_empty_response(self):
        self.handler.model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = None
        self.handler.model.generate_content.return_value = mock_response

        result = self.handler.summarize_video("transcript", "title", "channel")
        assert result is None

    @patch.object(GeminiHandler, "__init__", lambda self, key: None)
    def test_summarize_video_api_error(self):
        self.handler.model = MagicMock()
        self.handler.model.generate_content.side_effect = Exception("API error")

        result = self.handler.summarize_video("transcript", "title", "channel")
        assert result is None

    # --- get_todays_news ---

    @patch.object(GeminiHandler, "__init__", lambda self, key: None)
    def test_get_todays_news_success(self):
        self.handler.model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Today's financial news summary."
        self.handler.model.generate_content.return_value = mock_response

        result = self.handler.get_todays_news()
        assert result == "Today's financial news summary."

    @patch.object(GeminiHandler, "__init__", lambda self, key: None)
    def test_get_todays_news_empty_response(self):
        self.handler.model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = ""
        # Empty string is truthy in Python, but let's test with None
        mock_response.text = None
        self.handler.model.generate_content.return_value = mock_response

        result = self.handler.get_todays_news()
        assert result is None

    @patch.object(GeminiHandler, "__init__", lambda self, key: None)
    def test_get_todays_news_api_error(self):
        self.handler.model = MagicMock()
        self.handler.model.generate_content.side_effect = Exception("Gemini API error")

        result = self.handler.get_todays_news()
        assert result is None
