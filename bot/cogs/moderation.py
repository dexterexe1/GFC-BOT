from bot.ui.premium_cards import quick_card_view, style_card_view, embed_to_view
"""
moderation.py — Real moderation tools (prefix).
?bon (joke ban) removed by request.
"""
import discord
from discord.ext import commands
import discord.app_commands as app_commands
import datetime

from bot.config import bot, style_embed, style_embed, staff_check, is_staff, UTC, EMOJI_BULLET
from bot.database import (
    get_warnings, update_warnings, reset_warnings,
    add_warn_log, get_warn_logs, clear_warn_logs,
)

# ==========================================
#         🔨 REAL MODERATION TOOLS
# ==========================================
# These stay PREFIX-ONLY on purpose: /mod warn, /mod ban, /mod kick, etc.
# already provide slash-command equivalents.

@bot.command(name="warn", aliases=["w"])
@staff_check("mod")
async def warn_prefix(ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
    if member is None:
        await ctx.send(view=quick_card_view("❌ Syntax: `?warn @user [reason]`"))
        return
    # Unlimited warnings — always recorded in DB (no auto-timeout / no 3-strike cap)
    current = update_warnings(member.id, 1)
    add_warn_log(ctx.guild.id, member.id, ctx.author.id, reason)
    view = style_card_view(
        "Warning Issued",
        kind="warn",
        description=(
            f"{EMOJI_BULLET} user: {member.mention}\n"
            f"{EMOJI_BULLET} moderator: {ctx.author.mention}\n"
            f"{EMOJI_BULLET} warnings: **{current}** (unlimited)\n"
            f"{EMOJI_BULLET} reason: {reason}"
        ),
        footer=f"ID: {member.id}",
    )
    await ctx.send(view=view)

@bot.command(name="warnings", aliases=["warns"])
async def warnings_prefix(ctx, member: discord.Member = None):
    member = member or ctx.author
    count = get_warnings(member.id)
    logs = get_warn_logs(ctx.guild.id, member.id, limit=5)
    lines = [f"{EMOJI_BULLET} user: {member.mention}", f"{EMOJI_BULLET} total warnings: **{count}**"]
    if logs:
        lines.append(f"{EMOJI_BULLET} recent:")
        for mod_id, reason, created in logs:
            lines.append(f"  › <@{mod_id}> — {reason} ({created})")
    view = style_card_view(
        "Warnings",
        kind="info",
        description="\n".join(lines),
        footer=f"ID: {member.id}",
    )
    await ctx.send(view=view)

@bot.command(name="clearwarnings", aliases=["cw", "clearwarns"])
@staff_check("mod")
async def clearwarnings_prefix(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send(view=quick_card_view("❌ Syntax: `?clearwarnings @user`"))
        return
    reset_warnings(member.id)
    clear_warn_logs(ctx.guild.id, member.id)
    view = style_card_view(
        "Warnings Cleared",
        kind="success",
        description=f"{EMOJI_BULLET} user: {member.mention}\n{EMOJI_BULLET} warnings: **0** (cleared)",
        footer=f"ID: {member.id}",
    )
    await ctx.send(view=view)

@bot.command(name="mute", aliases=["timeout"])
@staff_check("mod")
async def mute_prefix(ctx, member: discord.Member = None, minutes: int = 10, *, reason: str = "No reason provided"):
    if member is None:
        await ctx.send(view=quick_card_view("❌ Syntax: `?mute @user [minutes] [reason]`"))
        return
    minutes = max(1, min(40320, minutes))  # Discord's timeout cap is 28 days
    try:
        await member.timeout(datetime.timedelta(minutes=minutes), reason=f"{reason} (by {ctx.author})")
    except discord.Forbidden:
        await ctx.send(view=quick_card_view("❌ I don't have permission to timeout that user (check role hierarchy)."))
        return
    view = style_card_view(
        "Member Timed Out",
        kind="mod",
        description=(
            f"{EMOJI_BULLET} user: {member.mention}\n"
            f"{EMOJI_BULLET} duration: **{minutes}** min\n"
            f"{EMOJI_BULLET} moderator: {ctx.author.mention}\n"
            f"{EMOJI_BULLET} reason: {reason}"
        ),
        footer=f"ID: {member.id}",
    )
    await ctx.send(view=view)

@bot.command(name="unmute", aliases=["untimeout"])
@staff_check("mod")
async def unmute_prefix(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send(view=quick_card_view("❌ Syntax: `?unmute @user`"))
        return
    try:
        await member.timeout(None, reason=f"Unmuted by {ctx.author}")
    except discord.Forbidden:
        await ctx.send(view=quick_card_view("❌ I don't have permission to unmute that user."))
        return
    view = style_card_view(
        "Member Unmuted",
        kind="success",
        description=f"{EMOJI_BULLET} user: {member.mention}\n{EMOJI_BULLET} moderator: {ctx.author.mention}",
        footer=f"ID: {member.id}",
    )
    await ctx.send(view=view)

@bot.command(name="kick", aliases=["k"])
@staff_check("kick")
async def kick_prefix(ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
    if member is None:
        await ctx.send(view=quick_card_view("❌ Syntax: `?kick @user [reason]`"))
        return
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        await ctx.send(view=quick_card_view("❌ You can't kick someone with an equal or higher role than you."))
        return
    try:
        await member.kick(reason=f"{reason} (by {ctx.author})")
    except discord.Forbidden:
        await ctx.send(view=quick_card_view("❌ I don't have permission to kick that user (check role hierarchy)."))
        return
    view = style_card_view(
        "Member Kicked",
        kind="mod",
        description=(
            f"{EMOJI_BULLET} user: **{member}**\n"
            f"{EMOJI_BULLET} moderator: {ctx.author.mention}\n"
            f"{EMOJI_BULLET} reason: {reason}"
        ),
        footer=f"ID: {member.id}",
    )
    await ctx.send(view=view)

@bot.command(name="ban", aliases=["b"])
@staff_check("ban")
async def ban_prefix(ctx, member: discord.Member = None, *, reason: str = "No reason provided"):
    if member is None:
        await ctx.send(view=quick_card_view("❌ Syntax: `?ban @user [reason]`"))
        return
        
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        await ctx.send(view=quick_card_view("❌ You can't ban someone with an equal or higher role than you."))
        return
        
    try:
        await member.ban(reason=f"{reason} (by {ctx.author})")
    except discord.Forbidden:
        await ctx.send(view=quick_card_view("❌ I don't have permission to ban that user (check role hierarchy)."))
        return
        
    view = style_card_view(
        "Member Banned",
        kind="error",
        description=(
            f"{EMOJI_BULLET} user: **{member}**\n"
            f"{EMOJI_BULLET} moderator: {ctx.author.mention}\n"
            f"{EMOJI_BULLET} reason: {reason}"
        ),
        footer=f"ID: {member.id}",
    )
    await ctx.send(view=view)

@bot.command(name="unban", aliases=["ub"])
@staff_check("ban")
async def unban_prefix(ctx, user_id: int = None, *, reason: str = "No reason provided"):
    if user_id is None:
        await ctx.send(view=quick_card_view("❌ Syntax: `?unban <user_id> [reason]`"))
        return
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=f"{reason} (by {ctx.author})")
    except discord.NotFound:
        await ctx.send(view=quick_card_view("❌ That user isn't banned."))
        return
    except discord.Forbidden:
        await ctx.send(view=quick_card_view("❌ I don't have permission to unban."))
        return
    view = style_card_view(
        "Member Unbanned",
        kind="success",
        description=f"{EMOJI_BULLET} user: **{user}**\n{EMOJI_BULLET} moderator: {ctx.author.mention}",
        footer=f"ID: {user.id}",
    )
    await ctx.send(view=view)


