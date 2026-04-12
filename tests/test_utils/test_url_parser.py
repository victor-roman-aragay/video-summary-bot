"""Tests for utils.url_parser"""

from video_summary_bot.utils.url_parser import extract_video_id


class TestExtractVideoId:
    """Tests for the extract_video_id function"""

    # --- Standard youtube.com URLs ---

    def test_standard_watch_url(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_watch_url_without_www(self):
        url = "https://youtube.com/watch?v=abc12345678"
        assert extract_video_id(url) == "abc12345678"

    def test_watch_url_with_extra_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120&list=PLtest"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    # --- Short youtu.be URLs ---

    def test_youtu_be_short_url(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_youtu_be_without_https(self):
        url = "http://youtu.be/abc12345678"
        assert extract_video_id(url) == "abc12345678"

    def test_youtu_be_without_protocol(self):
        url = "youtu.be/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    # --- Mobile URLs ---

    def test_mobile_watch_url(self):
        url = "https://m.youtube.com/watch?v=mobileVid12"
        assert extract_video_id(url) == "mobileVid12"

    # --- Shorts URLs ---

    def test_shorts_url(self):
        url = "https://youtube.com/shorts/shrtVid1234"
        assert extract_video_id(url) == "shrtVid1234"

    def test_shorts_url_with_www(self):
        url = "https://www.youtube.com/shorts/shrtVid1234"
        assert extract_video_id(url) == "shrtVid1234"

    # --- Embed URLs ---

    def test_embed_url(self):
        url = "https://www.youtube.com/embed/embedVid123"
        assert extract_video_id(url) == "embedVid123"

    # --- Edge cases ---

    def test_returns_none_for_invalid_url(self):
        assert extract_video_id("not_a_url") is None

    def test_returns_none_for_non_youtube_url(self):
        assert extract_video_id("https://vimeo.com/123456") is None

    def test_returns_none_for_empty_string(self):
        assert extract_video_id("") is None

    def test_video_id_with_underscores_and_dashes(self):
        url = "https://www.youtube.com/watch?v=aB-cD_12345"
        assert extract_video_id(url) == "aB-cD_12345"

    def test_just_video_id_not_extracted(self):
        """A bare video ID without URL context should not be extracted"""
        assert extract_video_id("dQw4w9WgXcQ") is None
