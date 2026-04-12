"""Shared pytest fixtures for the test suite"""

import os
import sys
import tempfile
import pytest

# Ensure src is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def tmp_db_path():
    """Provide a temporary database path for each test"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def sqlite_db(tmp_db_path):
    """Provide a fresh SQLite database instance"""
    from video_summary_bot.database.operations import Database
    return Database(tmp_db_path)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing"""
    monkeypatch.setenv("YOUTUBE_API_KEY", "test_youtube_key")
    monkeypatch.setenv("GEMINI_API_KEY", "test_gemini_key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_bot_token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_id")
    monkeypatch.setenv("BOT_PASSWORD", "test_password")
    monkeypatch.setenv("USE_SUPABASE", "false")


@pytest.fixture
def sample_video_info():
    """Sample video info dict for testing"""
    return {
        "id": "dQw4w9WgXcQ",
        "title": "Test Video Title",
        "description": "Test description",
        "published_at": "2025-01-01T12:00:00Z",
        "channel_title": "Test Channel",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "transcript": "This is a test transcript text for the video.",
    }


@pytest.fixture
def sample_channel():
    """Sample channel dict for testing"""
    return {
        "channel_handle": "@TestChannel",
        "channel_name": "Test Channel",
        "youtube_channel_id": "UCtestchannelid123",
        "language": "es",
        "check_start_hour": 10,
        "check_start_minute": 0,
        "check_end_hour": 14,
        "check_interval_minutes": 5,
        "active": 1,
    }


@pytest.fixture
def mock_youtube_response():
    """Sample YouTube API response structure"""
    return {
        "items": [
            {
                "id": {"videoId": "dQw4w9WgXcQ"},
                "snippet": {
                    "title": "Test Video",
                    "description": "Test description",
                    "publishedAt": "2025-01-01T12:00:00Z",
                    "channelTitle": "Test Channel",
                    "thumbnails": {
                        "medium": {"url": "https://example.com/thumb.jpg"}
                    },
                },
            }
        ]
    }


@pytest.fixture
def mock_telegram_response():
    """Sample Telegram API response structure"""
    return {
        "ok": True,
        "result": {
            "message_id": 123,
            "chat": {"id": "test_chat_id"},
            "date": 1700000000,
            "text": "Test message",
        },
    }


@pytest.fixture
def mock_telegram_updates():
    """Sample Telegram getUpdates response"""
    return {
        "ok": True,
        "result": [
            {
                "update_id": 100,
                "message": {
                    "message_id": 50,
                    "chat": {
                        "id": "123456789",
                        "first_name": "TestUser",
                        "username": "testuser",
                    },
                    "date": 1700000000,
                    "text": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                },
            }
        ],
    }
