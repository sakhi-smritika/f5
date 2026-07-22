"""Seed data for goals (public.goals)."""

# Parent goals must appear before their children. Use parent_key to link sub-goals.
# key is a stable identifier used only during seeding.

SEED_GOALS = [
    # seed_user@gmail.com — root goals
    {
        "email": "seed_user@gmail.com",
        "key": "personal_growth",
        "goal_name": "Personal growth",
        "goal_description": "Build better habits around reflection, learning, and health.",
        "progress": "On track",
    },
    {
        "email": "seed_user@gmail.com",
        "key": "sakhi_smritika",
        "goal_name": "Ship Sakhi Smritika",
        "goal_description": "Bring the personal-growth app to a usable daily workflow.",
        "progress": "In progress",
    },
    # seed_user@gmail.com — sub-goals
    {
        "email": "seed_user@gmail.com",
        "key": "daily_journaling",
        "parent_key": "personal_growth",
        "goal_name": "Journal daily",
        "goal_description": "Write in the diary at least five days per week.",
        "progress": "4/7 days this week",
    },
    {
        "email": "seed_user@gmail.com",
        "key": "chat_folders",
        "parent_key": "sakhi_smritika",
        "goal_name": "Chat folders",
        "goal_description": "Organize conversations into folders in the sidebar.",
        "progress": "Done",
    },
    {
        "email": "seed_user@gmail.com",
        "key": "seed_data",
        "parent_key": "sakhi_smritika",
        "goal_name": "Local seed data",
        "goal_description": "Seed users, diary, goals, and sample conversations for dev.",
        "progress": "In progress",
    },
    # test@example.com
    {
        "email": "test@example.com",
        "key": "qa_basics",
        "goal_name": "QA core flows",
        "goal_description": "Verify login, diary, day log, goals, and chat.",
        "progress": "Started",
    },
    {
        "email": "test@example.com",
        "key": "qa_diary",
        "parent_key": "qa_basics",
        "goal_name": "Test diary save",
        "goal_description": "Confirm diary entries load and persist per date.",
        "progress": "Done",
    },
    {
        "email": "test@example.com",
        "key": "qa_goals",
        "parent_key": "qa_basics",
        "goal_name": "Test goals hierarchy",
        "goal_description": "Confirm parent and child goals render correctly.",
        "progress": "Not started",
    },
]
