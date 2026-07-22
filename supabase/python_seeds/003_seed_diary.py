"""
Seed diary entries and hourly day logs into public.diary.

Each seed row is keyed by user email + date. Rows may include:
- diary fields: how_was_the_day, major_events, general_content
- day_log: hourly map with keys "0" through "23"
- both on the same date
"""

import logging

from .data.diary import SEED_DIARY_ENTRIES
from .utils import get_admin_client, resolve_user_ids_by_emails

logger = logging.getLogger(__name__)

DIARY_FIELDS = ("how_was_the_day", "major_events", "general_content")


def build_diary_row(user_id: str, entry: dict) -> dict:
    """Build a public.diary upsert row from a seed payload."""
    row = {
        "user_id": user_id,
        "date": entry["date"],
    }

    for field in DIARY_FIELDS:
        if field in entry:
            row[field] = entry[field]

    if "day_log" in entry:
        row["day_log"] = entry["day_log"]

    return row


def describe_entry(entry: dict) -> str:
    has_diary = any(field in entry for field in DIARY_FIELDS)
    has_day_log = "day_log" in entry
    if has_diary and has_day_log:
        return "diary + day log"
    if has_day_log:
        return "day log"
    return "diary"


def seed_diary() -> None:
    """Seed diary and day-log rows for configured users."""
    supabase = get_admin_client()
    emails = sorted({entry["email"] for entry in SEED_DIARY_ENTRIES})
    user_ids_by_email = resolve_user_ids_by_emails(supabase, emails)

    missing = [email for email in emails if email not in user_ids_by_email]
    if missing:
        raise RuntimeError(
            "Cannot seed diary rows; run 001_seed_users first. Missing users: "
            + ", ".join(missing)
        )

    logger.info("Seeding %s diary row(s)...", len(SEED_DIARY_ENTRIES))

    for entry in SEED_DIARY_ENTRIES:
        email = entry["email"]
        user_id = user_ids_by_email[email]
        date = entry["date"]
        kind = describe_entry(entry)
        row = build_diary_row(user_id, entry)

        supabase.table("diary").upsert(row, on_conflict="user_id,date").execute()
        logger.info("✓ Seeded %s entry for %s on %s", kind, email, date)

    logger.info("Diary seeding complete!")


if __name__ == "__main__":
    seed_diary()
