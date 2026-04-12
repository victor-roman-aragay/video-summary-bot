"""Tests for YouTube API handler (with mocking)"""

from unittest.mock import patch, MagicMock
from datetime import datetime
from video_summary_bot.handlers.youtube import YouTubeHandler


class TestYouTubeHandler:
    """Tests for the YouTubeHandler class with mocked API calls"""

    def setup_method(self):
        self.handler = YouTubeHandler("test_api_key")

    # --- get_todays_video ---

    @patch.object(YouTubeHandler, "_get_channel_id_from_handle")
    def test_get_todays_video_with_handle(self, mock_get_id):
        """When given a @handle, should resolve to channel ID first"""
        mock_get_id.return_value = "UCresolved123"

        mock_search = MagicMock()
        mock_search.execute.return_value = {
            "items": [
                {
                    "id": {"videoId": "vid123"},
                    "snippet": {
                        "title": "Today's Video",
                        "description": "Description",
                        "publishedAt": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "channelTitle": "Test Channel",
                        "thumbnails": {"medium": {"url": "https://example.com/thumb.jpg"}},
                    },
                }
            ]
        }
        self.handler.youtube = MagicMock()
        self.handler.youtube.search.return_value.list.return_value = mock_search

        result = self.handler.get_todays_video("@TestChannel")
        assert result is not None
        assert result["id"] == "vid123"
        mock_get_id.assert_called_once_with("@TestChannel")

    @patch.object(YouTubeHandler, "_get_channel_id_from_handle")
    def test_get_todays_video_handle_resolution_fails(self, mock_get_id):
        mock_get_id.return_value = None
        result = self.handler.get_todays_video("@NonexistentChannel")
        assert result is None

    def test_get_todays_video_no_videos(self):
        mock_search = MagicMock()
        mock_search.execute.return_value = {"items": []}
        self.handler.youtube = MagicMock()
        self.handler.youtube.search.return_value.list.return_value = mock_search

        result = self.handler.get_todays_video("UCtest123")
        assert result is None

    def test_get_todays_video_old_video(self):
        mock_search = MagicMock()
        mock_search.execute.return_value = {
            "items": [
                {
                    "id": {"videoId": "oldVid"},
                    "snippet": {
                        "title": "Old Video",
                        "description": "Description",
                        "publishedAt": "2024-01-01T12:00:00Z",
                        "channelTitle": "Test Channel",
                        "thumbnails": {"medium": {"url": "https://example.com/thumb.jpg"}},
                    },
                }
            ]
        }
        self.handler.youtube = MagicMock()
        self.handler.youtube.search.return_value.list.return_value = mock_search

        result = self.handler.get_todays_video("UCtest123")
        assert result is None

    def test_get_todays_video_api_error(self):
        mock_search = MagicMock()
        mock_search.execute.side_effect = Exception("API error")
        self.handler.youtube = MagicMock()
        self.handler.youtube.search.return_value.list.return_value = mock_search

        result = self.handler.get_todays_video("UCtest123")
        assert result is None

    # --- get_video_info ---

    def test_get_video_info_success(self):
        mock_list = MagicMock()
        mock_list.execute.return_value = {
            "items": [
                {
                    "snippet": {
                        "title": "Test Video",
                        "description": "Test description",
                        "publishedAt": "2025-01-01T12:00:00Z",
                        "channelTitle": "Test Channel",
                        "thumbnails": {"medium": {"url": "https://example.com/thumb.jpg"}},
                    }
                }
            ]
        }
        self.handler.youtube = MagicMock()
        self.handler.youtube.videos.return_value.list.return_value = mock_list

        result = self.handler.get_video_info("vid123")
        assert result is not None
        assert result["id"] == "vid123"
        assert result["title"] == "Test Video"

    def test_get_video_info_not_found(self):
        mock_list = MagicMock()
        mock_list.execute.return_value = {"items": []}
        self.handler.youtube = MagicMock()
        self.handler.youtube.videos.return_value.list.return_value = mock_list

        result = self.handler.get_video_info("nonexistent")
        assert result is None

    def test_get_video_info_api_error(self):
        mock_list = MagicMock()
        mock_list.execute.side_effect = Exception("API error")
        self.handler.youtube = MagicMock()
        self.handler.youtube.videos.return_value.list.return_value = mock_list

        result = self.handler.get_video_info("vid123")
        assert result is None

    # --- _get_channel_id_from_handle ---

    def test_get_channel_id_by_username(self):
        mock_channels = MagicMock()
        mock_channels.execute.return_value = {
            "items": [{"id": "UCresolved123"}]
        }
        self.handler.youtube = MagicMock()
        self.handler.youtube.channels.return_value.list.return_value = mock_channels

        result = self.handler._get_channel_id_from_handle("@TestChannel")
        assert result == "UCresolved123"

    def test_get_channel_id_by_search_fallback(self):
        mock_channels = MagicMock()
        mock_channels.execute.return_value = {"items": []}
        mock_search = MagicMock()
        mock_search.execute.return_value = {
            "items": [{"snippet": {"channelId": "UCsearch123"}}]
        }
        self.handler.youtube = MagicMock()
        self.handler.youtube.channels.return_value.list.return_value = mock_channels
        self.handler.youtube.search.return_value.list.return_value = mock_search

        result = self.handler._get_channel_id_from_handle("@TestChannel")
        assert result == "UCsearch123"

    def test_get_channel_id_not_found(self):
        mock_channels = MagicMock()
        mock_channels.execute.return_value = {"items": []}
        mock_search = MagicMock()
        mock_search.execute.return_value = {"items": []}
        self.handler.youtube = MagicMock()
        self.handler.youtube.channels.return_value.list.return_value = mock_channels
        self.handler.youtube.search.return_value.list.return_value = mock_search

        result = self.handler._get_channel_id_from_handle("@Nonexistent")
        assert result is None

    # --- get_transcript ---

    @patch("video_summary_bot.handlers.youtube.YouTubeTranscriptApi")
    def test_get_transcript_spanish_success(self, mock_transcript_api):
        mock_snippet = MagicMock()
        mock_snippet.text = "Hola mundo"
        mock_api = MagicMock()
        mock_api.fetch.return_value = [mock_snippet]
        mock_transcript_api.return_value = mock_api

        result = self.handler.get_transcript("vid123")
        assert result == "Hola mundo"

    @patch("video_summary_bot.handlers.youtube.YouTubeTranscriptApi")
    def test_get_transcript_falls_back_to_english(self, mock_transcript_api):
        mock_api = MagicMock()
        mock_api.fetch.side_effect = [
            Exception("No Spanish transcript"),  # es fails
            [MagicMock(text="English transcript")],  # en succeeds
        ]
        mock_transcript_api.return_value = mock_api

        result = self.handler.get_transcript("vid123")
        assert result == "English transcript"

    @patch("video_summary_bot.handlers.youtube.YouTubeTranscriptApi")
    def test_get_transcript_both_languages_fail(self, mock_transcript_api):
        mock_api = MagicMock()
        mock_api.fetch.side_effect = Exception("No transcript at all")
        mock_transcript_api.return_value = mock_api

        result = self.handler.get_transcript("vid123")
        assert result is None

    # --- get_video_info_with_transcript ---

    @patch.object(YouTubeHandler, "get_todays_video")
    @patch.object(YouTubeHandler, "get_transcript")
    def test_get_video_info_with_transcript_success(self, mock_transcript, mock_video):
        mock_video.return_value = {
            "id": "vid123",
            "title": "Test Video",
            "channel_title": "Test Channel",
        }
        mock_transcript.return_value = "Test transcript"

        result = self.handler.get_video_info_with_transcript("UCtest123")
        assert result is not None
        assert result["transcript"] == "Test transcript"

    @patch.object(YouTubeHandler, "get_todays_video")
    def test_get_video_info_with_transcript_no_video(self, mock_video):
        mock_video.return_value = None
        result = self.handler.get_video_info_with_transcript("UCtest123")
        assert result is None

    @patch.object(YouTubeHandler, "get_todays_video")
    @patch.object(YouTubeHandler, "get_transcript")
    def test_get_video_info_with_transcript_no_transcript_returns_video(self, mock_transcript, mock_video):
        """Should return video info even without transcript"""
        mock_video.return_value = {
            "id": "vid123",
            "title": "Test Video",
            "channel_title": "Test Channel",
        }
        mock_transcript.return_value = None

        result = self.handler.get_video_info_with_transcript("UCtest123")
        assert result is not None
        assert result["id"] == "vid123"
        assert "transcript" not in result
