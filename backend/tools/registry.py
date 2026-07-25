"""
Assembles the ADK tools exposed to the agents.

``ALL_TOOLS`` is the full set the chat assistant gets (``FunctionTool``s and
``McpToolset``s). ``KBIT_QUERY_TOOLS`` is a read-only ``FunctionTool`` subset
for the knowledge-bit query agent.
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
from .web_search_tools.parallel_web_search import get_parallel_web_search_toolset

_FUNCTION_TOOLS: list[FunctionTool] = [
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

_MCP_TOOLSETS = [
    get_parallel_web_search_toolset(),
]

ALL_TOOLS = [*_FUNCTION_TOOLS, *_MCP_TOOLSETS]

# Read-only tools for the knowledge-bit query agent, which reads the user's
# current situation to work out what kind of bits they need. Writes are excluded
# so query building can never mutate data — in particular ``create_kbit``, which
# would insert bits straight into the feed and bypass the screen and rank stages.
KBIT_QUERY_TOOLS: list[FunctionTool] = [
    # Goals — what the user is working toward
    FunctionTool(list_my_goals),
    FunctionTool(get_goal),
    FunctionTool(list_child_goals),
    FunctionTool(search_goals),
    # Knowledge Bits — what the user has already been shown
    FunctionTool(list_recent_kbits),
    FunctionTool(get_knowledge_bit),
    FunctionTool(search_kbits),
    # Diary — how the user's days are actually going
    FunctionTool(get_recent_diary_entries),
    FunctionTool(search_diary),
    FunctionTool(get_diary_entry),
    # Google — what the user's upcoming time and to-dos look like
    FunctionTool(list_calendar_events),
    FunctionTool(list_tasks),
]
