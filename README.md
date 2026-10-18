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

### Emojify

Add themed emojis to the beginning of every channel name in your server. Emojify can use built-in seasonal presets or a custom list of emojis, making it easy to give your server a festive or themed appearance.

**Installation:**
```
[p]cog install jrc2-cogs emojify  
[p]load emojify
```

**Features:**
- Apply random emojis to all channel names
- Built-in seasonal presets:
  - `christmas`
  - `halloween`
- Use your own custom emoji list
- Automatically replaces existing emoji prefixes created by the cog
- Preview changes before applying them with `--dry-run`
- Restore channel names by removing emoji prefixes

**Commands:**

| Command | Description |
|----------|-------------|
| `[p]emojify christmas` | Apply random Christmas-themed emojis to all channels |
| `[p]emojify halloween` | Apply random Halloween-themed emojis to all channels |
| `[p]emojify 🌸 🌺 🌻 ...` | Apply random emojis from a custom emoji list |
| `[p]emojify christmas --dry-run` | Preview Christmas channel renames without making changes |
| `[p]emojify 🌸 🌺 🌻 --dry-run` | Preview custom emoji renames without making changes |
| `[p]unemojify` | Remove leading emoji prefixes from all channels |
| `[p]unemojify --dry-run` | Preview channel names after emoji removal |

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
| `[p]santa create <date> <max_price> @participants...` | Create a new Secret Santa event (Admin) |
| `[p]santa import <date> <max_price> <pairings...>` | Import an existing event with forced pairings (Admin) |
| `[p]santa match` | Match all participants randomly (Admin) |
| `[p]santa rematch` | Redo matching for an event (Admin) |
| `[p]santa status` | Check the status of an event (Admin) |
| `[p]santa list` | List all Secret Santa events (Admin) |
| `[p]santa delete` | Delete an event (Admin) |
| `[p]santa remind` | Send reminder DMs to all participants (Admin) |
| `[p]santa add @users...` | Add participants to an event (Admin) |
| `[p]santa remove @users...` | Remove participants from an event (Admin) |
| `[p]santa message <message>` | Send anonymous message to your giftee |
| `[p]santa reply <message>` | Send anonymous reply to your Secret Santa |
| `[p]santa sent` | Mark that you have sent your gift |
| `[p]santa received` | Mark that you have received your gift |
| `[p]santa whoami` | Check who you are matched to (sent via DM) |

**DM Commands (for anonymity):**

| Command | Description |
|---------|-------------|
| `[p]santadm message <message>` | Send anonymous message to your giftee via DM |
| `[p]santadm reply <message>` | Reply to your Secret Santa via DM |
| `[p]santadm wishlist <wishlist>` | Set your wishlist via DM |
| `[p]santadm info` | Get your event info via DM |
| `[p]santadm sent` | Mark gift as sent via DM |
| `[p]santadm received` | Mark gift as received via DM |

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
