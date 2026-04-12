"""PostgreSQL database operations using SQLAlchemy"""

import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from sqlalchemy import create_engine, text, pool
from sqlalchemy.orm import sessionmaker, scoped_session

logger = logging.getLogger(__name__)


class PostgresDatabase:
    """PostgreSQL database handler using SQLAlchemy with pg8000 (pure Python driver)"""

    def __init__(self, database_url: str = None):
        """Initialize PostgreSQL connection"""
        self.database_url = database_url or os.getenv('DATABASE_URL')

        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")

        # Ensure we use pg8000 driver (pure Python, no native libpq needed)
        if self.database_url.startswith('postgresql://'):
            self.database_url = self.database_url.replace('postgresql://', 'postgresql+pg8000://', 1)

        # Create engine with connection pooling
        self.engine = create_engine(
            self.database_url,
            poolclass=pool.QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections before using
            echo=False  # Set to True for SQL debugging
        )

        # Create session factory
        self.Session = scoped_session(sessionmaker(bind=self.engine))

        # Initialize schema
        self.init_database()

    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def init_database(self):
        """Initialize database schema"""
        with self.engine.connect() as conn:
            # Users table
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))

            # Channels table
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS channels (
                    channel_id SERIAL PRIMARY KEY,
                    channel_handle TEXT UNIQUE NOT NULL,
                    channel_name TEXT,
                    youtube_channel_id TEXT,
                    language TEXT DEFAULT 'es',
                    check_start_hour INTEGER DEFAULT 10,
                    check_start_minute INTEGER DEFAULT 0,
                    check_end_hour INTEGER DEFAULT 14,
                    check_interval_minutes INTEGER DEFAULT 5,
                    active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''))

            # User-Channel subscriptions
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS user_channels (
                    user_id TEXT,
                    channel_id INTEGER,
                    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, channel_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
                )
            '''))

            # Summaries log
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS summaries (
                    summary_id SERIAL PRIMARY KEY,
                    channel_handle TEXT NOT NULL,
                    video_id TEXT,
                    video_title TEXT,
                    video_url TEXT,
                    summary_text TEXT,
                    video_date DATE,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success INTEGER DEFAULT 1
                )
            '''))

            # Create indexes
            conn.execute(text('CREATE INDEX IF NOT EXISTS idx_summaries_date ON summaries(video_date)'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS idx_summaries_channel ON summaries(channel_handle)'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS idx_summaries_video_id ON summaries(video_id)'))

            conn.commit()
            logger.info("PostgreSQL database initialized successfully")

    # User operations
    def add_user(self, user_id: str, username: str = None, active: bool = True):
        """Add or update a user"""
        with self.get_session() as session:
            session.execute(text('''
                INSERT INTO users (user_id, username, active)
                VALUES (:user_id, :username, :active)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    active = EXCLUDED.active,
                    updated_at = CURRENT_TIMESTAMP
            '''), {'user_id': user_id, 'username': username, 'active': int(active)})
            logger.info(f"User {user_id} added/updated")

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        with self.get_session() as session:
            result = session.execute(
                text('SELECT * FROM users WHERE user_id = :user_id'),
                {'user_id': user_id}
            ).fetchone()
            return dict(result._mapping) if result else None

    def get_all_users(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all users"""
        with self.get_session() as session:
            if active_only:
                result = session.execute(text('SELECT * FROM users WHERE active = 1'))
            else:
                result = session.execute(text('SELECT * FROM users'))
            return [dict(row._mapping) for row in result]

    def is_user_authorized(self, user_id: str) -> bool:
        """Check if user is authorized (exists and is active)"""
        with self.get_session() as session:
            result = session.execute(
                text('SELECT COUNT(*) as count FROM users WHERE user_id = :user_id AND active = 1'),
                {'user_id': user_id}
            ).fetchone()
            return result[0] > 0

    def deactivate_user(self, user_id: str):
        """Deactivate a user (soft delete)"""
        with self.get_session() as session:
            session.execute(
                text('UPDATE users SET active = 0, updated_at = CURRENT_TIMESTAMP WHERE user_id = :user_id'),
                {'user_id': user_id}
            )
            logger.info(f"User {user_id} deactivated")

    # Channel operations
    def add_channel(self, channel_handle: str, channel_name: str = None,
                   youtube_channel_id: str = None, language: str = 'es',
                   check_start_hour: int = 10, check_start_minute: int = 0,
                   check_end_hour: int = 14, check_interval_minutes: int = 5):
        """Add a new channel"""
        with self.get_session() as session:
            session.execute(text('''
                INSERT INTO channels
                (channel_handle, channel_name, youtube_channel_id, language, check_start_hour,
                 check_start_minute, check_end_hour, check_interval_minutes)
                VALUES (:handle, :name, :yt_id, :lang, :start_h, :start_m, :end_h, :interval)
                ON CONFLICT(channel_handle) DO NOTHING
            '''), {
                'handle': channel_handle, 'name': channel_name, 'yt_id': youtube_channel_id,
                'lang': language, 'start_h': check_start_hour, 'start_m': check_start_minute,
                'end_h': check_end_hour, 'interval': check_interval_minutes
            })
            logger.info(f"Channel {channel_handle} added")

    def get_channel(self, channel_handle: str) -> Optional[Dict[str, Any]]:
        """Get channel by handle"""
        with self.get_session() as session:
            result = session.execute(
                text('SELECT * FROM channels WHERE channel_handle = :handle'),
                {'handle': channel_handle}
            ).fetchone()
            return dict(result._mapping) if result else None

    def get_all_channels(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all channels"""
        with self.get_session() as session:
            if active_only:
                result = session.execute(text('SELECT * FROM channels WHERE active = 1'))
            else:
                result = session.execute(text('SELECT * FROM channels'))
            return [dict(row._mapping) for row in result]

    # User-Channel subscriptions
    def subscribe_user_to_channel(self, user_id: str, channel_id: int):
        """Subscribe a user to a channel"""
        with self.get_session() as session:
            session.execute(text('''
                INSERT INTO user_channels (user_id, channel_id)
                VALUES (:user_id, :channel_id)
                ON CONFLICT DO NOTHING
            '''), {'user_id': user_id, 'channel_id': channel_id})
            logger.info(f"User {user_id} subscribed to channel {channel_id}")

    def get_channel_subscribers(self, channel_handle: str) -> List[str]:
        """Get list of user IDs subscribed to a channel"""
        with self.get_session() as session:
            result = session.execute(text('''
                SELECT DISTINCT uc.user_id
                FROM user_channels uc
                JOIN channels c ON uc.channel_id = c.channel_id
                WHERE c.channel_handle = :handle AND c.active = 1
            '''), {'handle': channel_handle})
            return [row[0] for row in result]

    # Summary operations
    def add_summary(self, channel_handle: str, video_id: str, video_title: str,
                   video_url: str, summary_text: str, video_date: str = None,
                   success: bool = True):
        """Log a video summary"""
        if video_date is None:
            video_date = datetime.now().strftime('%Y-%m-%d')

        with self.get_session() as session:
            session.execute(text('''
                INSERT INTO summaries
                (channel_handle, video_id, video_title, video_url, summary_text, video_date, success)
                VALUES (:handle, :vid_id, :title, :url, :summary, :date, :success)
            '''), {
                'handle': channel_handle, 'vid_id': video_id, 'title': video_title,
                'url': video_url, 'summary': summary_text, 'date': video_date, 'success': int(success)
            })
            logger.info(f"Summary logged for {channel_handle}: {video_title}")

    def get_summary_by_video_id(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get summary for a specific video ID if it exists"""
        with self.get_session() as session:
            result = session.execute(text('''
                SELECT * FROM summaries
                WHERE video_id = :video_id AND success = 1
                ORDER BY processed_at DESC
                LIMIT 1
            '''), {'video_id': video_id}).fetchone()
            return dict(result._mapping) if result else None

    def has_video_id_been_processed(self, video_id: str) -> bool:
        """Check if a specific video ID has been processed"""
        with self.get_session() as session:
            result = session.execute(text('''
                SELECT COUNT(*) as count FROM summaries
                WHERE video_id = :video_id AND success = 1
            '''), {'video_id': video_id}).fetchone()
            return result[0] > 0

    def has_video_been_processed(self, channel_handle: str, date: str = None) -> bool:
        """Check if a video from a channel has been processed today"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        with self.get_session() as session:
            result = session.execute(text('''
                SELECT COUNT(*) as count FROM summaries
                WHERE channel_handle = :handle AND video_date = :date AND success = 1
            '''), {'handle': channel_handle, 'date': date}).fetchone()
            return result[0] > 0

    def close(self):
        """Close database connections"""
        self.Session.remove()
        self.engine.dispose()
