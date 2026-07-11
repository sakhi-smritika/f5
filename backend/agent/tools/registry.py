"""
Assembles the ADK tools exposed to the assistant.

Kept as a flat ``ALL_TOOLS`` list. Grouping/selection can be layered on later
without changing the underlying tool functions.
"""

from google.adk.tools import FunctionTool

from .diary_tools import (
    get_day_log,
    get_diary_entry,
    get_recent_diary_entries,
    search_diary,
)
from .profile_tools import get_my_profile

ALL_TOOLS: list[FunctionTool] = [
    FunctionTool(get_diary_entry),
    FunctionTool(get_recent_diary_entries),
    FunctionTool(search_diary),
    FunctionTool(get_day_log),
    FunctionTool(get_my_profile),
]
