# cogs ⚡

A collection of cogs (plugins) for [Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot).

## Installation

> You need to ensure you have the downloader enabled first.

```
[p]load downloader
```

Then add this repository:

```
[p]repo add jrc2-cogs https://github.com/jrc2/Red-Discord-Bot-Cogs
```

Install a cog:

```
[p]cog install jrc2-cogs <cog_name>
```

Load the cog:

```
[p]load <cog_name>
```

> **Note:** Replace `[p]` with your bot's prefix (e.g., `.` or `!`).


## Available Cogs

### Secret Santa

Manage Secret Santa events with participant matching, anonymous messaging, and gift tracking.

**Installation:**
```
[p]cog install jrc2-cogs secret_santa
[p]load secret_santa
```

**Commands:**

| Command | Description |
|---------|-------------|
| `[p]santa create <event_name> <date> <max_price> @participants...` | Create a new Secret Santa event (Admin) |
| `[p]santa import <event_name> <date> <max_price> <pairings...>` | Import an existing event with forced pairings (Admin) |
| `[p]santa match <event_name>` | Match all participants randomly (Admin) |
| `[p]santa rematch <event_name>` | Redo matching for an event (Admin) |
| `[p]santa status <event_name>` | Check the status of an event (Admin) |
| `[p]santa list` | List all Secret Santa events (Admin) |
| `[p]santa delete <event_name>` | Delete an event (Admin) |
| `[p]santa remind <event_name>` | Send reminder DMs to all participants (Admin) |
| `[p]santa add <event_name> @users...` | Add participants to an event (Admin) |
| `[p]santa remove <event_name> @users...` | Remove participants from an event (Admin) |
| `[p]santa message <event_name> <message>` | Send anonymous message to your giftee |
| `[p]santa reply <event_name> <message>` | Send anonymous reply to your Secret Santa |
| `[p]santa sent <event_name>` | Mark that you have sent your gift |
| `[p]santa received <event_name>` | Mark that you have received your gift |
| `[p]santa whoami <event_name>` | Check who you are matched to (sent via DM) |

**DM Commands (for anonymity):**

| Command | Description |
|---------|-------------|
| `[p]santadm message <event_id> <message>` | Send anonymous message to your giftee via DM |
| `[p]santadm reply <event_id> <message>` | Reply to your Secret Santa via DM |
| `[p]santadm wishlist <event_id> <wishlist>` | Set your wishlist via DM |
| `[p]santadm info <event_id>` | Get your event info via DM |
| `[p]santadm sent <event_id>` | Mark gift as sent via DM |
| `[p]santadm received <event_id>` | Mark gift as received via DM |

## Development

### Testing

This repository includes automated testing to ensure all cogs are compatible with Red-DiscordBot:

**Requirements:**
- Python 3.11 (Red-DiscordBot does not support Python 3.12+)

**Setup:**
```bash
# Install Red-DiscordBot and dependencies
pip install Red-DiscordBot
pip install cinemagoer==2022.12.27 httpx discord.py python-a2s>=1.3.0 Pillow>=10.2.0

# Run the test suite
python test_redbot_setup.py
```

**What the tests validate:**
- Red-DiscordBot core modules can be imported
- All cog Python files have valid syntax
- All cogs can be imported successfully
- All cogs have the required `setup` function

**CI/CD:**

The repository uses GitHub Actions to automatically:
- Lint all code with flake8
- Install Red-DiscordBot on Python 3.11
- Test that all cogs can be imported
- Validate Python syntax for all files

## Support

For issues or feature requests, please visit the [GitHub repository](https://github.com/jrc2/cogs).
