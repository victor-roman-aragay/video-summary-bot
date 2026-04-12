"""Tests for shorts detection in handlers"""

from unittest.mock import patch, MagicMock
import pytest
from video_summary_bot.handlers.youtube_rss import (
    YouTubeRSSHandler,
    _looks_like_shorts,
)
from video_summary_bot.handlers.youtube import YouTubeHandler, _parse_iso_duration


class TestParseIsoDuration:
    """Tests for the ISO 8601 duration parser"""

    def test_seconds_only(self):
        assert _parse_iso_duration("PT30S") == 30

    def test_minutes_and_seconds(self):
        assert _parse_iso_duration("PT5M30S") == 330

    def test_hours_minutes_seconds(self):
        assert _parse_iso_duration("PT1H30M15S") == 5415

    def test_minutes_only(self):
        assert _parse_iso_duration("PT10M") == 600

    def test_one_minute(self):
        assert _parse_iso_duration("PT1M") == 60

    def test_zero_duration(self):
        assert _parse_iso_duration("PT0S") == 0

    def test_invalid_format(self):
        assert _parse_iso_duration("invalid") == 0

    def test_empty_string(self):
        assert _parse_iso_duration("") == 0


class TestLooksLikeShorts:
    """Tests for the _looks_like_shorts heuristic function"""

    def test_title_with_hashtag_shorts(self):
        assert _looks_like_shorts("My video #shorts") is True

    def test_title_with_hashtag_short(self):
        assert _looks_like_shorts("Check this out #short") is True

    def test_title_case_insensitive(self):
        assert _looks_like_shorts("My #SHORTS video") is True

    def test_description_with_hashtag(self):
        assert _looks_like_shorts("Normal title", "Watch this #shorts") is True

    def test_combined_title_and_description(self):
        assert _looks_like_shorts("Cool", "my amazing #shorts content") is True

    def test_regular_video_title(self):
        assert _looks_like_shorts("Complete Guide to Python Programming") is False

    def test_title_contains_shorts_as_word(self):
        """'shorts' as a regular word without # should not trigger"""
        assert _looks_like_shorts("Best shorts of the year") is False

    def test_empty_inputs(self):
        assert _looks_like_shorts("", "") is False

    def test_hashtag_in_middle_of_word(self):
        """#shorts inside another word should still match"""
        assert _looks_like_shorts("Check #shorts now") is True


class TestYouTubeHandlerIsShorts:
    """Tests for YouTubeHandler.is_shorts method"""

    def setup_method(self):
        self.handler = YouTubeHandler("test_api_key")

    def test_is_shorts_video_under_60_seconds(self):
        """Video with duration <= 60s should be detected as Short"""
        mock_videos = MagicMock()
        mock_videos.execute.return_value = {
            "items": [
                {
                    "contentDetails": {
                        "duration": "PT0M45S",  # 45 seconds
                    }
                }
            ]
        }
        self.handler.youtube = MagicMock()
        self.handler.youtube.videos.return_value.list.return_value = mock_videos

        assert self.handler.is_shorts("shortVid123") is True

    def test_is_shorts_video_exactly_60_seconds(self):
        """Video with duration == 60s should be detected as Short"""
        mock_videos = MagicMock()
        mock_videos.execute.return_value = {
            "items": [
                {
                    "contentDetails": {
                        "duration": "PT1M0S",  # 60 seconds
                    }
                }
            ]
        }
        self.handler.youtube = MagicMock()
        self.handler.youtube.videos.return_value.list.return_value = mock_videos

        assert self.handler.is_shorts("shortVid123") is True

    def test_is_shorts_regular_video_over_60_seconds(self):
        """Video with duration > 60s should NOT be detected as Short"""
        mock_videos = MagicMock()
        mock_videos.execute.return_value = {
            "items": [
                {
                    "contentDetails": {
                        "duration": "PT10M30S",  # 10 minutes 30 seconds
                    }
                }
            ]
        }
        self.handler.youtube = MagicMock()
        self.handler.youtube.videos.return_value.list.return_value = mock_videos

        assert self.handler.is_shorts("regularVid123") is False

    def test_is_shorts_no_video_found(self):
        """Should return False if video not found"""
        mock_videos = MagicMock()
        mock_videos.execute.return_value = {"items": []}
        self.handler.youtube = MagicMock()
        self.handler.youtube.videos.return_value.list.return_value = mock_videos

        assert self.handler.is_shorts("nonexistent") is False

    def test_is_shorts_api_error(self):
        """Should return False on API error"""
        mock_videos = MagicMock()
        mock_videos.execute.side_effect = Exception("API error")
        self.handler.youtube = MagicMock()
        self.handler.youtube.videos.return_value.list.return_value = mock_videos

        assert self.handler.is_shorts("vid123") is False

    def test_is_shorts_custom_threshold(self):
        """Should respect custom max_duration_seconds"""
        # Test with a 2-minute video
        mock_videos = MagicMock()
        mock_videos.execute.return_value = {
            "items": [
                {
                    "contentDetails": {
                        "duration": "PT2M0S",  # 2 minutes = 120 seconds
                    }
                }
            ]
        }
        self.handler.youtube = MagicMock()
        self.handler.youtube.videos.return_value.list.return_value = mock_videos

        # With default 60s threshold, 2 min video is NOT a Short
        assert self.handler.is_shorts("vid123") is False
        # With 120s threshold, it's exactly at the boundary (<=), so IS a Short
        assert self.handler.is_shorts("vid123", max_duration_seconds=120) is True
        # With 180s threshold, 2 min is well within, so IS a Short
        assert self.handler.is_shorts("vid123", max_duration_seconds=180) is True
        # With 30s threshold, 2 min is above, so NOT a Short
        assert self.handler.is_shorts("vid123", max_duration_seconds=30) is False


class TestYouTubeRSSHandlerIsShortsHeuristic:
    """Tests for YouTubeRSSHandler.is_shorts_heuristic method"""

    def setup_method(self):
        self.handler = YouTubeRSSHandler()

    def test_detects_short_via_hashtag_in_title(self):
        video_info = {
            "title": "Quick tip #shorts",
            "description": "A quick programming tip",
        }
        assert self.handler.is_shorts_heuristic(video_info) is True

    def test_detects_short_via_hashtag_in_description(self):
        video_info = {
            "title": "Quick tip",
            "description": "Here's a quick tip #shorts",
        }
        assert self.handler.is_shorts_heuristic(video_info) is True

    def test_detects_short_via_short_transcript(self):
        """Transcript < 150 chars suggests a Short"""
        video_info = {
            "title": "My video",
            "description": "A video",
            "transcript": "Hi everyone, welcome to my channel. Today we look at this cool thing. Thanks for watching!",
        }
        # Transcript is 103 chars — below 150 threshold
        assert self.handler.is_shorts_heuristic(video_info) is True

    def test_regular_video_with_long_transcript(self):
        """Regular video with substantial transcript"""
        transcript = "This is a comprehensive tutorial about Python programming. " * 10  # ~550 chars
        video_info = {
            "title": "Complete Python Tutorial",
            "description": "Learn Python from scratch",
            "transcript": transcript,
        }
        assert self.handler.is_shorts_heuristic(video_info) is False

    def test_video_without_transcript_not_detected(self):
        """Video with no transcript and no #shorts should not be detected as Short"""
        video_info = {
            "title": "Normal Video",
            "description": "A normal description",
        }
        assert self.handler.is_shorts_heuristic(video_info) is False

    def test_empty_video_info(self):
        assert self.handler.is_shorts_heuristic({}) is False


class TestRSSHandlerSkipsShorts:
    """Tests that get_video_info_with_transcript returns None for Shorts"""

    @patch.object(YouTubeRSSHandler, "get_todays_video_from_rss")
    @patch.object(YouTubeRSSHandler, "is_shorts_heuristic")
    def test_returns_none_for_shorts_via_hashtag(self, mock_is_shorts, mock_rss):
        mock_rss.return_value = {
            "id": "shortVid",
            "title": "My #shorts video",
            "description": "A short video",
        }
        mock_is_shorts.return_value = True

        handler = YouTubeRSSHandler()
        result = handler.get_video_info_with_transcript("UCtest123")

        assert result is None
        mock_is_shorts.assert_called_once()

    @patch.object(YouTubeRSSHandler, "get_todays_video_from_rss")
    @patch.object(YouTubeRSSHandler, "is_shorts_heuristic")
    def test_returns_none_for_shorts_via_transcript_length(self, mock_is_shorts, mock_rss):
        mock_rss.return_value = {
            "id": "shortVid",
            "title": "Quick clip",
            "description": "A very short clip",
            "transcript": "Hi, bye!",  # Very short
        }
        mock_is_shorts.return_value = True

        handler = YouTubeRSSHandler()
        result = handler.get_video_info_with_transcript("UCtest123")

        assert result is None

    @patch.object(YouTubeRSSHandler, "get_todays_video_from_rss")
    @patch.object(YouTubeRSSHandler, "is_shorts_heuristic")
    @patch.object(YouTubeRSSHandler, "get_transcript")
    def test_regular_video_processed_normally(self, mock_transcript, mock_is_shorts, mock_rss):
        mock_rss.return_value = {
            "id": "regularVid",
            "title": "Full Tutorial",
            "description": "A comprehensive guide",
        }
        mock_is_shorts.return_value = False
        mock_transcript.return_value = "This is a long and detailed transcript."

        handler = YouTubeRSSHandler()
        result = handler.get_video_info_with_transcript("UCtest123")

        assert result is not None
        assert result["transcript"] == "This is a long and detailed transcript."
        assert result["video_id"] == "regularVid"

    @patch.object(YouTubeRSSHandler, "get_todays_video_from_rss")
    def test_returns_none_when_no_video(self, mock_rss):
        mock_rss.return_value = None
        handler = YouTubeRSSHandler()
        result = handler.get_video_info_with_transcript("UCtest123")
        assert result is None
