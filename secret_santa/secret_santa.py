import datetime
import logging
import random
from typing import List, Optional, Union

import discord
from redbot.core import Config, checks, commands

log = logging.getLogger("red.cog.secret_santa")

IDENTIFIER = 8472916358274916

# Discord embed field character limit
EMBED_FIELD_MAX_LENGTH = 1024

class SecretSanta(commands.Cog):
    """Manage Secret Santa events for your server."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=IDENTIFIER)

        default_guild = {
            "event": None,
        }
        self.config.register_guild(**default_guild)

    async def _get_event(self, guild):
        return await self.config.guild(guild).event()

    async def _get_user_event(self, user_id: int):
        all_guilds = await self.config.all_guilds()

        for guild_id, guild_data in all_guilds.items():
            event = guild_data.get("event")

            if not event:
                continue

            if str(user_id) in event.get("participants", {}):
                return guild_id, event

        return None

    async def _save_event(self, guild_or_id, event):
        if isinstance(guild_or_id, int):
            await self.config.guild_from_id(guild_or_id).event.set(event)
        else:
            await self.config.guild(guild_or_id).event.set(event)

    async def red_delete_data_for_user(self, *, requester, user_id: int):
        """Delete user data when requested."""

        all_guilds = await self.config.all_guilds()

        for guild_id, guild_data in all_guilds.items():

            event = guild_data.get("event")

            if not event:
                continue

            user_id_str = str(user_id)

            if user_id_str in event["participants"]:
                del event["participants"][user_id_str]
                await self.config.guild_from_id(guild_id).event.set(event)

    def _resolve_participants(
        self,
        participants: List[Union[discord.Member, discord.Role]]
    ) -> List[discord.Member]:
        """Resolve members and roles into a deduplicated member list."""

        resolved = []

        for item in participants:
            if isinstance(item, discord.Role):
                resolved.extend(
                    member
                    for member in item.members
                    if not member.bot
                )
            elif (
                isinstance(item, discord.Member)
                and not item.bot
            ):
                resolved.append(item)

        return list({
            member.id: member
            for member in resolved
        }.values())

    @commands.hybrid_group()
    @commands.guild_only()
    async def santa(self, ctx):
        """Secret Santa event management."""

    @santa.command(name="create")
    @checks.admin_or_permissions(manage_guild=True)
    async def santa_create(
        self,
        ctx,
        event_name: str,
        target_date: str,
        max_price: str,
        participants: commands.Greedy[
            Union[discord.Member, discord.Role]
        ]
    ):
        """Create a new Secret Santa event.

        Parameters:
        - event_name: A unique name for this event
        - target_date: The target date (YYYY-MM-DD format)
        - max_price: Maximum gift price (e.g., "$25" or "25 USD")
        - participants: Mention all participants and/or a role (at least 2 resolved participants required)

        Example: [p]santa create xmas2026 2026-12-25 "$50" @SecretSanta
                 [p]santa create xmas2026 2026-12-25 "$50" @John @Jane @Bob
                 [p]santa create xmas2026 2026-12-25 "$50" @SecretSanta @John
        """
        # Validate date format
        try:
            parsed_date = datetime.datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            await ctx.send("Invalid date format. Please use YYYY-MM-DD (e.g., 2024-12-25)")
            return

        resolved_participants = self._resolve_participants(participants)

        # Validate participants
        if len(resolved_participants) < 2:
            await ctx.send("You need at least 2 participants for a Secret Santa event.")
            return

        # Check if an event already exists
        current_event = await self._get_event(ctx.guild)

        if current_event:
            await ctx.send(
                "A Secret Santa event already exists. Delete it first."
            )
            return

        # Create participant data
        participant_data = {}
        for member in resolved_participants:
            participant_data[str(member.id)] = {
                "matched_to": None,
                "sent_gift": False,
                "received_gift": False,
                "wishlist": None,
            }

        # Create the event
        event = {
            "name": event_name,
            "target_date": target_date,
            "max_price": max_price,
            "participants": participant_data,
            "blocked_pairings": [],
            "family_groups": [],
            "created_by": ctx.author.id,
            "created_at": datetime.datetime.now().isoformat(),
            "matched": False,
        }

        await self._save_event(ctx.guild, event)

        # Send DMs to participants asking for their wishlist
        dm_success = 0
        dm_failed = 0
        for member in resolved_participants:
            try:
                embed = discord.Embed(
                    title="🎅 You've Been Added to a Secret Santa Event!",
                    description=(
                        f"You've been added to **{event_name}** in **{ctx.guild.name}**!"
                    ),
                    color=discord.Color.red()
                )
                embed.add_field(name="Target Date", value=parsed_date.strftime("%B %d, %Y"), inline=True)
                embed.add_field(name="Max Price", value=max_price, inline=True)
                embed.add_field(
                    name="📝 Set Your Wishlist",
                    value=(
                        f"Please set your wishlist so your Secret Santa knows what you'd like!\n"
                        f"DM me: `{ctx.prefix}santadm wishlist <your wishlist>`\n\n"
                        f"Example: `{ctx.prefix}santadm wishlist "
                        f"I'd love a book, some chocolates, or a cozy sweater!`"
                    ),
                    inline=False
                )
                embed.add_field(
                    name="💬 Anonymous Messaging",
                    value=(
                        f"After matching, you can send anonymous messages via DM!\n"
                        f"`{ctx.prefix}santadm message <your message>`"
                    ),
                    inline=False
                )
                embed.set_footer(text="Your wishlist will be shared with your Secret Santa after matching!")
                await member.send(embed=embed)
                dm_success += 1
            except discord.Forbidden:
                dm_failed += 1

        participant_names = ", ".join(p.display_name for p in resolved_participants)
        embed = discord.Embed(
            title="🎅 Secret Santa Event Created!",
            description=f"Event **{event_name}** has been created.",
            color=discord.Color.red()
        )
        embed.add_field(name="Target Date", value=parsed_date.strftime("%B %d, %Y"), inline=True)
        embed.add_field(name="Max Price", value=max_price, inline=True)
        embed.add_field(name="Participants", value=f"{len(resolved_participants)} people", inline=True)
        embed.add_field(name="DMs Sent", value=f"{dm_success} ✅ / {dm_failed} ❌", inline=True)
        embed.add_field(name="Participant List", value=participant_names, inline=False)
        embed.set_footer(
            text=f"Participants have been asked for wishlists. Use {ctx.prefix}santa match to assign pairs!"
        )

        await ctx.send(embed=embed)

    @santa.command(name="import")
    @checks.admin_or_permissions(manage_guild=True)
    async def santa_import(
        self,
        ctx,
        event_name: str,
        target_date: str,
        max_price: str,
        pairings: Optional[str] = None
    ):
        """Import an existing Secret Santa event with forced pairings.

        Parameters
        ----------
        event_name : str
            A unique name for this event
        target_date : str
            The target date (YYYY-MM-DD format)
        max_price : str
            Maximum gift price (e.g., "$25" or "25 USD")
        pairings : Optional[str]
            Space-separated pairs in format "giver_id:receiver_id" (use Discord user IDs)

        Example: [p]santa import xmas2024 2024-12-25 "$50" "123456789:987654321 111222333:444555666"
        """
        # Validate date format
        try:
            parsed_date = datetime.datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            await ctx.send("Invalid date format. Please use YYYY-MM-DD (e.g., 2024-12-25)")
            return

        if not pairings:
            await ctx.send("You need at least 1 pairing to import.")
            return

        # Parse space-separated pairings
        pairings_list = pairings.split()

        if len(pairings_list) < 1:
            await ctx.send("You need at least 1 pairing to import.")
            return

        # Check if event already exists
        current_event = await self._get_event(ctx.guild)
        if current_event:
            await ctx.send(
                "A Secret Santa event already exists. Delete it first."
            )
            return

        # Parse pairings
        participant_data = {}
        parsed_pairings = []
        all_givers = set()
        all_receivers = set()

        for pairing in pairings_list:
            if ":" not in pairing:
                await ctx.send(f"Invalid pairing format: `{pairing}`. Use format `giver_id:receiver_id`")
                return
            giver_str, receiver_str = pairing.split(":", 1)
            try:
                giver_id = int(giver_str.strip())
                receiver_id = int(receiver_str.strip())
            except ValueError:
                await ctx.send(f"Invalid user IDs in pairing: `{pairing}`. IDs must be numbers.")
                return

            if giver_id in all_givers:
                await ctx.send(f"User {giver_id} is listed as a giver more than once.")
                return
            if giver_id == receiver_id:
                await ctx.send(
                    f"User {giver_id} cannot give a gift to themselves. "
                    "Please fix the pairing."
                )
                return
            all_givers.add(giver_id)
            all_receivers.add(receiver_id)
            parsed_pairings.append((giver_id, receiver_id))

        # Validate that pairings form a complete exchange
        # Every participant should both give and receive
        if all_givers != all_receivers:
            missing_givers = all_receivers - all_givers
            missing_receivers = all_givers - all_receivers
            msg = "Incomplete pairings detected. "
            if missing_givers:
                msg += f"Users {missing_givers} receive but don't give. "
            if missing_receivers:
                msg += f"Users {missing_receivers} give but don't receive."
            await ctx.send(msg)
            return

        # Create participant data from pairings
        all_participants = all_givers | all_receivers
        for user_id in all_participants:
            participant_data[str(user_id)] = {
                "matched_to": None,
                "sent_gift": False,
                "received_gift": False,
                "wishlist": None,
            }

        # Apply pairings
        for giver_id, receiver_id in parsed_pairings:
            participant_data[str(giver_id)]["matched_to"] = receiver_id

        # Create the event
        event = {
            "name": event_name,
            "target_date": target_date,
            "max_price": max_price,
            "participants": participant_data,
            "blocked_pairings": [],
            "family_groups": [],
            "created_by": ctx.author.id,
            "created_at": datetime.datetime.now().isoformat(),
            "matched": True,
        }

        await self._save_event(ctx.guild, event)

        # Send DMs to participants with their match info and ask for wishlist
        dm_success = 0
        dm_failed = 0
        for giver_id, receiver_id in parsed_pairings:
            giver = self.bot.get_user(giver_id)
            receiver = self.bot.get_user(receiver_id)
            if giver and receiver:
                try:
                    embed = discord.Embed(
                        title="🎅 Secret Santa Match!",
                        description=f"You have been matched for **{event_name}** in **{ctx.guild.name}**!",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="Your Giftee", value=receiver.display_name, inline=True)
                    embed.add_field(name="Max Price", value=max_price, inline=True)
                    embed.add_field(name="Target Date", value=parsed_date.strftime("%B %d, %Y"), inline=True)
                    embed.add_field(
                        name="📝 Set Your Wishlist",
                        value=(
                            f"Set your wishlist so your Santa knows what you'd like!\n"
                            f"DM me: `{ctx.prefix}santadm wishlist <your wishlist>`"
                        ),
                        inline=False
                    )
                    embed.add_field(
                        name="Anonymous Messaging",
                        value=(
                            f"Send anonymous messages to your giftee via DM:\n"
                            f"`{ctx.prefix}santadm message <your message>`\n\n"
                            f"Reply to your Santa via DM:\n"
                            f"`{ctx.prefix}santadm reply <your message>`"
                        ),
                        inline=False
                    )
                    embed.set_footer(text="Remember to keep it a secret! 🤫")
                    await giver.send(embed=embed)
                    dm_success += 1
                except discord.Forbidden:
                    dm_failed += 1

        embed = discord.Embed(
            title="🎅 Secret Santa Event Imported!",
            description=f"Event **{event_name}** has been imported with {len(parsed_pairings)} pairings.",
            color=discord.Color.green()
        )
        embed.add_field(name="Target Date", value=parsed_date.strftime("%B %d, %Y"), inline=True)
        embed.add_field(name="Max Price", value=max_price, inline=True)
        embed.add_field(name="Participants", value=f"{len(all_participants)} people", inline=True)
        embed.add_field(name="DMs Sent", value=f"{dm_success} ✅ / {dm_failed} ❌", inline=True)
        embed.set_footer(text=f"Participants can use {ctx.prefix}santadm commands in DMs to message their match!")

        await ctx.send(embed=embed)

    @santa.command(name="match")
    @checks.admin_or_permissions(manage_guild=True)
    async def santa_match(self, ctx):
        """Match all participants in a Secret Santa event.

        This will randomly assign each participant to give a gift to another participant.
        Each person gives to exactly one person and receives from exactly one person.

        Example: [p]santa match
        """
        event = await self._get_event(ctx.guild)

        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return

        event_name = event["name"]

        if event["matched"]:
            await ctx.send(
                f"Event `{event_name}` has already been matched. "
                f"Use `{ctx.prefix}santa rematch` to redo the matching."
            )
            return

        participants = list(event["participants"].keys())

        if len(participants) < 2:
            await ctx.send("Not enough participants to match.")
            return

        # Generate random pairings (each person gives to one person)
        pairings = self._generate_pairings(
            [int(p) for p in participants],
            event.get("blocked_pairings", []),
            event.get("family_groups", []),
        )
        if not pairings:
            await ctx.send("Failed to generate valid pairings. Please try again.")
            return

        # Update participant data with pairings
        for giver_id, receiver_id in pairings:
            event["participants"][str(giver_id)]["matched_to"] = receiver_id
        event["matched"] = True
        await self._save_event(ctx.guild, event)

        # Reload event data to get wishlists
        event = await self._get_event(ctx.guild)

        # Send DMs to participants
        success_count = 0
        fail_count = 0
        for giver_id, receiver_id in pairings:
            giver = self.bot.get_user(giver_id)
            receiver = self.bot.get_user(receiver_id)
            if giver and receiver:
                try:
                    # Get the receiver's wishlist
                    receiver_wishlist = event["participants"].get(str(receiver_id), {}).get("wishlist")

                    embed = discord.Embed(
                        title="🎅 Secret Santa Match!",
                        description=f"You have been matched for **{event_name}** in **{ctx.guild.name}**!",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="Your Giftee", value=receiver.display_name, inline=True)
                    embed.add_field(name="Max Price", value=event["max_price"], inline=True)
                    embed.add_field(name="Target Date", value=event["target_date"], inline=True)

                    # Include the giftee's wishlist if available
                    if receiver_wishlist:
                        embed.add_field(
                            name="🎁 Your Giftee's Wishlist",
                            value=receiver_wishlist[:EMBED_FIELD_MAX_LENGTH],
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="🎁 Your Giftee's Wishlist",
                            value="No wishlist set yet. You can ask them via anonymous message!",
                            inline=False
                        )

                    embed.add_field(
                        name="Anonymous Messaging (via DM)",
                        value=(
                            f"Send anonymous messages to your giftee:\n"
                            f"`{ctx.prefix}santadm message <your message>`\n\n"
                            f"Reply to your Santa:\n"
                            f"`{ctx.prefix}santadm reply <your message>`"
                        ),
                        inline=False
                    )
                    embed.set_footer(text="Remember to keep it a secret! 🤫")
                    await giver.send(embed=embed)
                    success_count += 1
                except discord.Forbidden:
                    fail_count += 1

        embed = discord.Embed(
            title="🎅 Matching Complete!",
            description=f"All participants in **{event_name}** have been matched!",
            color=discord.Color.green()
        )
        embed.add_field(name="DMs Sent", value=str(success_count), inline=True)
        embed.add_field(name="DMs Failed", value=str(fail_count), inline=True)
        if fail_count > 0:
            embed.set_footer(
                text=f"Some users have DMs disabled. They can check their match with {ctx.prefix}santadm info"
            )

        await ctx.send(embed=embed)

    @santa.command(name="rematch")
    @checks.admin_or_permissions(manage_guild=True)
    async def santa_rematch(self, ctx):
        """Redo matching for a Secret Santa event.

        This will clear all existing pairings and create new random ones.

        Example: [p]santa rematch
        """
        event = await self._get_event(ctx.guild)

        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return

        event_name = event["name"]

        # Reset matched status
        for user_id in event["participants"]:
            event["participants"][user_id]["matched_to"] = None

        event["matched"] = False
        await self._save_event(ctx.guild, event)

        await ctx.send(
            f"Pairings for `{event_name}` have been reset. "
            f"Use `{ctx.prefix}santa match` to create new pairings."
        )

    def _generate_pairings(
        self,
        participants: List[int],
        blocked_pairings: List[list] = None,
        family_groups: List[list] = None,
    ) -> Optional[List[tuple]]:
        """
        Generate Secret Santa matches while respecting
        directional pair restrictions and family groups.
        """

        blocked_pairings = blocked_pairings or []
        family_groups = family_groups or []

        blocked_lookup = {
            (giver, receiver)
            for giver, receiver in blocked_pairings
        }

        family_lookup = {}

        for group in family_groups:
            members = set(group)

            for member in members:
                family_lookup.setdefault(
                    member,
                    set()
                ).update(
                    members - {member}
                )

        max_attempts = 5000

        for _ in range(max_attempts):

            shuffled = participants.copy()
            random.shuffle(shuffled)

            valid = True

            for giver, receiver in zip(
                participants,
                shuffled
            ):

                if giver == receiver:
                    valid = False
                    break

                if (giver, receiver) in blocked_lookup:
                    valid = False
                    break

                if receiver in family_lookup.get(
                    giver,
                    set()
                ):
                    valid = False
                    break

            if valid:
                return list(
                    zip(participants, shuffled)
                )

        return None

    @santa.command(name="blockpair")
    @checks.admin_or_permissions(manage_guild=True)
    async def santa_blockpair(
        self,
        ctx,
        giver: discord.Member,
        receiver: discord.Member,
    ):
        """Prevent one user from being assigned another user."""

        event = await self._get_event(ctx.guild)
        
        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return
        
        restriction = [giver.id, receiver.id]

        blocked = event.setdefault(
            "blocked_pairings",
            []
        )

        if restriction in blocked:
            await ctx.send("That restriction already exists.")
            return

        blocked.append(restriction)
        await self._save_event(ctx.guild, event)

        await ctx.send(
            f"✅ {giver.display_name} cannot draw {receiver.display_name}."
        )

    @santa.command(name="unblockpair")
    @checks.admin_or_permissions(manage_guild=True)
    async def santa_unblockpair(
        self,
        ctx,
        giver: discord.Member,
        receiver: discord.Member,
    ):
        """Remove a pairing restriction."""

        event = await self._get_event(ctx.guild)
        
        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return
        
        restriction = [giver.id, receiver.id]

        blocked = event.setdefault(
            "blocked_pairings",
            []
        )

        if restriction not in blocked:
            await ctx.send("That restriction does not exist.")
            return

        blocked.remove(restriction)
        await self._save_event(ctx.guild, event)

        await ctx.send(
            f"✅ {giver.display_name} may now draw {receiver.display_name}."
        )

    @santa.command(name="pairings")
    @checks.admin_or_permissions(manage_guild=True)
    async def santa_pairings(
        self,
        ctx,
    ):
        """List directional pairing restrictions."""

        event = await self._get_event(ctx.guild)
        
        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return
        
        blocked = event.get(
            "blocked_pairings",
            []
        )

        if not blocked:
            await ctx.send("No pairing restrictions configured.")
            return

        lines = []

        for giver_id, receiver_id in blocked:
            giver = ctx.guild.get_member(giver_id)
            receiver = ctx.guild.get_member(receiver_id)

            giver_name = giver.display_name if giver else str(giver_id)
            receiver_name = receiver.display_name if receiver else str(receiver_id)

            lines.append(f"• {giver_name} → {receiver_name}")

        await ctx.send("\n".join(lines))

    @santa.command(name="family")
    @checks.admin_or_permissions(manage_guild=True)
    async def santa_family(
        self,
        ctx,
        members: commands.Greedy[discord.Member]
    ):
        """
        Add a household/family group.
        Members in the same group cannot draw one another.
        """

        if len(members) < 2:
            await ctx.send(
                "You must specify at least two members."
            )
            return
        

        event = await self._get_event(ctx.guild)
        
        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return
        
        group = list({m.id for m in members})

        family_groups = event.setdefault(
            "family_groups",
            []
        )

        family_groups.append(group)
        await self._save_event(ctx.guild, event)

        names = ", ".join(
            member.display_name
            for member in members
        )

        await ctx.send(
            f"✅ Added family group: {names}"
        )

    @santa.command(name="families")
    @checks.admin_or_permissions(manage_guild=True)
    async def santa_families(
        self,
        ctx,
    ):
        """Show family groups."""

        event = await self._get_event(ctx.guild)
        
        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return
        
        groups = event.get(
            "family_groups",
            []
        )

        if not groups:
            await ctx.send(
                "No family groups configured."
            )
            return

        lines = []

        for idx, group in enumerate(groups, start=1):
            names = []

            for uid in group:
                member = ctx.guild.get_member(uid)

                if member:
                    names.append(member.display_name)
                else:
                    names.append(str(uid))

            lines.append(
                f"{idx}. {', '.join(names)}"
            )

        await ctx.send("\n".join(lines))

    @santa.command(name="removefamily")
    @checks.admin_or_permissions(manage_guild=True)
    async def santa_removefamily(
        self,
        ctx,
        index: int
    ):
        """Remove a family group."""

        event = await self._get_event(ctx.guild)
        
        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return
        
        groups = event.get(
            "family_groups",
            []
        )

        if index < 1 or index > len(groups):
            await ctx.send(
                "Invalid family group number."
            )
            return

        groups.pop(index - 1)
        await self._save_event(ctx.guild, event)

        await ctx.send(
            f"✅ Removed family group #{index}"
        )

    @santa.command(name="message")
    async def santa_message(self, ctx, *, message: str):
        """Send an anonymous message to your Secret Santa giftee.

        Your identity will be kept secret - the bot will relay the message.

        Example: [p]santa message What's your favorite color?
        """
        event = await self._get_event(ctx.guild)
        
        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return
        
        event_name = event["name"]

        if not event["matched"]:
            await ctx.send("This event hasn't been matched yet. Ask an admin to run the matching.")
            return

        user_id_str = str(ctx.author.id)
        if user_id_str not in event["participants"]:
            await ctx.send("You are not a participant in this event.")
            return

        matched_to = event["participants"][user_id_str]["matched_to"]
        if not matched_to:
            await ctx.send("You haven't been matched to anyone yet.")
            return

        recipient = self.bot.get_user(matched_to)
        if not recipient:
            await ctx.send("Could not find your giftee. They may have left the server.")
            return

        try:
            embed = discord.Embed(
                title="🎅 Anonymous Secret Santa Message!",
                description=message,
                color=discord.Color.red()
            )
            embed.add_field(name="Event", value=event_name, inline=True)
            embed.add_field(name="Server", value=ctx.guild.name, inline=True)
            embed.add_field(
                name="Reply",
                value=f"Reply anonymously via DM: `{ctx.prefix}santadm reply <message>`",
                inline=False
            )
            embed.set_footer(text="This is from your Secret Santa! 🎁")
            await recipient.send(embed=embed)

            # Delete the command message to preserve anonymity
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass

            # Send confirmation via DM to the sender
            try:
                await ctx.author.send(
                    f"✅ Your message to your Secret Santa giftee in "
                    f"**{event_name}** was sent successfully!"
                )
            except discord.Forbidden:
                # If we can't DM them, send a temporary message in channel
                temp_msg = await ctx.send("✅ Message sent!")
                await temp_msg.delete(delay=5)

        except discord.Forbidden:
            await ctx.send("Could not send message to your giftee. They may have DMs disabled.")

    @santa.command(name="reply")
    async def santa_reply(self, ctx, *, message: str):
        """Send an anonymous reply to your Secret Santa (the person giving you a gift).

        This allows you to respond to questions from your Secret Santa.

        Example: [p]santa reply My favorite color is blue!
        """
        event = await self._get_event(ctx.guild)
        
        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return
        
        event_name = event["name"]

        if not event["matched"]:
            await ctx.send("This event hasn't been matched yet.")
            return

        user_id_str = str(ctx.author.id)
        if user_id_str not in event["participants"]:
            await ctx.send("You are not a participant in this event.")
            return

        # Find who is giving a gift to this user
        santa_id = None
        for giver_id, data in event["participants"].items():
            if data["matched_to"] == ctx.author.id:
                santa_id = int(giver_id)
                break

        if not santa_id:
            await ctx.send("Could not find your Secret Santa. This might be a configuration error.")
            return

        santa = self.bot.get_user(santa_id)
        if not santa:
            await ctx.send("Could not find your Secret Santa. They may have left the server.")
            return

        try:
            embed = discord.Embed(
                title="🎁 Reply from Your Giftee!",
                description=message,
                color=discord.Color.green()
            )
            embed.add_field(name="Event", value=event_name, inline=True)
            embed.add_field(name="Server", value=ctx.guild.name, inline=True)
            embed.set_footer(text="This is from the person you're buying a gift for! 🎄")
            await santa.send(embed=embed)

            # Delete the command message to preserve anonymity
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass

            # Send confirmation via DM
            try:
                await ctx.author.send(f"✅ Your reply to your Secret Santa in **{event_name}** was sent successfully!")
            except discord.Forbidden:
                temp_msg = await ctx.send("✅ Reply sent!")
                await temp_msg.delete(delay=5)

        except discord.Forbidden:
            await ctx.send("Could not send reply to your Secret Santa. They may have DMs disabled.")

    @santa.command(name="sent")
    async def santa_sent(self, ctx):
        """Mark that you have sent your gift.

        Example: [p]santa sent
        """
        event = await self._get_event(ctx.guild)
        
        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return
        
        user_id_str = str(ctx.author.id)
        if user_id_str not in event["participants"]:
            await ctx.send("You are not a participant in this event.")
            return

        event["participants"][user_id_str]["sent_gift"] = True
        await self._save_event(ctx.guild, event)

        await ctx.send("🎁 You've marked your gift as **sent**! Thank you!")

    @santa.command(name="received")
    async def santa_received(self, ctx):
        """Mark that you have received your gift.

        Example: [p]santa received
        """
        event = await self._get_event(ctx.guild)
        
        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return
        
        user_id_str = str(ctx.author.id)
        if user_id_str not in event["participants"]:
            await ctx.send("You are not a participant in this event.")
            return

        event["participants"][user_id_str]["received_gift"] = True
        await self._save_event(ctx.guild, event)

        await ctx.send("🎄 You've marked your gift as **received**! Enjoy your present!")

    @santa.command(name="whoami")
    async def santa_whoami(self, ctx):
        """Check who you are matched to give a gift to (sent via DM).

        Example: [p]santa whoami
        """
        event = await self._get_event(ctx.guild)
        
        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return
        
        event_name = event["name"]

        user_id_str = str(ctx.author.id)

        if user_id_str not in event["participants"]:
            await ctx.send("You are not a participant in this event.")
            return

        if not event["matched"]:
            await ctx.send("This event hasn't been matched yet.")
            return

        matched_to = event["participants"][user_id_str]["matched_to"]
        if not matched_to:
            await ctx.send("You haven't been matched to anyone yet.")
            return

        recipient = self.bot.get_user(matched_to)
        if not recipient:
            await ctx.send("Could not find your giftee. They may have left the server.")
            return

        try:
            embed = discord.Embed(
                title="🎅 Your Secret Santa Assignment",
                description=f"For event **{event_name}** in **{ctx.guild.name}**",
                color=discord.Color.red()
            )
            embed.add_field(name="Your Giftee", value=recipient.display_name, inline=True)
            embed.add_field(name="Max Price", value=event["max_price"], inline=True)
            embed.add_field(name="Target Date", value=event["target_date"], inline=True)
            embed.add_field(
                name="Gift Status",
                value="✅ Sent" if event["participants"][user_id_str]["sent_gift"] else "⏳ Not yet sent",
                inline=True
            )
            embed.set_footer(text="Keep it a secret! 🤫")
            await ctx.author.send(embed=embed)
            await ctx.send("📬 Check your DMs!")
        except discord.Forbidden:
            await ctx.send("I couldn't send you a DM. Please enable DMs from server members.")

    @santa.command(name="status")
    @checks.admin_or_permissions(manage_guild=True)
    async def santa_status(self, ctx):
        """Check the status of a Secret Santa event (admin only).

        Shows all participants and their gift status.

        Example: [p]santa status
        """
        event = await self._get_event(ctx.guild)

        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return

        event_name = event["name"]

        embed = discord.Embed(
            title=f"🎅 Secret Santa Status: {event_name}",
            color=discord.Color.red()
        )
        embed.add_field(name="Target Date", value=event["target_date"], inline=True)
        embed.add_field(name="Max Price", value=event["max_price"], inline=True)
        embed.add_field(name="Matched", value="✅ Yes" if event["matched"] else "❌ No", inline=True)

        # Count statuses
        total = len(event["participants"])
        sent_count = sum(1 for p in event["participants"].values() if p.get("sent_gift"))
        received_count = sum(1 for p in event["participants"].values() if p.get("received_gift"))

        embed.add_field(name="Participants", value=str(total), inline=True)
        embed.add_field(name="Gifts Sent", value=f"{sent_count}/{total}", inline=True)
        embed.add_field(name="Gifts Received", value=f"{received_count}/{total}", inline=True)

        # Participant details
        participant_lines = []
        for user_id_str, data in event["participants"].items():
            user = self.bot.get_user(int(user_id_str))
            name = user.display_name if user else f"User {user_id_str}"
            sent = "✅" if data.get("sent_gift") else "⏳"
            received = "✅" if data.get("received_gift") else "⏳"
            participant_lines.append(f"{name}: Sent {sent} | Received {received}")

        if participant_lines:
            # Split into multiple fields if needed
            participant_text = "\n".join(participant_lines)
            if len(participant_text) <= EMBED_FIELD_MAX_LENGTH:
                embed.add_field(name="Participant Details", value=participant_text, inline=False)
            else:
                # Truncate if too long
                truncate_at = EMBED_FIELD_MAX_LENGTH - 4
                embed.add_field(
                    name="Participant Details",
                    value=participant_text[:truncate_at] + "...",
                    inline=False
                )

        await ctx.send(embed=embed)

    @santa.command(name="delete")
    @checks.admin_or_permissions(manage_guild=True)
    async def santa_delete(self, ctx):
        """Delete a Secret Santa event.

        Example: [p]santa delete
        """
        event = await self._get_event(ctx.guild)
        
        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return

        event_name = event["name"]

        await self.config.guild(ctx.guild).event.set(None)

        await ctx.send(f"🗑️ Event `{event_name}` has been deleted.")

    @santa.command(name="remind")
    @checks.admin_or_permissions(manage_guild=True)
    async def santa_remind(self, ctx):
        """Send reminder DMs to all participants in a Secret Santa event.

        Reminds participants to:
        - Update their wishlist
        - Mark their gift as sent (if not already)
        - Mark their gift as received (if not already)
        - Use anonymous DM messaging

        Example: [p]santa remind
        """
        event = await self._get_event(ctx.guild)
        
        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return
        
        event_name = event["name"]

        target_date = event.get("target_date", "Not specified")
        max_price = event.get("max_price", "Not specified")

        dm_success = 0
        dm_failed = 0

        for user_id_str, participant_data in event["participants"].items():
            user = self.bot.get_user(int(user_id_str))
            if not user:
                dm_failed += 1
                continue

            try:
                embed = discord.Embed(
                    title="🎅 Secret Santa Reminder!",
                    description=f"A friendly reminder about **{event_name}** in **{ctx.guild.name}**!",
                    color=discord.Color.red()
                )
                embed.add_field(name="Target Date", value=target_date, inline=True)
                embed.add_field(name="Max Price", value=max_price, inline=True)

                # Wishlist reminder
                if participant_data.get("wishlist"):
                    embed.add_field(
                        name="📝 Your Wishlist",
                        value=(
                            f"You have a wishlist set! You can update it anytime.\n"
                            f"DM me: `{ctx.prefix}santadm wishlist <your wishlist>`"
                        ),
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="📝 Set Your Wishlist",
                        value=(
                            f"You haven't set a wishlist yet! Help your Santa out.\n"
                            f"DM me: `{ctx.prefix}santadm wishlist <your wishlist>`"
                        ),
                        inline=False
                    )

                # Gift sent reminder (only if matched)
                if event["matched"]:
                    if participant_data.get("sent_gift"):
                        embed.add_field(
                            name="🎁 Gift Sent",
                            value="✅ You've marked your gift as sent!",
                            inline=True
                        )
                    else:
                        embed.add_field(
                            name="🎁 Gift Sent",
                            value=(
                                f"⏳ Don't forget to mark your gift as sent!\n"
                                f"DM me: `{ctx.prefix}santadm sent`"
                            ),
                            inline=True
                        )

                    # Gift received reminder
                    if participant_data.get("received_gift"):
                        embed.add_field(
                            name="🎄 Gift Received",
                            value="✅ You've marked your gift as received!",
                            inline=True
                        )
                    else:
                        embed.add_field(
                            name="🎄 Gift Received",
                            value=(
                                f"⏳ Remember to mark when you receive your gift!\n"
                                f"DM me: `{ctx.prefix}santadm received`"
                            ),
                            inline=True
                        )

                # Anonymous messaging reminder (only if matched)
                if event["matched"]:
                    embed.add_field(
                        name="💬 Anonymous Messaging",
                        value=(
                            f"You can send anonymous messages via DM!\n\n"
                            f"**Message your giftee:**\n"
                            f"`{ctx.prefix}santadm message <your message>`\n\n"
                            f"**Reply to your Santa:**\n"
                            f"`{ctx.prefix}santadm reply <your message>`"
                        ),
                        inline=False
                    )

                embed.set_footer(text="Happy gifting! 🎁")
                await user.send(embed=embed)
                dm_success += 1
            except discord.Forbidden:
                dm_failed += 1

        embed = discord.Embed(
            title="🎅 Reminders Sent!",
            description=f"Reminder DMs have been sent for **{event_name}**.",
            color=discord.Color.green()
        )
        embed.add_field(name="DMs Sent", value=f"{dm_success} ✅", inline=True)
        embed.add_field(name="DMs Failed", value=f"{dm_failed} ❌", inline=True)
        if dm_failed > 0:
            embed.set_footer(text="Some users have DMs disabled or couldn't be found.")

        await ctx.send(embed=embed)

    @santa.command(name="add")
    @checks.admin_or_permissions(manage_guild=True)
    async def santa_add(
        self, 
        ctx, 
        participants: commands.Greedy[
            Union[discord.Member, discord.Role]
        ]):
        """Add participants to an existing event (before matching).

        Parameters
        ----------
        participants : commands.Greedy[Union[discord.Member, discord.Role]]
            Members and/or role containing members to add to the event

        Example: [p]santa add @user1 @user2
                 [p]santa add @SecretSanta @user1
        """
        event = await self._get_event(ctx.guild)
        
        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return
        
        event_name = event["name"]

        if event["matched"]:
            await ctx.send(
                f"Cannot add participants after matching. Use `{ctx.prefix}santa rematch` to reset matching first."
            )
            return

        resolved_participants = self._resolve_participants(participants)

        if not resolved_participants:
            await ctx.send("Please mention at least one member to add.")
            return

        max_price = event.get("max_price", "Not specified")
        target_date = event.get("target_date", "Not specified")

        added = []
        already_in = []
        added_members = []

        for member in resolved_participants:
            user_id_str = str(member.id)
            if user_id_str in event["participants"]:
                already_in.append(member.display_name)
            else:
                event["participants"][user_id_str] = {
                    "matched_to": None,
                    "sent_gift": False,
                    "received_gift": False,
                    "wishlist": None,
                }
                added.append(member.display_name)
                added_members.append(member)
        await self._save_event(ctx.guild, event)

        # Send DMs to newly added members asking for their wishlist
        dm_success = 0
        dm_failed = 0
        for member in added_members:
            try:
                embed = discord.Embed(
                    title="🎅 You've Been Added to a Secret Santa Event!",
                    description=(
                        f"You've been added to **{event_name}** in **{ctx.guild.name}**!"
                    ),
                    color=discord.Color.red()
                )
                embed.add_field(name="Target Date", value=target_date, inline=True)
                embed.add_field(name="Max Price", value=max_price, inline=True)
                embed.add_field(
                    name="📝 Set Your Wishlist",
                    value=(
                        f"Please set your wishlist so your Secret Santa knows what you'd like!\n"
                        f"DM me: `{ctx.prefix}santadm wishlist <your wishlist>`\n\n"
                        f"Example: `{ctx.prefix}santadm wishlist "
                        f"I'd love a book, some chocolates, or a cozy sweater!`"
                    ),
                    inline=False
                )
                embed.add_field(
                    name="💬 Anonymous Messaging",
                    value=(
                        f"After matching, you can send anonymous messages via DM!\n"
                        f"`{ctx.prefix}santadm message <your message>`"
                    ),
                    inline=False
                )
                embed.set_footer(text="Your wishlist will be shared with your Secret Santa after matching!")
                await member.send(embed=embed)
                dm_success += 1
            except discord.Forbidden:
                dm_failed += 1

        msg = ""
        if added:
            msg += f"✅ Added: {', '.join(added)}\n"
            msg += f"📬 DMs sent: {dm_success} ✅ / {dm_failed} ❌\n"
        if already_in:
            msg += f"ℹ️ Already in event: {', '.join(already_in)}"

        await ctx.send(msg or "No changes made.")

    @santa.command(name="remove")
    @checks.admin_or_permissions(manage_guild=True)
    async def santa_remove(self, ctx, members: commands.Greedy[discord.Member]):
        """Remove participants from an existing event (before matching).

        Parameters
        ----------
        members : commands.Greedy[discord.Member]
            Members to remove from the event

        Example: [p]santa remove @user1 @user2
        """
        event = await self._get_event(ctx.guild)
        
        if not event:
            await ctx.send(
                "No Secret Santa event exists."
            )
            return
        
        if event["matched"]:
            await ctx.send(
                f"Cannot remove participants after matching. "
                f"Use `{ctx.prefix}santa rematch` to reset matching first."
            )
            return

        if not members:
            await ctx.send("Please mention at least one member to remove.")
            return

        removed = []
        not_in = []

        for member in members:
            user_id_str = str(member.id)
            if user_id_str in event["participants"]:
                del event["participants"][user_id_str]
                removed.append(member.display_name)
            else:
                not_in.append(member.display_name)
        await self._save_event(ctx.guild, event)

        msg = ""
        if removed:
            msg += f"🗑️ Removed: {', '.join(removed)}\n"
        if not_in:
            msg += f"ℹ️ Not in event: {', '.join(not_in)}"

        await ctx.send(msg or "No changes made.")

    # DM-only commands for anonymity
    @commands.hybrid_group()
    @commands.dm_only()
    async def santadm(self, ctx):
        """Secret Santa DM commands for anonymous messaging.

        These commands can only be used in DMs with the bot to preserve anonymity.
        """

    @santadm.command(name="message")
    async def santadm_message(self, ctx, *, message: str):
        """Send an anonymous message to your Secret Santa giftee (DM only).

        Your identity is kept secret - the bot relays the message.

        Example: [p]santadm message What's your favorite color?
        """
        result = await self._get_user_event(
            ctx.author.id
        )

        if not result:
            await ctx.send(
                "You are not participating in a Secret Santa event."
            )
            return

        guild_id, event = result
        event_name = event["name"]

        if not event["matched"]:
            await ctx.send("This event hasn't been matched yet. Please wait for the matching to complete.")
            return

        user_id_str = str(ctx.author.id)
        if user_id_str not in event["participants"]:
            await ctx.send("You are not a participant in this event.")
            return

        matched_to = event["participants"][user_id_str]["matched_to"]
        if not matched_to:
            await ctx.send("You haven't been matched to anyone yet.")
            return

        recipient = self.bot.get_user(matched_to)
        if not recipient:
            await ctx.send("Could not find your giftee. They may have left the server.")
            return

        guild = self.bot.get_guild(guild_id)
        guild_name = guild.name if guild else "Unknown Server"

        try:
            embed = discord.Embed(
                title="🎅 Anonymous Secret Santa Message!",
                description=message,
                color=discord.Color.red()
            )
            embed.add_field(name="Event", value=event_name, inline=True)
            embed.add_field(name="Server", value=guild_name, inline=True)
            embed.add_field(
                name="Reply",
                value=f"Reply anonymously via DM: `{ctx.prefix}santadm reply <message>`",
                inline=False
            )
            embed.set_footer(text="This is from your Secret Santa! 🎁")
            await recipient.send(embed=embed)

            await ctx.send("✅ Your message to your Secret Santa giftee was sent successfully!")

        except discord.Forbidden:
            await ctx.send("Could not send message to your giftee. They may have DMs disabled.")

    @santadm.command(name="reply")
    async def santadm_reply(self, ctx, *, message: str):
        """Send an anonymous reply to your Secret Santa (DM only).

        This allows you to respond to questions from your Secret Santa.

        Example: [p]santadm reply My favorite color is blue!
        """
        result = await self._get_user_event(
            ctx.author.id
        )
        
        if not result:
            await ctx.send(
                "You are not participating in a Secret Santa event."
            )
            return
        
        guild_id, event = result
        event_name = event["name"]

        if not event["matched"]:
            await ctx.send("This event hasn't been matched yet.")
            return

        user_id_str = str(ctx.author.id)
        if user_id_str not in event["participants"]:
            await ctx.send("You are not a participant in this event.")
            return

        # Find who is giving a gift to this user
        santa_id = None
        for giver_id, data in event["participants"].items():
            if data["matched_to"] == ctx.author.id:
                santa_id = int(giver_id)
                break

        if not santa_id:
            await ctx.send("Could not find your Secret Santa. This might be a configuration error.")
            return

        santa = self.bot.get_user(santa_id)
        if not santa:
            await ctx.send("Could not find your Secret Santa. They may have left the server.")
            return

        guild = self.bot.get_guild(guild_id)
        guild_name = guild.name if guild else "Unknown Server"

        try:
            embed = discord.Embed(
                title="🎁 Reply from Your Giftee!",
                description=message,
                color=discord.Color.green()
            )
            embed.add_field(name="Event", value=event_name, inline=True)
            embed.add_field(name="Server", value=guild_name, inline=True)
            embed.set_footer(text="This is from the person you're buying a gift for! 🎄")
            await santa.send(embed=embed)

            await ctx.send("✅ Your reply to your Secret Santa was sent successfully!")

        except discord.Forbidden:
            await ctx.send("Could not send reply to your Secret Santa. They may have DMs disabled.")

    @santadm.command(name="wishlist")
    async def santadm_wishlist(self, ctx, *, wishlist: str):
        """Set your wishlist for a Secret Santa event (DM only).

        Your wishlist will be shared with your Secret Santa when matching occurs.
        If matching already happened, your Santa will be notified of the update.

        Example: [p]santadm wishlist I'd love a book, some chocolates, or a cozy sweater!
        """
        result = await self._get_user_event(
            ctx.author.id
        )
        
        if not result:
            await ctx.send(
                "You are not participating in a Secret Santa event."
            )
            return
        
        guild_id, event = result
        event_name = event["name"]

        user_id_str = str(ctx.author.id)
        if user_id_str not in event["participants"]:
            await ctx.send("You are not a participant in this event.")
            return

        # Update the wishlist
        event["participants"][user_id_str]["wishlist"] = wishlist
        await self._save_event(guild_id, event)

        guild = self.bot.get_guild(guild_id)
        guild_name = guild.name if guild else "Unknown Server"

        await ctx.send(
            f"✅ Your wishlist for **{event_name}** in **{guild_name}** has been saved!\n\n"
            f"**Your wishlist:**\n{wishlist}"
        )

        # If the event is already matched, notify the Santa of the wishlist update
        if event["matched"]:
            # Find who is giving a gift to this user
            santa_id = None
            for giver_id, data in event["participants"].items():
                if data["matched_to"] == ctx.author.id:
                    santa_id = int(giver_id)
                    break

            if santa_id:
                santa = self.bot.get_user(santa_id)
                if santa:
                    try:
                        embed = discord.Embed(
                            title="📝 Your Giftee Updated Their Wishlist!",
                            description="Your giftee has updated their wishlist.",
                            color=discord.Color.blue()
                        )
                        embed.add_field(name="Event", value=event_name, inline=True)
                        embed.add_field(name="Server", value=guild_name, inline=True)
                        embed.add_field(
                            name="🎁 Updated Wishlist",
                            value=wishlist[:EMBED_FIELD_MAX_LENGTH],
                            inline=False
                        )
                        embed.set_footer(text="Use this information to pick the perfect gift! 🎄")
                        await santa.send(embed=embed)
                    except discord.Forbidden:
                        log.debug(
                            "Failed to DM Santa %s about wishlist update for event %s",
                            santa_id, event_name
                        )

    @santadm.command(name="info")
    async def santadm_info(self, ctx):
        """Get information about your Secret Santa event (DM only).

        Shows your assignment, wishlist, and event details.

        Example: [p]santadm info
        """
        result = await self._get_user_event(
            ctx.author.id
        )
        
        if not result:
            await ctx.send(
                "You are not participating in a Secret Santa event."
            )
            return
        
        guild_id, event = result
        event_name = event["name"]

        user_id_str = str(ctx.author.id)
        if user_id_str not in event["participants"]:
            await ctx.send("You are not a participant in this event.")
            return

        guild = self.bot.get_guild(guild_id)
        guild_name = guild.name if guild else "Unknown Server"

        participant_data = event["participants"][user_id_str]

        embed = discord.Embed(
            title="🎅 Your Secret Santa Info",
            description=f"Event **{event_name}** in **{guild_name}**",
            color=discord.Color.red()
        )
        embed.add_field(name="Target Date", value=event.get("target_date", "Not set"), inline=True)
        embed.add_field(name="Max Price", value=event.get("max_price", "Not set"), inline=True)

        if event["matched"]:
            matched_to = participant_data.get("matched_to")
            if matched_to:
                recipient = self.bot.get_user(matched_to)
                giftee_name = recipient.display_name if recipient else f"User {matched_to}"
                embed.add_field(name="Your Giftee", value=giftee_name, inline=True)

                # Get the recipient's wishlist
                recipient_data = event["participants"].get(str(matched_to), {})
                recipient_wishlist = recipient_data.get("wishlist")
                if recipient_wishlist:
                    embed.add_field(
                        name="🎁 Your Giftee's Wishlist",
                        value=recipient_wishlist[:EMBED_FIELD_MAX_LENGTH],
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="🎁 Your Giftee's Wishlist",
                        value="No wishlist set yet.",
                        inline=False
                    )
        else:
            embed.add_field(name="Status", value="⏳ Not matched yet", inline=True)

        # Show user's own wishlist
        my_wishlist = participant_data.get("wishlist")
        if my_wishlist:
            embed.add_field(
                name="📝 Your Wishlist",
                value=my_wishlist[:EMBED_FIELD_MAX_LENGTH],
                inline=False
            )
        else:
            embed.add_field(
                name="📝 Your Wishlist",
                value=f"Not set. Use `{ctx.prefix}santadm wishlist <your wishlist>` to set it!",
                inline=False
            )

        embed.add_field(
            name="Gift Status",
            value="✅ Sent" if participant_data.get("sent_gift") else "⏳ Not yet sent",
            inline=True
        )
        embed.add_field(
            name="Received",
            value="✅ Yes" if participant_data.get("received_gift") else "⏳ Not yet",
            inline=True
        )

        embed.set_footer(text="Keep it a secret! 🤫")
        await ctx.send(embed=embed)

    @santadm.command(name="sent")
    async def santadm_sent(self, ctx):
        """Mark that you have sent your gift (DM only).

        Example: [p]santadm sent
        """
        result = await self._get_user_event(
            ctx.author.id
        )
        
        if not result:
            await ctx.send(
                "You are not participating in a Secret Santa event."
            )
            return
        
        guild_id, event = result

        user_id_str = str(ctx.author.id)
        if user_id_str not in event["participants"]:
            await ctx.send("You are not a participant in this event.")
            return

        event["participants"][user_id_str]["sent_gift"] = True
        await self._save_event(guild_id, event)

        await ctx.send("🎁 You've marked your gift as **sent**! Thank you!")

    @santadm.command(name="received")
    async def santadm_received(self, ctx):
        """Mark that you have received your gift (DM only).

        Example: [p]santadm received
        """
        result = await self._get_user_event(
            ctx.author.id
        )
        
        if not result:
            await ctx.send(
                "You are not participating in a Secret Santa event."
            )
            return
        
        guild_id, event = result

        user_id_str = str(ctx.author.id)
        if user_id_str not in event["participants"]:
            await ctx.send("You are not a participant in this event.")
            return

        event["participants"][user_id_str]["received_gift"] = True
        await self._save_event(guild_id, event)

        await ctx.send("🎄 You've marked your gift as **received**! Enjoy your present!")
