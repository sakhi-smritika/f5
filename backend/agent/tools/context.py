"""
Per-request user scoping for agent tools.

The chat endpoint sets ``current_user_id`` before running the agent so that tool
functions can read only the signed-in user's data. The LLM never supplies the
user id; tools always take it from here.
"""

from contextvars import ContextVar

current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)

# A human-readable label for the user's current local date/time, e.g.
# "Saturday, 2026-07-11 23:59 (Asia/Kolkata)". Set per request from the client
# so the assistant can resolve relative dates like "today" / "yesterday".
current_now_label: ContextVar[str | None] = ContextVar("current_now_label", default=None)

# A human-readable label for the user's approximate location, e.g.
# "latitude 12.9716, longitude 77.5946". Set per request from the client's
# geolocation (when granted).
current_location_label: ContextVar[str | None] = ContextVar(
    "current_location_label", default=None
)

# The knowledge bit under discussion, when a conversation is a kbit thread. Set
# per request from the linked bit (title/content/related_goal) so the agent can
# ground its replies in it. The bit is never stored as a chat message; it lives
# only in the system prompt, re-derived from the conversation's kbit_id on every
# turn (see agent._instruction_provider).
current_kbit: ContextVar[dict | None] = ContextVar("current_kbit", default=None)


def require_user_id() -> str:
    """Return the current user's id or raise if it has not been set.

    Tools call this instead of accepting a user id argument, so the model can
    never read another user's data.
    """
    user_id = current_user_id.get()
    if not user_id:
        raise RuntimeError(
            "No authenticated user in context; tools must run within a request "
            "that set current_user_id."
        )
    return user_id
