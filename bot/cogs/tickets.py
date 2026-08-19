"""
tickets.py — Ticket system TEMPORARILY DISABLED (TICKETS_ENABLED = False).

Full implementation is preserved in tickets_backup.py.
Re-enable by setting TICKETS_ENABLED = True in config and restoring this file
from tickets_backup.py (or the original zip).
"""
import discord
from bot.config import TICKETS_ENABLED


class TicketPanelView(discord.ui.View):
    """Stub while tickets are disabled."""
    def __init__(self, *args, **kwargs):
        super().__init__(timeout=None)


class TicketManageView(discord.ui.View):
    """Stub while tickets are disabled."""
    def __init__(self, *args, **kwargs):
        super().__init__(timeout=None)


async def open_new_ticket(*args, **kwargs):
    """No-op while tickets are disabled."""
    return None


# No commands registered while disabled.
