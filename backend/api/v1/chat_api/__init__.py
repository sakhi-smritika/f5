"""
Chat endpoints backed by the ADK agent.

Conversations are ADK sessions (messages + state) persisted in Supabase Postgres
via ``DatabaseSessionService``. A small ``conversations`` table stores sidebar
metadata (title, timestamps) so the frontend can render a ChatGPT-style history
list directly from Supabase (RLS-scoped), while message content is loaded through
these endpoints from the ADK session's event history.
"""

from .router import router

__all__ = ["router"]
