# Video Summary Bot

Automated YouTube video summarizer bot for Telegram that monitors YouTube channels, generates AI-powered summaries of video content, and delivers them to Telegram users.

## Features

- 🎥 Automated YouTube video monitoring via RSS (quota-free)
- 🤖 AI-powered video summarization using Google Gemini
- 📱 Telegram bot integration for message delivery
- 👂 Interactive mode for on-demand URL processing from multiple users
- 📊 Database tracking and caching of processed videos (SQLite or PostgreSQL via Supabase)
- 🔄 Smart caching - reuses existing summaries instead of regenerating
- 🔒 User authorization with password-based self-registration
- ⏰ Scheduled checks with configurable per-channel time windows
- 🌍 Multi-user support with per-user channel subscriptions

## Project Structure

```
video-summary-bot/
├── src/
│   └── video_summary_bot/
│       ├── bots/                    # Bot implementations
│       │   ├── combined.py         # Runs both scheduler + listen bot in parallel threads
│       │   ├── listen.py           # Interactive URL processor (with password registration)
│       │   └── video_summary.py    # One-time channel processor
│       ├── handlers/                # External API integrations
│       │   ├── youtube.py          # YouTube Data API handler
│       │   ├── youtube_rss.py      # RSS feed handler (quota-free)
│       │   ├── gemini.py           # Gemini AI handler
│       │   └── telegram.py         # Telegram bot handler
│       ├── database/                # Database layer
│       │   ├── factory.py          # DB factory (auto-selects SQLite/PostgreSQL)
│       │   ├── operations.py       # SQLite operations
│       │   └── postgres_operations.py  # PostgreSQL (Supabase) operations
│       ├── config/                  # Configuration
│       │   ├── settings.py         # API keys & settings
│       │   └── users.py            # Legacy user preferences (use DB instead)
│       ├── utils/                   # Utilities
│       │   ├── url_parser.py       # YouTube URL extraction
│       │   └── logger.py           # Logging setup
│       └── scheduler.py             # Job scheduler with per-channel time windows
├── data/                            # Data files
│   └── video_summary.db            # SQLite database (if not using Supabase)
├── scripts/                         # Utility scripts
│   ├── migrate_users_to_db.py      # Migrate users from config to DB
│   ├── migrate_database.py         # General database migration
│   ├── migrate_sqlite_to_supabase.py  # SQLite → Supabase migration
│   └── test_supabase_connection.py
├── tests/                          # Test suite
├── docs/
│   └── USER_MANAGEMENT.md          # User management guide
└── notebooks/
    └── playground.ipynb            # Development playground
```

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd video-summary-bot
   ```

2. **Install dependencies with uv**
   ```bash
   uv sync
   source .venv/bin/activate
   ```

3. **Configure environment variables**

   Copy `.env.example` to `.env` and fill in your API keys:
   ```bash
   cp .env.example .env
   ```

   Required variables:
   - `YOUTUBE_API_KEY` - YouTube Data API v3 key (only needed for initial channel ID lookup)
   - `GEMINI_API_KEY` - Google Gemini API key
   - `TELEGRAM_BOT_TOKEN` - Telegram bot token from @BotFather
   - `BOT_PASSWORD` - Password for user self-registration

   Database (choose one):
   - **SQLite (development):** `USE_SUPABASE=false`
   - **PostgreSQL/Supabase (production):** Set `USE_SUPABASE=true` and `DATABASE_URL`

## Usage

The bot can be run in several modes:

### Quick Start (Using Helper Script)

**Recommended: Run both bots together**

```bash
# Run scheduler + listen bot simultaneously (recommended!)
./run.sh combined   
```

Or run individually:

```bash
# Listen for YouTube URLs only
./run.sh listen          

# Run scheduler (automated mode) only
./run.sh schedule        

# Process today's videos once
./run.sh video-summary   
```

### Alternative: Direct Execution

You can also run using `uv run` directly:

```bash
# Recommended: Combined mode (both scheduler and listen bot)
uv run python -m video_summary_bot combined

# Or run individually:
# 1. Listen Mode (Interactive)
uv run python -m video_summary_bot listen

# 2. Scheduler Mode (Automated)
uv run python -m video_summary_bot schedule

# 3. One-time Video Summary
uv run python -m video_summary_bot video-summary
```

### Mode Descriptions

- **combined** ⭐ - Runs both scheduler and listen bot in parallel threads (RECOMMENDED)
  - Best for production use
  - Handles both automated channel monitoring AND user requests
  - Single process, two threads running simultaneously
  - Press Ctrl+C to stop both bots

- **listen** - Interactive mode that listens for YouTube URLs from authorized users
  - Users send a YouTube URL via Telegram and get a summary back
  - Automatically checks if video has been processed before
  - If video exists in database, retrieves cached summary (no API calls)
  - If video is new, generates summary and saves to database
  - **Self-registration:** Unauthorized users can register by sending the `BOT_PASSWORD`

- **schedule** - Runs scheduled checks for new videos automatically
  - Checks all subscribed channels every 10 minutes within their configured time windows
  - Each channel has its own schedule (start hour, end hour, check interval)
  - Only processes videos published today
  - Sends summaries to all users subscribed to each channel

- **video-summary** - Process today's videos from configured channels once
  - One-time execution, then exits
  - Useful for manual runs or cron jobs

## Configuration

### User Management (Database-based) ✨

**Users are managed in the database, not config files.**

#### Self-Registration

Users can register themselves by sending the `BOT_PASSWORD` to the bot on Telegram. Once the correct password is received, the user is automatically added to the database.

#### Adding Users Manually

```bash
# Open database
sqlite3 data/video_summary.db

# Add a user (use their Telegram chat ID)
INSERT INTO users (user_id, username, active) VALUES ('123456789', 'John Doe', 1);

# Subscribe user to channels
INSERT INTO user_channels (user_id, channel_id) VALUES ('123456789', 1);
```

Or use Python:
```python
from video_summary_bot.database.factory import get_database
db = get_database()
db.add_user(user_id="123456789", username="John Doe")
db.subscribe_user_to_channel("123456789", channel_id=1)
```

📖 **Full guide:** See [docs/USER_MANAGEMENT.md](docs/USER_MANAGEMENT.md) for detailed instructions

### Channel Configuration

Channels are managed in the database with per-channel scheduling:

```bash
sqlite3 data/video_summary.db

# Add a channel
INSERT INTO channels (channel_handle, channel_name, youtube_channel_id, language,
                      check_start_hour, check_start_minute, check_end_hour)
VALUES ('@channelhandle', 'Channel Name', 'UCxxxxx', 'es', 10, 0, 14);
```

Channel schedule settings:
- `check_start_hour` / `check_start_minute` - Start of the daily check window
- `check_end_hour` - End of the daily check window
- `check_interval_minutes` - How often to check within the window (default: 5)
- `language` - Language code for transcript fetching (default: `es`)
- `active` - Whether the channel is active (1=yes, 0=no)

## Database

The bot uses SQLite to track:
- User subscriptions
- Channel configurations
- Processed video summaries
- Check schedules

Database location: [data/video_summary.db](data/video_summary.db)

## Development

### Running Tests
```bash
pytest tests/
```

### Using the Playground Notebook
```bash
jupyter notebook notebooks/playground.ipynb
```

### Project Commands

Install in development mode:
```bash
pip install -e .
```

## API Quota Management

The bot uses RSS feeds for video discovery (quota-free) and only uses the YouTube API for:
- Initial channel ID lookup (one-time)
- Video metadata retrieval

This approach minimizes API quota usage significantly.

## License

MIT

## Contributing

Pull requests are welcome! Please ensure:
- Code follows the existing structure
- All tests pass
- Documentation is updated
