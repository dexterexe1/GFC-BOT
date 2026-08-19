"""
bot_control.py — Advanced Bot Control System
- Owner-only mode
- Command disable system (per-server and global)
- No-prefix system toggle
- Bot lockdown features
"""
import discord
from discord.ext import commands
import discord.app_commands as app_commands
from typing import Optional

from bot.config import bot, style_embed, BRAND_COLOR, BRAND_EMOJI, staff_check
from bot.database import (
    is_feature_disabled, disable_feature, enable_feature,
    add_bot_owner, remove_bot_owner, is_bot_owner, get_bot_owners,
    is_owner_only_mode, set_owner_only_mode, is_noprefix_enabled, set_noprefix_enabled
)

# ==========================================
#         OWNER-ONLY MODE SYSTEM
# ==========================================

async def owner_only_check(ctx):
    """Check if bot is in owner-only mode and if user is authorized."""
    if not is_owner_only_mode():
        return True  # Owner-only mode disabled, allow all
    
    # Check if user is a bot owner
    if is_bot_owner(ctx.author.id):
        return True
    
    # Not authorized
    await ctx.send(
        embed=style_embed(
            title="🔒 Bot Locked",
            description=f"This bot is currently in **Owner-Only Mode**.\n"
                       f"Only authorized owners can use commands.",
            kind="error"
        ),
        delete_after=10
    )
    return False


async def command_enabled_check(ctx):
    """Check if command is disabled for this server or globally."""
    command_name = ctx.command.name if ctx.command else None
    if not command_name:
        return True
    
    # Check global disable
    if await is_feature_disabled(0, command_name, 'command'):
        await ctx.send(
            embed=style_embed(
                title="❌ Command Disabled",
                description=f"The command `{command_name}` has been **globally disabled** by the bot owner.",
                kind="error"
            ),
            delete_after=10
        )
        return False
    
    # Check server-specific disable
    if ctx.guild and await is_feature_disabled(ctx.guild.id, command_name, 'command'):
        await ctx.send(
            embed=style_embed(
                title="❌ Command Disabled",
                description=f"The command `{command_name}` has been disabled in this server.",
                kind="error"
            ),
            delete_after=10
        )
        return False
    
    return True


# ==========================================
#         BOT OWNER MANAGEMENT
# ==========================================

# ==========================================
#         OWNER-ONLY MODE TOGGLE
# ==========================================

@bot.hybrid_command(
    name="devhelp",
    aliases=["developerhelp", "devcommands"],
    help="Show developer-only bot commands (owners only)",
    description="Show developer-only bot commands (owners only)",
)
async def developer_help_cmd(ctx: commands.Context):
    """Show the commands available to bot owners."""
    try:
        if not is_bot_owner(ctx.author.id):
            await ctx.send(
                embed=style_embed(
                    title="Unauthorized",
                    description=(
                        "Only bot owners can use ?devhelp.\n"
                        "Add your Discord user ID to BOT_OWNER_IDS in bot/config.py."
                    ),
                    kind="error",
                )
            )
            return

        static = {
            "Developer / Owner": [
                "`?owneronlymode [on|off]` — Lock bot to owners only",
                "`?lockbot` — Alias for owner-only mode",
                "`?botstatus` / `?botinfo` — Bot status info",
                "`?devhelp` — This menu",
            ],
            "Command Management": [
                "`?disablecommand <name> [server|global]` — Disable a command",
                "`?enablecommand <name> [server|global]` — Re-enable a command",
                "`?disabledcommands` — List disabled commands",
            ],
            "No-prefix / modes": [
                "`?togglenoprefix` / `?noprefixmode` — Toggle no-prefix mode",
            ],
            "Premium AI (owner)": [
                "`?provideai` / `?disableai`",
                "`?providenonprefix` / `?disablenonprefix`",
                "`?aistatus` / `?ailist`",
            ],
        }

        live_lines = []
        try:
            for command in sorted(bot.commands, key=lambda c: c.name.lower()):
                if command.hidden:
                    continue
                if _is_developer_command(command):
                    sig = getattr(command, "signature", "") or ""
                    usage = f"?{command.name}" + (f" {sig}" if sig else "")
                    desc = (command.help or command.description or "").strip()
                    if len(desc) > 80:
                        desc = desc[:77] + "..."
                    live_lines.append(f"`{usage}`" + (f" — {desc}" if desc else ""))
        except Exception:
            pass

        embed = style_embed(
            title="Developer Command Center",
            description="Owner-only tools. You are authorized.",
            kind="info",
        )
        for cat, lines in static.items():
            embed.add_field(name=cat, value="\n".join(lines), inline=False)

        if live_lines:
            chunk, chunks, size = [], [], 0
            for line in live_lines:
                if chunk and size + len(line) + 1 > 1000:
                    chunks.append("\n".join(chunk))
                    chunk, size = [], 0
                chunk.append(line)
                size += len(line) + 1
            if chunk:
                chunks.append("\n".join(chunk))
            for i, ch in enumerate(chunks[:5]):
                name = "Registered owner commands" if i == 0 else f"Registered owner commands ({i + 1})"
                embed.add_field(name=name, value=ch, inline=False)

        embed.set_footer(text="Developer Tools • United Bunnies")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"devhelp error: `{e}`")


# ==========================================
#         COMMAND DISABLE SYSTEM
# ==========================================

@bot.command(name="disablecommand", aliases=["disablecmd"], help="Disable a command globally or per-server (owners only)")
async def disable_command_cmd(ctx: commands.Context, command_name: str, scope: str = "server"):
    """Disable a command globally or in this server."""
    # Check if command issuer is a bot owner (global) or admin (server)
    if scope.lower() == "global":
        if not is_bot_owner(ctx.author.id):
            await ctx.send(
                embed=style_embed(
                    title="❌ Unauthorized",
                    description="Only bot owners can disable commands globally.",
                    kind="error"
                )
            )
            return
        guild_id = 0
        scope_text = "globally"
    else:
        if not ctx.guild:
            await ctx.send(embed=style_embed(title="❌ Error", description="This command must be used in a server.", kind="error"))
            return
        if not ctx.author.guild_permissions.administrator:
            await ctx.send(
                embed=style_embed(
                    title="❌ Unauthorized",
                    description="Only server administrators can disable commands in this server.",
                    kind="error"
                )
            )
            return
        guild_id = ctx.guild.id
        scope_text = "in this server"
    
    # Check if command exists
    if not bot.get_command(command_name):
        await ctx.send(
            embed=style_embed(
                title="❌ Unknown Command",
                description=f"Command `{command_name}` does not exist.",
                kind="error"
            )
        )
        return
    
    # Disable the command
    await disable_feature(guild_id, command_name, 'command')
    
    embed = style_embed(
        title=f"{BRAND_EMOJI} Command Disabled",
        description=f"✅ Command `{command_name}` has been disabled **{scope_text}**.",
        kind="success"
    )
    
    await ctx.send(embed=embed)


@bot.command(name="enablecommand", aliases=["enablecmd"], help="Re-enable a disabled command (owners/admins)")
async def enable_command_cmd(ctx: commands.Context, command_name: str, scope: str = "server"):
    """Re-enable a previously disabled command."""
    # Check permissions
    if scope.lower() == "global":
        if not is_bot_owner(ctx.author.id):
            await ctx.send(
                embed=style_embed(
                    title="❌ Unauthorized",
                    description="Only bot owners can enable commands globally.",
                    kind="error"
                )
            )
            return
        guild_id = 0
        scope_text = "globally"
    else:
        if not ctx.guild:
            await ctx.send(embed=style_embed(title="❌ Error", description="This command must be used in a server.", kind="error"))
            return
        if not ctx.author.guild_permissions.administrator:
            await ctx.send(
                embed=style_embed(
                    title="❌ Unauthorized",
                    description="Only server administrators can enable commands in this server.",
                    kind="error"
                )
            )
            return
        guild_id = ctx.guild.id
        scope_text = "in this server"
    
    # Enable the command
    await enable_feature(guild_id, command_name, 'command')
    
    embed = style_embed(
        title=f"{BRAND_EMOJI} Command Enabled",
        description=f"✅ Command `{command_name}` has been re-enabled **{scope_text}**.",
        kind="success"
    )
    
    await ctx.send(embed=embed)


@bot.command(name="disabledcommands", aliases=["listdisabled"], help="List all disabled commands")
async def list_disabled_commands(ctx: commands.Context):
    """List all disabled commands for this server and globally."""
    from bot.database import list_disabled_features
    
    # Get global disabled commands
    global_disabled = list_disabled_features(0, 'command')
    
    # Get server disabled commands
    server_disabled = []
    if ctx.guild:
        server_disabled = list_disabled_features(ctx.guild.id, 'command')
    
    description = ""
    
    if global_disabled:
        description += "**🌐 Globally Disabled:**\n"
        for cmd in global_disabled:
            description += f"• `{cmd}`\n"
        description += "\n"
    
    if server_disabled:
        description += f"**🏠 Disabled in This Server:**\n"
        for cmd in server_disabled:
            description += f"• `{cmd}`\n"
        description += "\n"
    
    if not global_disabled and not server_disabled:
        description = "No commands are currently disabled."
    
    embed = style_embed(
        title=f"{BRAND_EMOJI} Disabled Commands",
        description=description,
        color=BRAND_COLOR,
        kind="info"
    )
    
    await ctx.send(embed=embed)


# ==========================================
#         NO-PREFIX SYSTEM TOGGLE
# ==========================================

@bot.command(name="togglenoprefix", aliases=["noprefixmode"], help="Enable/disable no-prefix system (staff/mod or owner)")
@staff_check("mod")
async def toggle_noprefix_cmd(ctx: commands.Context, enabled: Optional[bool] = None):
    """Toggle the no-prefix command system. Server mods/staff can turn it on or off."""
    # staff_check already enforces mod; owners also pass is_staff
    
    # Toggle if not specified
    if enabled is None:
        enabled = not is_noprefix_enabled()
    
    set_noprefix_enabled(enabled)
    
    if enabled:
        embed = style_embed(
            title="✅ No-Prefix System Enabled",
            description="The no-prefix command system is now **active**.\n\n"
                       "Users with no-prefix permission can run commands without `?`",
            kind="success"
        )
    else:
        embed = style_embed(
            title="❌ No-Prefix System Disabled",
            description="The no-prefix command system is now **disabled**.\n\n"
                       "All users must use `?` prefix for commands.",
            kind="info"
        )
    
    await ctx.send(embed=embed)


@bot.command(name="botstatus", aliases=["botinfo"], help="Show bot control status")
async def bot_status_cmd(ctx: commands.Context):
    """Show current bot control settings."""
    owners = get_bot_owners()
    owner_mode = is_owner_only_mode()
    noprefix_mode = is_noprefix_enabled()
    
    description = ""
    
    # Owner-only mode
    if owner_mode:
        description += "🔒 **Owner-Only Mode:** `ENABLED`\n"
        description += "   Only bot owners can use commands\n\n"
    else:
        description += "🔓 **Owner-Only Mode:** `DISABLED`\n"
        description += "   All users can use commands\n\n"
    
    # No-prefix system
    if noprefix_mode:
        description += "✅ **No-Prefix System:** `ENABLED`\n"
        description += "   Trusted users can run commands without `?`\n\n"
    else:
        description += "❌ **No-Prefix System:** `DISABLED`\n"
        description += "   All users must use `?` prefix\n\n"
    
    # Bot managers
    description += f"👑 **Revenue Managers:** `{len(owners)}`\n"
    if owners:
        for owner_id, owner_name in owners[:3]:  # Show first 3
            user = bot.get_user(owner_id)
            if user:
                description += f"   • {user.mention}\n"
        if len(owners) > 3:
            description += f"   • ... and {len(owners) - 3} more\n"
    
    embed = style_embed(
        title=f"{BRAND_EMOJI} Bot Control Status",
        description=description,
        color=BRAND_COLOR,
        kind="info"
    )
    
    embed.set_footer(text="United Bunnies Bot Control System")
    
    await ctx.send(embed=embed)


# ==========================================
#         COMMAND CHECK HOOKS
# ==========================================

# Register checks globally
@bot.check
async def global_command_checks(ctx):
    """Global checks that run before every command."""
    # Check owner-only mode
    if not await owner_only_check(ctx):
        return False
    
    # Check if command is disabled
    if not await command_enabled_check(ctx):
        return False
    
    return True
