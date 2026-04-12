# Video Summary Bot - Project Context

## Overview

Automated YouTube video summarizer bot for Telegram that monitors YouTube channels, generates AI-powered summaries of video content, and delivers them to Telegram users.

**Tech Stack:**
- **Language:** Python 3.9+
- **Package Manager:** uv (with pyproject.toml)
- **Database:** SQLite (local) or PostgreSQL (Supabase for production)
- **ORM:** SQLAlchemy
- **AI Model:** Google Gemini (`gemini-3.1-flash-lite-preview`)
- **Telegram Bot:** python-telegram-bot (via requests)
- **YouTube Integration:** RSS feeds (quota-free) + YouTube Data API v3
- **Scheduler:** `schedule` library

## Project Structure

```
video-summary-bot/
├── src/video_summary_bot/
│   ├── __main__.py              # Entry point with CLI commands
│   ├── scheduler.py              # Job scheduler for automated checks
│   ├── bots/
│   │   ├── combined.py          # Runs both scheduler + listen bot in parallel threads
│   │   ├── listen.py            # Interactive Telegram bot for on-demand URL processing
│   │   └── video_summary.py     # Scheduled channel monitor bot
│   ├── handlers/
│   │   ├── youtube.py           # YouTube Data API handler
│   │   ├── youtube_rss.py       # RSS feed handler (quota-free video discovery)
│   │   ├── gemini.py            # Gemini AI handler (summarization)
│   │   └── telegram.py          # Telegram bot handler
│   ├── database/
│   │   └── operations.py        # SQLite/Supabase operations (Database class)
│   ├── config/
│   │   ├── settings.py          # API keys & settings (loads from .env)
│   │   └── users.py             # Legacy user preferences (use DB instead)
│   └── utils/
│       ├── url_parser.py        # URL extraction utilities
│       └── logger.py            # Logging setup
├── data/
│   └── video_summary.db         # SQLite database
├── scripts/
│   ├── migrate_database.py      # Database migration
│   ├── migrate_users_to_db.py   # Migrate users from config to DB
│   ├── migrate_sqlite_to_supabase.py  # Migrate SQLite to Supabase
│   └── test_supabase_connection.py
├── tests/
│   ├── test_bots/
│   ├── test_handlers/
│   └── test_utils/
├── docs/
│   └── USER_MANAGEMENT.md       # User management guide
├── notebooks/
│   └── playground.ipynb         # Development playground
├── run.sh                       # Helper script to run the bot
├── pyproject.toml               # Project dependencies
└── .env.example                 # Environment variable template
```

## Key Commands

### Running the Bot

```bash
# Recommended: Combined mode (scheduler + listen bot)
./run.sh combined
# or
uv run python -m video_summary_bot combined

# Listen mode only (interactive URL processing)
./run.sh listen

# Scheduler mode only (automated channel monitoring)
./run.sh schedule

# One-time video summary processing
./run.sh video-summary
```

### Development

```bash
# Install dependencies
uv sync
source .venv/bin/activate

# Run tests
pytest tests/

# Run with uv directly
uv run python -m video_summary_bot combined
```

### Database Management

```bash
# Open SQLite database
sqlite3 data/video_summary.db

# Run migration scripts
uv run python scripts/migrate_users_to_db.py
uv run python scripts/migrate_sqlite_to_supabase.py
```

## Environment Variables

Required variables in `.env`:

```env
# API Keys
YOUTUBE_API_KEY=your_youtube_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Database (choose one)
USE_SUPABASE=true
DATABASE_URL=postgresql://...  # Supabase connection string

# OR use SQLite
USE_SUPABASE=false
SQLITE_DB_PATH=data/video_summary.db

# Other settings
BOT_NAME=YouTube-Financial-Bot
LOG_LEVEL=INFO
TIMEZONE=Europe/Madrid
DEBUG_MODE=true
DRY_RUN=false
```

## Database Schema

### Tables

- **users** - Telegram users (user_id, username, active, created_at, updated_at)
- **channels** - YouTube channels (channel_handle, channel_name, youtube_channel_id, language, check schedule settings, active)
- **user_channels** - User-channel subscriptions (user_id, channel_id, subscribed_at)
- **summaries** - Processed video summaries (channel_handle, video_id, video_title, video_url, summary_text, video_date, processed_at, success)

### Key Database Operations

The `Database` class in `src/video_summary_bot/database/operations.py` provides:
- User CRUD operations (`add_user`, `get_user`, `get_all_users`, `deactivate_user`)
- Channel management (`add_channel`, `get_channel`, `get_all_channels`)
- Subscription management (`subscribe_user_to_channel`, `unsubscribe_user_from_channel`, `get_user_channels`, `get_channel_subscribers`)
- Summary logging (`add_summary`, `has_video_been_processed`, `get_summaries`, `get_summary_by_video_id`, `has_video_id_been_processed`)

## Architecture

### Bot Modes

1. **Combined Mode** (Recommended): Runs both scheduler and listen bot in parallel threads
   - Scheduler thread: Checks configured channels every 10 minutes
   - Listen thread: Waits for YouTube URLs from Telegram users

2. **Listen Mode**: Interactive mode that listens for YouTube URLs from configured users
   - Checks if video has been processed before (uses cached summary)
   - If new, generates summary via Gemini AI and saves to database

3. **Schedule Mode**: Runs scheduled checks for new videos automatically
   - Checks configured channels every 10 minutes
   - Only processes videos published today

4. **Video-Summary Mode**: One-time execution to process today's videos

### Data Flow

1. **RSS Discovery** (quota-free): `YouTubeRSSHandler` fetches RSS feeds to discover new videos
2. **Transcript Fetching**: `YouTubeTranscriptApi` extracts video transcripts
3. **AI Summarization**: `GeminiHandler` generates summary using `gemini-3.1-flash-lite-preview`
4. **Database Storage**: Summary is stored in SQLite/PostgreSQL with video metadata
5. **Telegram Delivery**: Summary is sent to subscribed users via Telegram bot

### Caching Strategy

- Video summaries are cached in the database
- If a video has been processed before, the cached summary is returned
- No API calls are made for already-processed videos

### User Authorization

- Only configured users can interact with the bot
- Users are stored in the database (not config files)
- Use `db.is_user_authorized(user_id)` to check authorization

## Key Configuration

### Monitored YouTube Channels

Defined in `src/video_summary_bot/config/settings.py`:
- `@JoseLuisCavattv`
- `@nacho_ic`
- `@juanrallo`
- `@bravosresearchcrypto`
- `@bravosresearch`

### Channel Check Schedule

Each channel has configurable check windows:
- `check_start_hour` / `check_start_minute` - Start of check window
- `check_end_hour` - End of check window
- `check_interval_minutes` - Interval between checks (default: 5 min)

## Important Notes

1. **RSS-first approach**: The bot uses RSS feeds for video discovery to minimize YouTube API quota usage
2. **Users are database-managed**: Don't use `config/users.py` for production - use the database
3. **Migration scripts**: Available in `scripts/` for moving from config-based to DB-based user management
4. **Supabase support**: Can use PostgreSQL via Supabase for production (set `USE_SUPABASE=true`)
5. **Spanish-language content**: The Gemini prompts are configured for Spanish financial/economic content
6. **Timezone**: Default is `Europe/Madrid`

## Dependencies

From `pyproject.toml`:
- `schedule==1.2.2` - Job scheduling
- `requests==2.32.5` - HTTP requests
- `python-dotenv==1.1.1` - Environment variable loading
- `youtube-transcript-api==1.2.2` - Transcript extraction
- `google-api-python-client==2.182.0` - YouTube API
- `google-generativeai==0.8.5` - Gemini AI
- `feedparser==6.0.12` - RSS feed parsing
- `pytz>=2024.0` - Timezone handling
- `psycopg2-binary>=2.9.9` - PostgreSQL adapter
- `sqlalchemy>=2.0.0` - ORM

## Testing

Test structure:
```
tests/
├── test_bots/
├── test_handlers/
└── test_utils/
```

Run tests with: `pytest tests/`

## Common Tasks

### Adding a New User

```python
from video_summary_bot.database import Database
db = Database()
db.add_user(user_id="123456789", username="John Doe")
db.subscribe_user_to_channel("123456789", channel_handle="@channelhandle")
```

### Adding a New Channel

```python
db.add_channel(
    channel_handle="@NewChannel",
    channel_name="New Channel",
    youtube_channel_id="UCxxxxx",
    language="es"
)
```

### Getting Telegram Chat ID

1. Start a chat with the bot
2. Send any message
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Look for `"chat":{"id":123456789}`

## Git Workflow

- Main branch: `main`
- Recent commits follow conventional style
- Always review `git status` and `git diff` before committing
