# HOMIES Discord Bot

A feature-rich Discord bot built with **discord.py** featuring advanced moderation, analytics, voting systems, and server management tools.

## Features

### 🗳️ Advanced Voting System
- Create polls with 2-4 options via modal interface
- Button-based voting (not reactions)
- Member participation tracking with percentage calculations
- One vote per user enforcement
- Vote persistence with JSON storage
- Admin-only vote management and cleanup

### 🛡️ Moderation Tools
- **Mute/Timeout**: Temporarily timeout members with custom durations (30m, 2h, 1d, etc.)
- **Slowmode**: Set channel slowmode with configurable delays
- **Role Hierarchy**: Respects Discord role permissions for moderation actions

### 🎙️ Voice Channel Management
- Dynamic temporary voice channels with auto-cleanup
- Custom channel renaming with rate limiting
- User limit configuration (0-99)
- Lock/unlock channel access
- Channel ownership claim system
- Voice channel information display

### 📊 Server Analytics & Monitoring
- Real-time server health dashboard (`/serverhealth`)
- Member statistics tracking
- Message activity monitoring per channel
- Daily engagement metrics with automatic reset
- Top channels ranking
- Bot uptime tracking with global file optimization
- Voice activity statistics
- System resource monitoring (CPU, RAM, disk, temperature)

### 🎨 Creative Tools
- Custom embed builder with modal interface
- HEX color code support
- Named color support (red, blue, green, etc.)
- Announcement system with multiple formats

### 👤 User Information
- Detailed user profile lookup
- Server member statistics
- Avatar viewing
- User activity tracking

### 🤖 Bot Management
- Per-guild data isolation (separate stats per server)
- AFK system with custom reasons
- Bot stay-in-voice feature for 24/7 presence
- Command help documentation
- Server role listing
- Ping/latency checking

## Installation

### Prerequisites
- Python 3.10+
- discord.py 2.0+
- psutil (for system monitoring)
- Git

### Setup Steps

1. **Clone the repository:**
```bash
git clone https://github.com/jimbon25/HOMIES-discord-bot.git
cd discord-announcer
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**
Create a `.env` file in the root directory:
```env
BOT_TOKEN=your_discord_bot_token_here
OWNER_ID=your_discord_user_id_here
```

5. **Run the bot:**
```bash
python bot.py
```

## Project Structure

```
discord-announcer/
├── bot.py                      # Main bot file
├── cogs/                       # Command modules
│   ├── afk.py                 # AFK system
│   ├── avatar.py              # Avatar viewer
│   ├── author.py              # Bot info
│   ├── dashboard.py           # Server health display
│   ├── disableslowmode.py     # Remove slowmode
│   ├── embedbuilder.py        # Embed creation tool
│   ├── help.py                # Help command
│   ├── listcommands.py        # List all commands
│   ├── mute.py                # Mute/timeout users
│   ├── ping.py                # Bot latency check
│   ├── rolelist.py            # List server roles
│   ├── serverinfo.py          # Server information
│   ├── slowmode.py            # Set slowmode
│   ├── stayafk.py             # Bot voice stay (24/7)
│   ├── system.py              # System monitoring
│   ├── test.py                # Test command
│   ├── userinfo.py            # User profile
│   ├── voicechannel.py        # Voice channel management
│   └── vote.py                # Voting system
├── dashboard/                 # Analytics modules
│   ├── tracker.py             # Activity tracking
│   ├── analytics.py           # Metrics computation
│   └── display.py             # Dashboard display
├── data/                      # Data storage (gitignored)
│   ├── stats_guild_*.json    # Per-guild statistics
│   ├── uptime.json           # Global uptime tracking
│   └── votes/                # Vote data files
├── .env                       # Environment variables (gitignored)
├── .gitignore                 # Git ignore rules
├── discord-bot.service        # Systemd service file
└── README.md                  # This file
```

## Commands

### Announcements
- `/announce` - Send announcement with embed/plain format
- `/announce text_size` - Configure text size (normal, medium, large)

### Voting System
- `/create_vote` - Create a voting poll (admin-only)
- `/cleanup_votes` - Delete all vote data (admin-only)

### Moderation
- `/slowmode <channel> <seconds>` - Set channel slowmode (admin)
- `/disableslowmode <channel>` - Remove slowmode (admin)
- `/mute <member> <duration>` - Timeout member (admin)
- `/unmute <member>` - Remove timeout (admin)

### Voice Channels
- `/vc rename <name>` - Rename your voice channel
- `/vc limit <number>` - Set user limit (0-99)
- `/vc lock` - Lock/unlock channel
- `/vc claim` - Claim channel ownership
- `/vc info` - View channel information

### Bot Voice Management
- `/stayafk join` - Bot joins and stays in your voice channel
- `/stayafk leave` - Bot leaves voice channel
- `/stayafk status` - Check bot voice connection status
- `/stayafk clearcache` - Clear voice cache (troubleshooting)

### Server Information
- `/serverhealth` - Main server health dashboard
- `/members` - Detailed member statistics
- `/activity` - Activity tracking and top channels
- `/engagement` - Engagement metrics
- `/stats` - Quick server statistics
- `/serverinfo` - Full server details
- `/system` - System resource monitoring (owner-only)

### User Tools
- `/userinfo <@user>` - User profile information
- `/avatar <@user>` - View user avatar
- `/rolelist` - List all server roles
- `/help` - Display all available commands

### Creative Tools
- `/createembed` - Create custom embeds with modal

### Bot Info
- `/author` - Bot and author information
- `/ping` - Check bot latency
- `/test` - Test bot response

### AFK System
- `?afk <reason>` - Set AFK status (prefix command)

## Data Storage

### Per-Guild Data
Each server gets its own statistics file: `data/stats_guild_{guild_id}.json`

Tracks:
- Member counts and activity
- Message statistics
- Daily joins/leaves
- Channel activity
- Engagement metrics
- Bot latency per server

### Global Data
- `data/uptime.json` - Bot uptime (updated every 60 seconds)
- `data/votes/` - Vote poll data and results

## Security Features

- ✅ `.env` file protection (tokens never committed)
- ✅ Per-guild data isolation
- ✅ Role hierarchy checking for moderation
- ✅ Admin-only command restrictions
- ✅ Owner-only system commands
- ✅ User identification for vote enforcement
- ✅ Rate limiting on voice channel operations

## Performance Optimizations

- **Global uptime tracking** - Reduced from 100x disk writes to 1 write per 60 seconds
- **Per-guild data** - Separate stats files prevent conflicts
- **Date-based daily reset** - Accurate daily metric reset with timestamp checking
- **Persistent vote storage** - JSON-based voting with member count context
- **Efficient component limits** - Respects Discord API max 5 components per message

## Deployment

### Systemd Service
The bot can be run as a systemd service for 24/7 operation:

```bash
# Copy service file
sudo cp discord-bot.service /etc/systemd/system/

# Enable and start service
sudo systemctl enable discord-bot
sudo systemctl start discord-bot

# Check status
sudo systemctl status discord-bot

# View logs
sudo journalctl -u discord-bot -f
```

### Environment Configuration
Ensure `.env` file contains:
- `BOT_TOKEN` - Your Discord bot token (from Discord Developer Portal)
- `OWNER_ID` - Your Discord user ID (for `/system` command access)

## Development

### Running in Development Mode
```bash
# With auto-reload (requires nodemon or similar)
python bot.py

# Enable debug logging
# Edit bot.py and set: discord.utils.setup_logging(level=logging.DEBUG)
```

### Adding New Cogs
1. Create new file in `cogs/` directory
2. Create class extending `commands.Cog`
3. Implement `async def setup(bot)` function
4. Bot will auto-load on restart

### Testing Commands
Use `/test` command to verify bot is responding

## Troubleshooting

### Bot not connecting to voice
- Use `/stayafk clearcache` to reset voice connection
- Check bot has "Connect" and "Speak" permissions in voice channel

### Commands not appearing
- Use `/help` to verify commands synced
- Restart bot: `sudo systemctl restart discord-bot`
- Check bot has slash command permissions

### Vote system issues
- Use `/cleanup_votes` to reset vote data
- Check vote options are 2-4 items

### Uptime tracking issues
- Delete `data/uptime.json` and restart bot
- Check file permissions on `data/` directory

## Technical Stack

- **Language**: Python 3.10+
- **Framework**: discord.py 2.0+
- **Async**: asyncio
- **Data Storage**: JSON
- **Monitoring**: psutil
- **Deployment**: systemd

## Configuration

### Discord Intents
Bot requires these intents:
- `Intents.default()` - Standard intents
- `Intents.members` - Member join/leave tracking
- `Intents.message_content` - Message content reading

### Permissions Required
Ensure bot role has:
- Send Messages
- Embed Links
- Read Message History
- Manage Messages
- Manage Roles (for mute)
- Manage Channels (for slowmode)
- Move Members
- Mute Members
- Deafen Members
- Manage Guild

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
3. Push to the branch
5. Create a Pull Request

## License

This project is open source and available under the MIT License.

## Support

For issues, bugs, or feature requests, please open an issue on GitHub:
https://github.com/jimbon25/HOMIES-discord-bot/issues

## Author

**j1mb** - Discord Bot Developer

---

**Last Updated**: March 2026
**Bot Version**: 1.0
**Total Commands**: 40+
**Cogs Loaded**: 18
