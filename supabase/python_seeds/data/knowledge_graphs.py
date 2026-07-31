"""Seed data for user-managed knowledge graphs.

Each graph belongs to a user (by email) and is keyed by ``key`` for internal
reference. ``nodes`` lists concept nodes; ``edges`` are pairs of node keys
(undirected). Run ``005_seed_knowledge_graphs`` before ``006_seed_kbits`` so bits
can resolve graph and node ids at seed time.
"""

SEED_KNOWLEDGE_GRAPHS = [
    {
        "email": "seed_user@gmail.com",
        "key": "agentic_ai",
        "title": "Agentic AI systems",
        "description": (
            "Concepts for building agents that reason, call tools, and iterate "
            "toward a goal."
        ),
        "nodes": [
            {
                "key": "react",
                "label": "ReAct pattern",
                "description": "Interleave reasoning traces with tool actions.",
            },
            {
                "key": "tool_use",
                "label": "Tool use loops",
                "description": "Repeated observe-act cycles through an API surface.",
            },
            {
                "key": "planning",
                "label": "Planning loops",
                "description": "Decompose a goal before executing tool steps.",
            },
        ],
        "edges": [
            ("react", "tool_use"),
            ("tool_use", "planning"),
        ],
    },
    {
        "email": "test@example.com",
        "key": "qa_graph",
        "title": "Software testing",
        "description": "Core testing concepts for QA work on the app.",
        "nodes": [
            {
                "key": "repro",
                "label": "Bug reproduction",
                "description": "Reliably recreate a failure before fixing it.",
            },
            {
                "key": "round_trip",
                "label": "Round-trip testing",
                "description": "Write data, read it back, assert parity.",
            },
        ],
        "edges": [
            ("repro", "round_trip"),
        ],
    },
]
