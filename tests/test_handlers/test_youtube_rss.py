"""Tests for YouTube RSS handler"""

from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from video_summary_bot.handlers.youtube_rss import YouTubeRSSHandler


class TestYouTubeRSSHandler:
    """Tests for the YouTubeRSSHandler class"""

    def setup_method(self):
        self.handler = YouTubeRSSHandler()

    def test_init_no_api_key_needed(self):
        """RSS handler should not require any API keys"""
        handler = YouTubeRSSHandler()
        assert handler is not None

    @patch("video_summary_bot.handlers.youtube_rss.feedparser.parse")
    def test_get_todays_video_from_rss_success(self, mock_parse):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        mock_feed = MagicMock()
        mock_feed.entries = [
            MagicMock(
                yt_videoid="vid123",
                title="Test Video",
                summary="Test description",
                published=today,
                author="Test Channel",
                link="https://www.youtube.com/watch?v=vid123",
                media_thumbnail=[{"url": "https://example.com/thumb.jpg"}],
            )
        ]
        mock_parse.return_value = mock_feed

        result = self.handler.get_todays_video_from_rss("UCtestchannelid")

        assert result is not None
        assert result["id"] == "vid123"
        assert result["title"] == "Test Video"
        assert result["url"] == "https://www.youtube.com/watch?v=vid123"

    @patch("video_summary_bot.handlers.youtube_rss.feedparser.parse")
    def test_get_todays_video_no_entries(self, mock_parse):
        mock_feed = MagicMock()
        mock_feed.entries = []
        mock_parse.return_value = mock_feed

        result = self.handler.get_todays_video_from_rss("UCtestchannelid")
        assert result is None

    @patch("video_summary_bot.handlers.youtube_rss.feedparser.parse")
    def test_get_todays_video_old_video(self, mock_parse):
        """Video from yesterday should return None"""
        old_date = "2024-01-01T12:00:00+00:00"
        mock_feed = MagicMock()
        mock_feed.entries = [
            MagicMock(
                yt_videoid="oldVid",
                title="Old Video",
                summary="Old description",
                published=old_date,
                author="Test Channel",
                link="https://www.youtube.com/watch?v=oldVid",
                media_thumbnail=[],
            )
        ]
        mock_parse.return_value = mock_feed

        result = self.handler.get_todays_video_from_rss("UCtestchannelid")
        assert result is None

    @patch("video_summary_bot.handlers.youtube_rss.feedparser.parse")
    def test_get_todays_video_parse_error(self, mock_parse):
        mock_parse.side_effect = Exception("Parse error")
        result = self.handler.get_todays_video_from_rss("UCtestchannelid")
        assert result is None

    @patch("video_summary_bot.handlers.youtube_rss.YouTubeTranscriptApi")
    def test_get_transcript_success(self, mock_transcript_api_class):
        mock_snippet = MagicMock()
        mock_snippet.text = "Hello world"
        mock_transcript = [mock_snippet]
        mock_api = MagicMock()
        mock_api.fetch.return_value = mock_transcript
        mock_transcript_api_class.return_value = mock_api

        result = self.handler.get_transcript("vid123", languages=["es"])
        assert result == "Hello world"

    @patch("video_summary_bot.handlers.youtube_rss.YouTubeTranscriptApi")
    def test_get_transcript_failure(self, mock_transcript_api_class):
        mock_api = MagicMock()
        mock_api.fetch.side_effect = Exception("No transcript")
        mock_transcript_api_class.return_value = mock_api

        result = self.handler.get_transcript("vid123")
        assert result is None

    @patch.object(YouTubeRSSHandler, "get_todays_video_from_rss")
    @patch.object(YouTubeRSSHandler, "get_transcript")
    def test_get_video_info_with_transcript_success(self, mock_transcript, mock_rss):
        mock_rss.return_value = {
            "id": "vid123",
            "title": "Test Video",
            "channel_title": "Test Channel",
            "url": "https://youtube.com/watch?v=vid123",
        }
        mock_transcript.return_value = "Test transcript"

        handler = YouTubeRSSHandler()
        result = handler.get_video_info_with_transcript("UCtest123")

        assert result is not None
        assert result["transcript"] == "Test transcript"
        assert result["video_id"] == "vid123"

    @patch.object(YouTubeRSSHandler, "get_todays_video_from_rss")
    def test_get_video_info_with_transcript_no_video(self, mock_rss):
        mock_rss.return_value = None
        handler = YouTubeRSSHandler()
        result = handler.get_video_info_with_transcript("UCtest123")
        assert result is None

    @patch.object(YouTubeRSSHandler, "get_todays_video_from_rss")
    @patch.object(YouTubeRSSHandler, "get_transcript")
    def test_get_video_info_with_transcript_no_transcript(self, mock_transcript, mock_rss):
        mock_rss.return_value = {
            "id": "vid123",
            "title": "Test Video",
            "channel_title": "Test Channel",
            "url": "https://youtube.com/watch?v=vid123",
        }
        mock_transcript.return_value = None
        handler = YouTubeRSSHandler()
        result = handler.get_video_info_with_transcript("UCtest123")
        assert result is None  # Returns None if no transcript

    @patch.object(YouTubeRSSHandler, "get_todays_video_from_rss")
    @patch.object(YouTubeRSSHandler, "is_shorts_heuristic")
    def test_get_video_info_with_transcript_skips_shorts(self, mock_is_shorts, mock_rss):
        mock_rss.return_value = {
            "id": "shortVid",
            "title": "My #shorts video",
            "channel_title": "Test Channel",
            "url": "https://youtube.com/watch?v=shortVid",
        }
        mock_is_shorts.return_value = True

        handler = YouTubeRSSHandler()
        result = handler.get_video_info_with_transcript("UCtest123")

        assert result is None
        mock_is_shorts.assert_called_once()
