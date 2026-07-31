"""Seed data for knowledge bits (public.knowledge_bits).

Each entry belongs to a user (by email). ``goal_name`` optionally links the bit
to a seeded goal of the same name (resolved to ``related_goal`` at seed time);
omit it for goalless bits. Interaction flags default to unset when absent.

``generator_prompt`` is the user message sent to the LLM generator when the bit
was created (same shape as ``build_generator_user_message`` in the pipeline).

``comments`` optionally seeds a discussion thread on the bit: each string is a
user comment, and the agent generates a reply after each one (see
005_seed_kbits). The bit itself is the subject of the thread and is never stored
as a message.
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
        "generator_prompt": (
            "Generate 5 knowledge bits.\n\n"
            "Focus on: habit formation; overcoming inertia; morning routines\n"
            "Avoid repeating: Spaced repetition beats cramming\n"
            "What this user needs right now:\n"
            "They keep failing to start their morning routine and want practical "
            "ways to make the first step feel small enough to actually do."
        ),
        "is_read": True,
        "is_liked": True,
        "comments": [
            "I keep failing to start my morning routine — where would you apply this first?",
            "Okay: one push-up and one line in my journal. I'll try it tomorrow.",
        ],
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
        "generator_prompt": (
            "Generate 5 knowledge bits.\n\n"
            "Focus on: journaling as reflection; prompts that unlock insight; "
            "daily writing habits\n"
            "Avoid repeating: Two-minute rule for starting habits\n"
            "What this user needs right now:\n"
            "They journal regularly but mostly log events. They want bits that help "
            "turn writing into a thinking practice."
        ),
        "is_read": True,
        "is_marked_relavant": True,
        "rating": 5,
        "comments": [
            "What kind of question should I put at the top of the page?",
        ],
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
        "generator_prompt": (
            "Generate 5 knowledge bits.\n\n"
            "Focus on: deep work; attention management; phone distraction\n"
            "Avoid repeating: Write to think, not to record; Two-minute rule for starting habits\n"
            "What this user needs right now:\n"
            "Their phone is the biggest blocker to focused work. They need concrete "
            "environment and ritual changes, not generic productivity advice."
        ),
        "is_read": False,
        "comments": [
            "My phone is my biggest distraction. Any tip beyond just putting it away?",
        ],
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
        "generator_prompt": (
            "Generate 5 knowledge bits.\n\n"
            "Focus on: incremental shipping; reducing scope; learning from users early\n"
            "Avoid repeating: Feedback loops shrink the goal gap\n"
            "What this user needs right now:\n"
            "They are building Sakhi Smritika and tend toward big batches. They need "
            "bits that reinforce shipping small slices and getting feedback quickly."
        ),
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
        "generator_prompt": (
            "Generate 5 knowledge bits.\n\n"
            "Focus on: sleep hygiene; wind-down routines; performance and recovery\n"
            "What this user needs right now:\n"
            "They often work late into the evening and treat sleep as optional. "
            "Goalless general well-being angle — no specific goal to anchor."
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
        "generator_prompt": (
            "Generate 5 knowledge bits.\n\n"
            "Focus on: spaced repetition; long-term memory; study systems\n"
            "Avoid repeating: Two-minute rule for starting habits\n"
            "What this user needs right now:\n"
            "They are learning new material and default to cramming. They need "
            "evidence-based study habits that stick."
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
        "generator_prompt": (
            "Generate 5 knowledge bits.\n\n"
            "Focus on: environment design; choice architecture; reducing friction\n"
            "Avoid repeating: The map of deep work; Make the default the good choice\n"
            "What this user needs right now:\n"
            "They rely on motivation and lose streaks when willpower dips. "
            "Bits should emphasize designing defaults, not trying harder."
        ),
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
        "generator_prompt": (
            "Generate 5 knowledge bits.\n\n"
            "Focus on: feedback loops; measuring progress; course correction\n"
            "Avoid repeating: Ship small, ship often\n"
            "What this user needs right now:\n"
            "They have goals for Sakhi Smritika but progress feels vague. "
            "They need bits on tightening the loop between action and measurable signal."
        ),
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
        "generator_prompt": (
            "Generate 5 knowledge bits.\n\n"
            "Focus on: user-journey testing; prioritizing core flows; practical QA\n"
            "Avoid repeating: Reproduce before you fix\n"
            "What this user needs right now:\n"
            "They are QA-ing the app and want to focus testing on real user paths "
            "instead of chasing coverage metrics."
        ),
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
        "generator_prompt": (
            "Generate 5 knowledge bits.\n\n"
            "Focus on: bug reproduction; debugging discipline; flaky tests\n"
            "Avoid repeating: Test the flow a user actually takes\n"
            "What this user needs right now:\n"
            "They hit a flaky bug they cannot reproduce reliably. "
            "Bits should stress systematic reproduction before fixing."
        ),
        "comments": [
            "I have a flaky bug I can't reproduce reliably. How should I start?",
            "Makes sense — I'll capture the exact steps and environment next time it fires.",
        ],
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
        "generator_prompt": (
            "Generate 5 knowledge bits.\n\n"
            "Focus on: round-trip testing; serialization; diary save/load\n"
            "Avoid repeating: Reproduce before you fix\n"
            "What this user needs right now:\n"
            "They are testing diary persistence and need reminders to verify "
            "write-read parity, not just that save appears to succeed."
        ),
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
        "generator_prompt": (
            "Generate 5 knowledge bits.\n\n"
            "Focus on: redirecting curiosity; replacing doom-scrolling; small experiments\n"
            "What this user needs right now:\n"
            "General personal-growth angle — help them channel restlessness into "
            "learning instead of passive scrolling. No specific goal."
        ),
        # goalless bit
    },
]
