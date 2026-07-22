"""Seed data for sample chat conversations."""

SAMPLE_CONVERSATIONS = [
    {
        "title": "Morning reflection",
        "user_text": "Help me reflect on my day and pick one thing to improve tomorrow.",
    },
    {
        "title": "Weekly goals",
        "user_text": "I want to build a better weekly plan for my goals.",
    },
]

APP_NAME = "f5-chat"
DEFAULT_MODEL = "gpt-4o-mini"

SYSTEM_INSTRUCTION = (
    "You are a helpful, concise assistant embedded in a personal-growth web app. "
    "Be practical and encouraging. Use Markdown (lists, code blocks, bold) when it "
    "improves clarity, and keep answers focused."
)
