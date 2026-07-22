"""Shared constants for the Knowledge Bits API."""

# How many bits a single invoke asks the source for, and the hard ceiling.
DEFAULT_INVOKE_COUNT = 5
MAX_INVOKE_COUNT = 20

# How many recent bit titles are loaded to seed dedup / query exclusions.
RECENT_TITLES_LIMIT = 100

# Interaction fields a client may set through PATCH /kbits/{id}. Everything
# else on the row (title, content, timestamps, user_id) is server-owned.
UPDATABLE_FIELDS: frozenset[str] = frozenset(
    {
        "is_read",
        "is_liked",
        "is_disliked",
        "rating",
        "is_marked_relavant",
        "is_marked_irrelavant",
    }
)

# Bounds for the optional star rating.
MIN_RATING = 1
MAX_RATING = 5
