"""
community.py — Help menu, control panel, setup dropdowns, announcements, leveling cmds, dashboard links, no-prefix helpers.
Extracted from the original monolithic bot.py. Logic unchanged.
"""
from bot.ui.premium_cards import quick_card_view, style_card_view, fun_card_view, embed_to_view
import discord
from discord.ext import commands
import discord.app_commands as app_commands
import datetime
import asyncio
import random
import re
import requests

from bot.config import (
    bot, style_embed, style_embed, UTC, BRAND_COLOR,
    afk_users,
    SUPPORT_SERVER_URL, DASHBOARD_URL, INVITE_URL, GIPHY_API_KEY, fetch_giphy_gif_url,
    has_required_slash_role, mod_group, LEVELING_SYSTEM_ENABLED, EMOJI_BULLET, staff_check,
)
from bot.database import (
    get_level_data, add_xp, level_leaderboard, xp_for_level,
    is_leveling_enabled, get_levelup_channel,
    get_all_role_menu_message_ids, get_role_menu_items,
    has_noprefix_perm, get_trusted_role_id, list_noprefix_users,
    set_config, get_config, add_vouch, count_vouches,
)


# --- HELPERS (kept for applications / other cogs) ---
def make_progress_bar(current: int, needed: int, length: int = 15) -> str:
    filled = round(length * min(current / needed, 1.0)) if needed else 0
    return "█" * filled + "░" * (length - filled)


# Leveling commands (?rank, ?levelleaderboard), ?dashboard removed by request.


# --- ANNOUNCE ?p ---
# ==========================================
#      📢 AESTHETIC TEXT & IMAGE ?P COMMAND
# ==========================================

@bot.hybrid_command(name="p", description="[Staff] Post a custom formatted announcement embed")
@staff_check("admin")
@app_commands.describe(text="Announcement text. Use [IMAGE] <url>, [SECTION] or [FIELD] to structure it")
async def p_prefix(ctx, *, text: str):
    try:
        if ctx.message:
            await ctx.message.delete()
    except Exception: pass

    image_urls = re.findall(r'\[IMAGE\]\s*([^\s]+)', text)
    cleaned_text = re.sub(r'\[IMAGE\]\s*[^\s]+', '', text).strip()

    if not image_urls:
        image_urls = ["https://cdn.discordapp.com/attachments/1126581404164100147/1319747806143058012/united_bunnies.png"]

    embeds = []
    if "[SECTION]" in cleaned_text:
        parts = cleaned_text.split("[SECTION]")
        main_desc = parts[0].strip()
        main_embed = discord.Embed(title="⚡ ── 𝐕𝐎𝐑𝐓𝐄𝐗 ── ⚡", description=main_desc, color=0x8B5CF6, timestamp=datetime.datetime.now(UTC))
        for part in parts[1:]:
            part = part.strip()
            if not part: continue
            lines = part.split("\n", 1)
            main_embed.add_field(name=f"⚡ ─── {lines[0].strip().upper()} ─── ⚡", value=lines[1].strip() if len(lines) > 1 else "...", inline=False)
    else:
        parts = cleaned_text.split("[FIELD]")
        main_desc = parts[0].strip()
        main_embed = discord.Embed(title="⚡ ── 𝐕𝐎𝐑𝐓𝐄𝐗 ── ⚡", description=main_desc, color=0x8B5CF6, timestamp=datetime.datetime.now(UTC))
        for part in parts[1:]:
            part = part.strip()
            if not part: continue
            lines = part.split('\n', 1)
            main_embed.add_field(name=lines[0].strip(), value=lines[1].strip() if len(lines) > 1 else "...", inline=False)

    main_embed.set_footer(text="🐰 United Bunnies System Active ✨")
    main_embed.set_image(url=image_urls[0])
    embeds.append(main_embed)

    for extra_url in image_urls[1:4]:
        extra_embed = discord.Embed(color=0x2f3136)
        extra_embed.set_image(url=extra_url)
        embeds.append(extra_embed)

    await ctx.send(embeds=embeds)


# --- CONTROL PANEL ---
# ==========================================
#         🕹️ INTERACTIVE CONTROL PANEL
# ==========================================
# A single persistent embed with buttons that ties together tickets,
# vouching, server info, and music into one place — so members don't
# need to remember every command.

class VouchModal(discord.ui.Modal, title="Vouch for a Member"):
    user_input = discord.ui.TextInput(
        label="User ID or @mention",
        placeholder="e.g. 123456789012345678 or paste their mention",
        required=True,
    )
    comment_input = discord.ui.TextInput(
        label="Comment (optional)",
        placeholder="What was it for?",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.user_input.value.strip()
        match = re.search(r"\d{15,25}", raw)
        if not match:
            await interaction.response.send_message(view=quick_card_view("❌ Couldn't find a valid user ID or mention in that."), ephemeral=True)
            return

        target_id = int(match.group())
        target = interaction.guild.get_member(target_id)
        if target is None:
            await interaction.response.send_message(view=quick_card_view("❌ Couldn't find that member in this server."), ephemeral=True)
            return
        if target.id == interaction.user.id:
            await interaction.response.send_message(view=quick_card_view("❌ You can't vouch for yourself."), ephemeral=True)
            return
        if target.bot:
            await interaction.response.send_message(view=quick_card_view("❌ You can't vouch for a bot."), ephemeral=True)
            return

        comment = self.comment_input.value.strip() or None
        add_vouch(interaction.guild.id, target.id, interaction.user.id, comment)
        total = count_vouches(interaction.guild.id, target.id)

        embed = discord.Embed(
            description=f"✅ {interaction.user.mention} vouched for {target.mention}",
            color=discord.Color.green(),
        )
        if comment:
            embed.add_field(name="Comment", value=comment, inline=False)
        embed.set_footer(text=f"{target.display_name} now has {total} vouch(es)")
        await interaction.response.send_message(view=embed_to_view(embed))


# --- SETUP DROPDOWNS ---

# ==========================================
#         ⚙️ COMMUNITY HELP MENU STRUCTURE
# ==========================================

HELP_CATEGORIES = {
    "general": {
        "label": "General",
        "emoji": "📚",
        "title": "📚 General",
        "description": "__**Staff/mod only** on allowed servers.__",
        "fields": [
            ("ℹ️ Basics", (
                "`?help` — This menu.\n"
                "`?ping` — Bot latency.\n"
                "`?serverinfo` / `?si` — Server info.\n"
                "`?commands` / `?commandsinfo` — Raw command name lists.\n"
                "`?p <text>` — Staff: post announcement embed."
            )),
        ],
    },
    "mod": {
        "label": "Moderation",
        "emoji": "🔨",
        "title": "🔨 Moderation",
        "description": "__**Staff only.**__ Prefix **or** `/mod` slash versions.",
        "fields": [
            ("⚔️ Enforcement", (
                "`?warn` / `?w` `@user [reason]`\n"
                "`?warnings` / `?warns` `[@user]`\n"
                "`?clearwarnings` / `?cw` `@user`\n"
                "`?mute` / `?timeout` `@user [mins] [reason]`\n"
                "`?unmute` / `?untimeout` `@user`\n"
                "`?kick` / `?k` `@user [reason]`\n"
                "`?ban` / `?b` `@user [reason]`\n"
                "`?unban` / `?ub` `<user_id>`"
            )),
            ("⚙️ `/mod` setup", (
                "`/mod setup` · `/mod panel` · `/mod clear <amount>`\n"
                "`/mod setwelcome` · `/mod setlogs` · `/mod setwelcomemessage`\n"
                "`/mod warn` · `/mod mute` · `/mod kick` · `/mod ban`"
            )),
        ],
    },
    "vouch": {
        "label": "Vouch",
        "emoji": "✅",
        "title": "✅ Vouch System",
        "description": "__**Vouch for trusted members.**__",
        "fields": [
            ("✅ Commands", (
                "`?vouch @user [reason]`\n"
                "`?unvouch @user`\n"
                "`?vouches` / `?vouchlist` `[@user]`\n"
                "`?vouchleaderboard` / `?vouchlb`\n"
                "`?setvouchchannel` / `?setvouch` — set channel\n"
                "`?clearvouchchannel` / `?clearvouch`"
            )),
        ],
    },
    "revenue": {
        "label": "Revenue",
        "emoji": "💰",
        "title": "💰 Revenue",
        "description": "__**Track sales / staff revenue.**__ Post in the revenue channel, then use reports.",
        "fields": [
            ("📊 Reports", (
                "`?todayrevenue` / `?today`\n"
                "`?weekrevenue` / `?week`\n"
                "`?monthrevenue` / `?month`\n"
                "`?allrevenue` / `?totalrevenue`\n"
                "`?revenuedetails` / `?revdetails`\n"
                "`?revenuevia` / `?revvia` `<staff>`\n"
                "`?revenuehelp` / `?revhelp`"
            )),
            ("⚙️ Setup", (
                "`?setrevenuechannel` `#channel`\n"
                "`?clearrevenuechannel`\n"
                "`?clearrevenue` — wipe history (admin)\n"
                "`?makerevenuemanager` — owner tools\n"
                "`?refreshbloxvalues` — refresh value cache"
            )),
        ],
    },
    "roles": {
        "label": "Roles",
        "emoji": "🎭",
        "title": "🎭 Roles",
        "description": "__**Staff role tools.**__",
        "fields": [
            ("🎭 Commands", (
                "`?roles` — list roles\n"
                "`?roleinfo [@role]` — key perms\n"
                "`?rolefullinfo @role` — full details\n"
                "`?rolehelp`\n"
                "`?addrole <name>` — create a role"
            )),
        ],
    },
    "ai": {
        "label": "AI Manager",
        "emoji": "🤖",
        "title": "🤖 AI Manager",
        "description": "__**Premium AI (owner enables per server).**__",
        "fields": [
            ("🤖 Use", (
                "`?ai <question>` · `?aihelp`\n"
                "`?aiprice` / `?airule` / `?aiservice`\n"
                "`?aiimportprice` · `?aiimportrules`\n"
                "`?aiconfig` · `?aiclear`"
            )),
            ("👑 Owner", (
                "`?provideai` · `?disableai`\n"
                "`?providenonprefix` · `?disablenonprefix`\n"
                "`?aistatus` · `?ailist` · `?aitest`"
            )),
        ],
    },
    "custom": {
        "label": "Custom & Perms",
        "emoji": "🔐",
        "title": "🔐 Permissions & Custom",
        "description": "__**Staff tools.**__",
        "fields": [
            ("🔐 Command perms", (
                "`/cmdperm-allow` · `/cmdperm-deny`\n"
                "`/cmdperm-list` · `/cmdperm-reset`"
            )),
            ("💬 Auto-replies", (
                "`/new-command` · `/delete-command` · `/list-commands`"
            )),
            ("🔒 Toggle", (
                "`?disable` / `?enable` <name>\n"
                "`?disablecommand` / `?enablecommand`\n"
                "`?disabledcommands`"
            )),
        ],
    },
    "owner": {
        "label": "Owner / Dev",
        "emoji": "👑",
        "title": "👑 Owner & Bot Control",
        "description": "__**Bot owners only for most of these.**__",
        "fields": [
            ("👑 Control", (
                "`?botstatus` / `?botinfo`\n"
                "`?owneronlymode` / `?lockbot`\n"
                "`?togglenoprefix` / `?noprefixmode` — staff/mod can toggle\n"
                "`?devhelp` / `?developerhelp`"
            )),
        ],
    },
}


HELP_HOME_TITLE = "🔒 ── GFC BOT (STAFF / MOD) ── 🔒"
HELP_HOME_DESCRIPTION = (
    "__**Private staff & mod command center.**__\n"
    "Only works on allowed servers. Staff/mod only.\n"
    "Pick a category below — Vouch, Revenue, Mod, Roles, AI, etc.\n\n"
    "Prefix `?` or `/slash` where available."
)


def build_help_home_embed() -> discord.Embed:
    embed = discord.Embed(
        title=HELP_HOME_TITLE,
        description=HELP_HOME_DESCRIPTION,
        color=BRAND_COLOR,
        timestamp=datetime.datetime.now(UTC),
    )
    category_list = "\n".join(f"{c['emoji']} **{c['label']}**" for c in HELP_CATEGORIES.values())
    embed.add_field(name="📂 Categories", value=category_list, inline=False)
    embed.set_footer(text="GFC Bot • Staff/mod only • Allowed servers")
    return embed


def build_help_category_embed(key: str) -> discord.Embed:
    cat = HELP_CATEGORIES[key]
    embed = discord.Embed(
        title=cat["title"],
        description=cat["description"],
        color=BRAND_COLOR,
        timestamp=datetime.datetime.now(UTC),
    )
    for name, value in cat["fields"]:
        embed.add_field(name=f"__**{name}**__", value=value, inline=False)
    embed.set_footer(text="United Bunnies • Use the menu below to browse other categories")
    return embed


class HelpCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=cat["label"], value=key, emoji=cat["emoji"])
            for key, cat in HELP_CATEGORIES.items()
        ]
        super().__init__(placeholder="📂 Select a command category…", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        embed = build_help_category_embed(key)
        await interaction.response.edit_message(embed=embed, view=HelpView())


class HelpHomeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Home", emoji="🏠", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction):
        embed = build_help_home_embed()
        await interaction.response.edit_message(embed=embed, view=HelpView())


class HelpView(discord.ui.View):
    """Persistent help menu: category dropdown + Home/Support/Dashboard buttons."""
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpCategorySelect())
        self.add_item(HelpHomeButton())
        self.add_item(discord.ui.Button(label="Support", emoji="🛟", style=discord.ButtonStyle.link, url=SUPPORT_SERVER_URL, row=1))
        self.add_item(discord.ui.Button(label="Dashboard", emoji="📊", style=discord.ButtonStyle.link, url=DASHBOARD_URL, row=1))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


@bot.hybrid_command(name="help", description="Show the command list")
async def help_prefix(ctx):
    embed = build_help_home_embed()
    await ctx.send(embed=embed, view=HelpView())



@bot.hybrid_command(name="ping", description="Check the bot's latency")
async def ping_prefix(ctx):
    await ctx.send(view=style_card_view(
        "Ping",
        kind="info",
        description=f"{EMOJI_BULLET} latency: **{round(bot.latency * 1000)}ms**",
    ))


@bot.hybrid_command(name="serverinfo", aliases=["si", "guildinfo"], description="Show info about this server")
async def serverinfo_prefix(ctx):
    g = ctx.guild
    if g is None:
        await ctx.send(view=quick_card_view("❌ Server only."))
        return
    owner = g.owner.mention if g.owner else "Unknown"
    created = discord.utils.format_dt(g.created_at, style="R") if g.created_at else "Unknown"
    embed = discord.Embed(
        title=f"📡 {g.name}",
        color=BRAND_COLOR,
        timestamp=datetime.datetime.now(UTC),
    )
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="Owner", value=owner, inline=True)
    embed.add_field(name="Members", value=str(g.member_count), inline=True)
    embed.add_field(name="Channels", value=str(len(g.channels)), inline=True)
    embed.add_field(name="Roles", value=str(len(g.roles)), inline=True)
    embed.add_field(name="Boosts", value=str(g.premium_subscription_count or 0), inline=True)
    embed.add_field(name="Created", value=created, inline=True)
    embed.set_footer(text=f"ID: {g.id}")
    await ctx.send(embed=embed)

# Fun commands removed by request.


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRole) or isinstance(error, commands.MissingPermissions):
        await ctx.send(view=quick_card_view("❌ You don't have permission to use that command."), delete_after=6)
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(view=quick_card_view("❌ Missing arguments. Use `?help` for usage."), delete_after=6)
        return
    if isinstance(error, commands.CheckFailure):
        await ctx.send(str(error) or "❌ You don't have permission to use that command.", delete_after=6)
        return
    await ctx.send(view=quick_card_view(f"❌ Error: {error}"), delete_after=8)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        if interaction.response.is_done():
            await interaction.followup.send("❌ You don't have permission to use that command.", ephemeral=True)
        else:
            await interaction.response.send_message(view=quick_card_view("❌ You don't have permission to use that command."), ephemeral=True)
        return
    if interaction.response.is_done():
        await interaction.followup.send(f"❌ Error: {error}", ephemeral=True)
    else:
        await interaction.response.send_message(view=quick_card_view(f"❌ Error: {error}"), ephemeral=True)


