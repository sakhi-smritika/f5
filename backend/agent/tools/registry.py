"""
Assembles the ADK tools exposed to the assistant.

Kept as a flat ``ALL_TOOLS`` list. Grouping/selection can be layered on later
without changing the underlying tool functions.
"""

from google.adk.tools import FunctionTool

from .introspection_tools.diary_tools import (
    get_day_log,
    get_diary_entry,
    get_recent_diary_entries,
    search_diary,
    set_day_log_hour,
    upsert_diary_entry,
)
from .google_tools.calender_tools import (
    create_calendar_event,
    list_calendar_events,
)

from .google_tools.tasks_tools import (
    complete_task,
    create_task,
    list_tasks
)

from .goals_tools.goals_tools import (
    create_goal,
    get_goal,
    list_child_goals,
    list_my_goals,
    search_goals,
    update_goal,
)

from .kbits_tools.kbits_tools import (
    create_kbit,
    get_knowledge_bit,
    list_recent_kbits,
    search_kbits,
    update_kbit,
)

ALL_TOOLS: list[FunctionTool] = [
    # Diary
    FunctionTool(get_diary_entry),
    FunctionTool(get_recent_diary_entries),
    FunctionTool(search_diary),
    FunctionTool(get_day_log),
    FunctionTool(upsert_diary_entry),
    FunctionTool(set_day_log_hour),
    # Goals
    FunctionTool(list_my_goals),
    FunctionTool(get_goal),
    FunctionTool(list_child_goals),
    FunctionTool(search_goals),
    FunctionTool(create_goal),
    FunctionTool(update_goal),
    # Knowledge Bits
    FunctionTool(list_recent_kbits),
    FunctionTool(get_knowledge_bit),
    FunctionTool(search_kbits),
    FunctionTool(create_kbit),
    FunctionTool(update_kbit),
    # Google Calendar / Tasks
    FunctionTool(list_calendar_events),
    FunctionTool(create_calendar_event),
    FunctionTool(list_tasks),
    FunctionTool(create_task),
    FunctionTool(complete_task),
]
