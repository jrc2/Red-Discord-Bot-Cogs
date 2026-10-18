import discord
from redbot.core import commands
import regex
import random


class Emojify(commands.Cog):
    """Adds themed emojis to the front of all channel names."""

    def __init__(self, bot):
        self.bot = bot
        self.presets = {
            "christmas": ["🎄", "🎅", "❄️", "🎁", "⛄", "🔔", "🕯️", "🧦", "🦌", "🌟", "🛷", "🎀"],
            "halloween": ["🎃", "👻", "🕷️", "🕸️", "🦇", "🧛", "🌙", "🍬", "🧙", "🧹", "🐈‍⬛"],
        }

    def _is_emoji(self, text: str) -> bool:
        """
        Determine whether the provided text contains an emoji.

        Parameters
        ----------
        text : str
            The string to validate.

        Returns
        -------
        bool
            True if the string contains at least one emoji codepoint,
            otherwise False.
        """
        if not text:
            return False

        return bool(regex.search(r"\p{Emoji}", text))

    def _strip_leading_emoji(self, text: str) -> str:
        """
        Remove a leading emoji grapheme from a string.
        
        This is used to prevent channel names from accumulating multiple
        emoji prefixes when emojify is run repeatedly.
        
        Parameters
        ----------
        text : str
            The channel name to process.
        
        Returns
        -------
        str
            The channel name with the first emoji grapheme removed if one
            exists at the beginning of the name. Otherwise, the original
            string is returned unchanged.
        """
        if not text:
            return text

        match = regex.match(r"^\X", text)

        if not match:
            return text

        first = match.group()

        # If the first grapheme contains an emoji codepoint
        if regex.search(r"\p{Emoji}", first):
            return text[len(first):]

        return text

    @commands.has_permissions(manage_channels=True)
    @commands.command(name="emojify")
    async def emojify(self, ctx: commands.Context, preset_or_emoji: str, *rest: str):
        """
        Apply themed emoji prefixes to all channels in the server.

        The command accepts either a built-in preset name or a custom list
        of emojis. Existing leading emojis are removed before a new prefix
        is applied. Each channel receives a randomly selected emoji from
        the chosen set.

        Use `--dry-run` to preview the changes without renaming channels.

        Examples
        --------
        - [p]emojify christmas
        - [p]emojify halloween
        - [p]emojify 🌸 🌺 🌻
        - [p]emojify christmas --dry-run

        Parameters
        ----------
        preset_or_emoji : str
            A preset name or the first emoji in a custom emoji list.

        *rest : str
            Additional emojis and optional command flags.
        """
        # Check if it's a preset name
        preset = self.presets.get(preset_or_emoji.lower())

        dry_run = False
        args = list(rest)
        if "--dry-run" in args:
            dry_run = True
            args.remove("--dry-run")

        if preset is not None:
            emoji_list = preset
        else:
            # Collect all arguments and filter for valid emojis
            all_args = [preset_or_emoji] + args
            emoji_list = [arg for arg in all_args if self._is_emoji(arg)]

            if len(emoji_list) == 0:
                valid_presets = ", ".join(self.presets.keys())
                return await ctx.reply(
                    f"`{preset_or_emoji}` is not a valid preset or emoji. "
                    f"Available presets: **{valid_presets}**. "
                    "Usage: `!emojify christmas` or `!emojify 🌸 🌺 🌻`"
                )

        done = 0
        failed = []
        preview = []

        for channel in ctx.guild.channels:
            emoji = random.choice(emoji_list)
            stripped = self._strip_leading_emoji(channel.name)
            new_name = f"{emoji}{stripped}"
            if new_name == channel.name:
                continue

            preview.append(f"{channel.name} -> {new_name}")

            if dry_run:
                continue

            try:
                await channel.edit(name=new_name)
                done += 1
            except discord.Forbidden:
                failed.append(channel.name)
            except discord.HTTPException:
                failed.append(channel.name)

        if dry_run:
            text = "\n".join(preview[:20])

            if len(preview) > 20:
                text += (f"\n...and {len(preview) - 20} more")

            return await ctx.reply(f"**DRY RUN**\n```{text}```")

        msg = f"Applied emojis to **{done}** channel(s)."
        if failed:
            msg += f" Failed to rename: {', '.join(failed)}."
        await ctx.reply(msg)

    @commands.has_permissions(manage_channels=True)
    @commands.command(name="unemojify")
    async def unemojify(self, ctx: commands.Context, *args):
        """
        Remove leading emoji prefixes from all channel names.

        Performs a best-effort cleanup by stripping the first emoji grapheme
        from channel names. This restores channels renamed by the emojify
        command.

        Use `--dry-run` to preview the changes without modifying channels.

        Examples
        --------
        - [p]unemojify
        - [p]unemojify --dry-run

        Parameters
        ----------
        *args : str
            Optional command flags such as `--dry-run`.
        """
        dry_run = "--dry-run" in args
        done = 0
        failed = []
        preview = []

        for channel in ctx.guild.channels:
            stripped = self._strip_leading_emoji(
                channel.name
            )
            if stripped != channel.name:
                preview.append(f"{channel.name} -> {stripped}")

                if dry_run:
                    continue
            
                try:
                    await channel.edit(name=stripped)
                    done += 1
                except (discord.Forbidden, discord.HTTPException):
                    failed.append(channel.name)

        if dry_run:
            text = "\n".join(preview[:20])

            if len(preview) > 20:
                text += (f"\n...and {len(preview) - 20} more")

            return await ctx.reply(f"**DRY RUN**\n```{text}```")
        
        msg = f"Cleaned **{done}** channel(s)."
        if failed:
            msg += f" Failed: {', '.join(failed)}."
        await ctx.reply(msg)
