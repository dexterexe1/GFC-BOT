"""Simple command directory commands for GFC Bot.

?commands      -> categorized list of all registered command names
?commandsinfo  -> flat list of every registered prefix/slash command name

Both are hybrid commands, so /commands and /commandsinfo also work.
"""
import discord
from discord.ext import commands

from bot.config import bot, style_embed, BRAND_COLOR, BRAND_EMOJI


def _all_command_names():
    """Return every registered prefix and slash command name, deduplicated."""
    names = set()

    for command in bot.walk_commands():
        if getattr(command, "hidden", False):
            continue
        name = getattr(command, "qualified_name", None) or getattr(command, "name", None)
        if name:
            names.add(name)

    try:
        for command in bot.tree.walk_commands():
            name = getattr(command, "qualified_name", None) or getattr(command, "name", None)
            if name:
                names.add(name)
    except Exception:
        pass

    return sorted(names, key=lambda value: value.lower())


def _category_for(command_name: str) -> str:
    root = command_name.split(" ", 1)[0].lower()
    mapping = {
        "ban": "🛡️ Moderation", "kick": "🛡️ Moderation", "timeout": "🛡️ Moderation",
        "warn": "🛡️ Moderation", "mute": "🛡️ Moderation", "unmute": "🛡️ Moderation",
        "purge": "🛡️ Moderation", "slowmode": "🛡️ Moderation", "mod": "🛡️ Moderation",
        "addrole": "🎭 Roles", "role": "🎭 Roles", "roles": "🎭 Roles",
        "roleinfo": "🎭 Roles", "rolefullinfo": "🎭 Roles", "rolehelp": "🎭 Roles",
        "revenue": "💰 Revenue", "setrevenuechannel": "💰 Revenue",
        "clearrevenuechannel": "💰 Revenue", "weekrevenue": "💰 Revenue",
        "monthrevenue": "💰 Revenue", "todayrevenue": "💰 Revenue",
        "allrevenue": "💰 Revenue", "revenuedetails": "💰 Revenue",
        "revenuevia": "💰 Revenue", "revenuehelp": "💰 Revenue",
        "vouch": "✅ Vouch", "unvouch": "✅ Vouch", "vouches": "✅ Vouch",
        "vouchleaderboard": "✅ Vouch", "setvouchchannel": "✅ Vouch",
        "clearvouchchannel": "✅ Vouch",
        "owneronlymode": "👑 Developer", "lockbot": "👑 Developer", "devhelp": "👑 Developer",
        "developerhelp": "👑 Developer", "devcommands": "👑 Developer",
        "disablecommand": "👑 Developer", "disablecmd": "👑 Developer",
        "enablecommand": "👑 Developer", "enablecmd": "👑 Developer",
        "disabledcommands": "👑 Developer", "listdisabled": "👑 Developer",
        "togglenoprefix": "👑 Developer", "noprefixmode": "👑 Developer",
        "botstatus": "👑 Developer", "botinfo": "👑 Developer",
        "commands": "📚 General", "commandsinfo": "📚 General",
        "help": "📚 General", "ping": "📚 General", "serverinfo": "📚 General",
        "ai": "🤖 AI Manager", "aihelp": "🤖 AI Manager", "aiimportprice": "🤖 AI Manager",
        "aiimportrules": "🤖 AI Manager", "aiprice": "🤖 AI Manager", "airule": "🤖 AI Manager",
        "aiservice": "🤖 AI Manager", "aiconfig": "🤖 AI Manager", "aiclear": "🤖 AI Manager",
        "provideai": "👑 Developer", "disableai": "👑 Developer",
        "providenonprefix": "👑 Developer", "disablenonprefix": "👑 Developer",
        "aistatus": "👑 Developer", "ailist": "👑 Developer",
    }
    return mapping.get(root, "📦 Other")


def _chunk_lines(lines, max_chars=950):
    chunks, current, size = [], [], 0
    for line in lines:
        if current and size + len(line) + 1 > max_chars:
            chunks.append("\n".join(current))
            current, size = [], 0
        current.append(line)
        size += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks or ["No commands found."]


@bot.hybrid_command(
    name="commands",
    description="Show the bot's command names grouped by category.",
)
async def commands_list(ctx: commands.Context):
    try:
        names = _all_command_names()
        categories = {}
        for name in names:
            categories.setdefault(_category_for(name), []).append(name)

        fields = []
        for category in sorted(categories, key=lambda x: x.lower()):
            value = "\n".join(f"• `{name}`" for name in categories[category])
            parts = _chunk_lines(value.splitlines(), 950)
            for index, part in enumerate(parts):
                field_name = category if index == 0 else f"{category} (continued)"
                fields.append((field_name, part))

        pages = [fields[i : i + 20] for i in range(0, max(len(fields), 1), 20)] or [[]]
        for page_i, page_fields in enumerate(pages, start=1):
            desc = "Registered command names."
            if len(pages) > 1:
                desc += f" (page {page_i}/{len(pages)})"
            embed = style_embed(
                title=f"{BRAND_EMOJI} GFC Bot Commands",
                description=desc,
                kind="info",
            )
            for field_name, part in page_fields:
                embed.add_field(name=field_name, value=part or "—", inline=False)
            embed.set_footer(text=f"{len(names)} commands • GFC Bot")
            await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ commands error: `{e}`")


@bot.hybrid_command(
    name="commandsinfo",
    description="Show every registered command name in the bot.",
)
async def commands_info(ctx: commands.Context):
    try:
        names = _all_command_names()
        lines = [f"• `{name}`" for name in names]
        chunks = _chunk_lines(lines, 3500)
        for index, chunk in enumerate(chunks, start=1):
            title = (
                f"{BRAND_EMOJI} All Commands"
                if len(chunks) == 1
                else f"{BRAND_EMOJI} All Commands • {index}/{len(chunks)}"
            )
            embed = style_embed(
                title=title,
                description=chunk or "No commands found.",
                kind="info",
            )
            embed.set_footer(text=f"{len(names)} commands • GFC Bot")
            await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ commandsinfo error: `{e}`")
