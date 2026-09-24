"""Seed data for diary entries and hourly day logs (public.diary)."""

# Each row targets one user + date. Include diary fields, day_log, or both.
# day_log keys are hour strings "0" through "23". Each hour is
# {"done": "...", "impact": "..."}.

SEED_DIARY_ENTRIES = [
    # Diary-only entry
    {
        "email": "seed_user@gmail.com",
        "date": "2026-07-18",
        "how_was_the_day": "Calm and productive. Felt focused after an early start.",
        "major_events": "Shipped a small UI fix and reviewed project notes.",
        "general_content": (
            "Morning was quiet. I blocked two hours for deep work and kept notifications "
            "off. Evening walk helped me decompress before planning tomorrow."
        ),
    },
    # Another diary-only entry
    {
        "email": "seed_user@gmail.com",
        "date": "2026-07-19",
        "how_was_the_day": "A bit scattered in the afternoon, but ended on a good note.",
        "major_events": "Caught up with a friend over coffee.",
        "general_content": (
            "Started the day with inbox cleanup. Lost momentum after lunch, then "
            "recovered with a short journaling session."
        ),
    },
    # Day-log-only entry
    {
        "email": "seed_user@gmail.com",
        "date": "2026-07-20",
        "day_log": {
            "6": {"done": "Wake up, stretch, plan the day", "impact": "Started with a clear list"},
            "7": {"done": "Breakfast and light reading", "impact": "Settled in before deep work"},
            "9": {"done": "Deep work on Sakhi Smritika", "impact": "Moved the day log UI forward"},
            "12": {"done": "Lunch break", "impact": "Reset energy for the afternoon"},
            "14": {"done": "Code review and bug fixes", "impact": "Unblocked a couple of open PRs"},
            "17": {"done": "Walk outside", "impact": "Cleared my head after sitting all day"},
            "20": {"done": "Diary writing and wind down", "impact": "Captured the day before it faded"},
            "22": {"done": "Read before sleep", "impact": "Slept easier"},
        },
    },
    # Combined diary + day log on the same date
    {
        "email": "seed_user@gmail.com",
        "date": "2026-07-21",
        "how_was_the_day": "Energized and intentional throughout the day.",
        "major_events": "Completed folder feature for chat sidebar.",
        "general_content": (
            "Good balance of building and reflection. Happy with how the sidebar "
            "organization turned out."
        ),
        "day_log": {
            "8": {"done": "Standup and prioritization", "impact": "Locked the day's focus"},
            "10": {"done": "Frontend work on folders", "impact": "Sidebar folders actually usable"},
            "13": {"done": "Lunch + short walk", "impact": "Came back less stuck"},
            "15": {"done": "Backend endpoints for folder delete", "impact": "Delete path works end to end"},
            "18": {"done": "Manual testing in local Supabase", "impact": "Caught a RLS miss before merge"},
            "21": {"done": "Notes for tomorrow", "impact": "Didn't lose the next step"},
        },
    },
    # Test user: diary entry
    {
        "email": "test@example.com",
        "date": "2026-07-20",
        "how_was_the_day": "Neutral — mostly testing flows.",
        "major_events": "Ran through login and diary save paths.",
        "general_content": "Used this account to verify seeded data loads correctly.",
    },
    # Test user: day log entry
    {
        "email": "test@example.com",
        "date": "2026-07-21",
        "day_log": {
            "9": {"done": "QA pass on diary page", "impact": "Confirmed save/load for diary fields"},
            "11": {"done": "QA pass on day log page", "impact": "Hour slots load and persist"},
            "15": {"done": "Regression check on chat panel", "impact": "No break in the streaming path"},
        },
    },
]
