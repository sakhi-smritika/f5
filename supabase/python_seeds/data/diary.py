"""Seed data for diary entries and hourly day logs (public.diary)."""

# Each row targets one user + date. Include diary fields, day_log, or both.
# day_log keys are hour strings "0" through "23", matching the Day Log UI.

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
            "6": "Wake up, stretch, plan the day",
            "7": "Breakfast and light reading",
            "9": "Deep work on Sakhi Smritika",
            "12": "Lunch break",
            "14": "Code review and bug fixes",
            "17": "Walk outside",
            "20": "Diary writing and wind down",
            "22": "Read before sleep",
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
            "8": "Standup and prioritization",
            "10": "Frontend work on folders",
            "13": "Lunch + short walk",
            "15": "Backend endpoints for folder delete",
            "18": "Manual testing in local Supabase",
            "21": "Notes for tomorrow",
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
            "9": "QA pass on diary page",
            "11": "QA pass on day log page",
            "15": "Regression check on chat panel",
        },
    },
]
