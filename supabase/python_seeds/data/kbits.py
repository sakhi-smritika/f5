"""Seed data for knowledge bits (public.knowledge_bits).

Each entry belongs to a user (by email). ``goal_name`` optionally links the bit
to a seeded goal of the same name (resolved to ``related_goal`` at seed time);
omit it for goalless bits. Interaction flags default to unset when absent.
"""

SEED_KBITS = [
    # seed_user@gmail.com
    {
        "email": "seed_user@gmail.com",
        "title": "Two-minute rule for starting habits",
        "content": (
            "When a habit feels too big to start, shrink it to something you can do "
            "in two minutes: read one page, write one line, do one push-up. The point "
            "is to master showing up. Once the ritual is automatic, scaling the effort "
            "is far easier than fighting inertia every day."
        ),
        "goal_name": "Personal growth",
        "is_read": True,
        "is_liked": True,
    },
    {
        "email": "seed_user@gmail.com",
        "title": "Write to think, not to record",
        "content": (
            "Journaling is most useful when it's a thinking tool rather than a log of "
            "events. Ask a question at the top of the page and let the writing chase an "
            "answer. You'll notice patterns in your mood and decisions that are invisible "
            "in the moment."
        ),
        "goal_name": "Journal daily",
        "is_read": True,
        "is_marked_relavant": True,
        "rating": 5,
    },
    {
        "email": "seed_user@gmail.com",
        "title": "The map of deep work",
        "content": (
            "Deep work is the ability to focus without distraction on a cognitively "
            "demanding task. Protect a fixed block each day, remove your phone from the "
            "room, and define a clear target before you start. Depth compounds: an hour "
            "of true focus often beats a distracted afternoon."
        ),
        "goal_name": "Personal growth",
        "is_read": False,
    },
    {
        "email": "seed_user@gmail.com",
        "title": "Ship small, ship often",
        "content": (
            "Large releases hide risk and delay feedback. Break work into slices you can "
            "finish and ship in a day or two. Each small release is a chance to learn "
            "whether you're building the right thing before you've spent weeks on the "
            "wrong one."
        ),
        "goal_name": "Ship Sakhi Smritika",
        "is_liked": True,
    },
    {
        "email": "seed_user@gmail.com",
        "title": "Sleep is a performance input, not a luxury",
        "content": (
            "Consistent sleep improves memory consolidation, mood regulation, and "
            "reaction time more than any supplement. Anchor your wake time first; the "
            "bedtime tends to follow. Treat the last hour before bed as a wind-down, not "
            "a second work session."
        ),
        # goalless bit — general well-being
    },
    {
        "email": "seed_user@gmail.com",
        "title": "Spaced repetition beats cramming",
        "content": (
            "Reviewing material at increasing intervals moves it into long-term memory "
            "far more efficiently than a single long study session. A few minutes today, "
            "tomorrow, next week, and next month will outlast hours of cramming the night "
            "before."
        ),
        "is_read": True,
    },
    {
        "email": "seed_user@gmail.com",
        "title": "Make the default the good choice",
        "content": (
            "Willpower is unreliable; environment is not. Put the book on your pillow, "
            "the running shoes by the door, and the junk food out of sight. You don't "
            "have to win an argument with yourself if the easy option is already the one "
            "you want."
        ),
        "goal_name": "Personal growth",
        "is_disliked": True,
    },
    {
        "email": "seed_user@gmail.com",
        "title": "Feedback loops shrink the goal gap",
        "content": (
            "A goal without a feedback loop drifts. Decide how you'll measure progress "
            "and check it on a fixed cadence. The tighter the loop between action and "
            "signal, the faster you can course-correct toward what you actually want."
        ),
        "goal_name": "Ship Sakhi Smritika",
        "is_marked_relavant": True,
    },
    # test@example.com
    {
        "email": "test@example.com",
        "title": "Test the flow a user actually takes",
        "content": (
            "Coverage numbers can look great while the real user journey is broken. Start "
            "your test plan from the paths people use most—log in, create, edit, delete—"
            "and make those bulletproof before chasing edge cases."
        ),
        "goal_name": "QA core flows",
        "is_read": True,
        "rating": 4,
    },
    {
        "email": "test@example.com",
        "title": "Reproduce before you fix",
        "content": (
            "A bug you can't reproduce is a bug you can't confidently fix. Nail down the "
            "exact steps, data, and environment first. The reproduction is often 80% of "
            "the debugging work; the fix is the easy part."
        ),
        "goal_name": "QA core flows",
    },
    {
        "email": "test@example.com",
        "title": "Persisted data deserves a round-trip test",
        "content": (
            "Whenever data is saved and reloaded, test the full round trip: write it, "
            "read it back, and assert it matches. Serialization mismatches and timezone "
            "bugs love to hide in the gap between save and load."
        ),
        "goal_name": "Test diary save",
        "is_liked": True,
        "is_marked_relavant": True,
    },
    {
        "email": "test@example.com",
        "title": "Curiosity is a renewable resource",
        "content": (
            "The urge to scroll is often just curiosity looking for a target. Point it at "
            "something that moves you forward—one article, one concept, one small "
            "experiment—and the same restlessness becomes fuel instead of a drain."
        ),
        # goalless bit
    },
]
