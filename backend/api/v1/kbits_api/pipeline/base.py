"""Core types and the strategy registry for the knowledge-bits pipeline.

The pipeline has four stages, and each stage is a *strategy*: an interchangeable
algorithm sharing one fixed input/output contract. Many strategies can be
registered per stage; one is the default. The orchestrator resolves each stage
by name (from the request or the registered default) and chains them:

    build(query) -> generate -> screen -> rank -> insert

Adding a new algorithm means writing a class that satisfies the stage's
``Protocol`` and registering it. Nothing else in the pipeline changes. The query
and generate stages are awaited (they call agents and models); screen and rank
are pure in-process transforms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, Protocol, TypeVar, runtime_checkable


@dataclass
class Query:
    """What kind of bits the user needs, produced by a ``QueryStrategy``.

    ``include`` and ``exclude`` are short terms: the rank stage scores candidates
    against ``include``, and the screen stage treats ``exclude`` as redundant
    ground. ``brief`` is optional prose — an agent-built query uses it to explain
    what this user needs right now, which terms alone cannot carry.

    ``graph_id`` and ``expansion_node_id`` are set by graph query strategies for
    post-generation enrichment; they are not part of the public invoke API.
    """

    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    brief: str = ""
    graph_id: str | None = None
    expansion_node_id: str | None = None
    rejected_titles: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        """Flatten the query into plain text for a text/LLM-based generator."""
        parts: list[str] = []
        if self.include:
            parts.append("Focus on: " + "; ".join(self.include))
        if self.exclude:
            parts.append("Avoid repeating: " + "; ".join(self.exclude))
        if self.brief:
            parts.append("What this user needs right now:\n" + self.brief)
        return "\n".join(parts)


@dataclass
class KBCandidate:
    """A single knowledge bit before it is persisted."""

    title: str
    content: str
    related_goal: str | None = None


@dataclass
class PipelineContext:
    """Shared, read-only inputs available to every strategy in one invoke.

    Loaded once by the orchestrator so strategies never re-query the database.
    Agent-backed strategies read live data through tools instead and only need
    ``user_id``, ``goal_id`` and ``count`` from here.
    """

    user_id: str
    goal_id: str | None = None
    count: int = 5
    goals: list[dict] = field(default_factory=list)
    profile: dict = field(default_factory=dict)
    existing_titles: list[str] = field(default_factory=list)
    graph_weights: dict[str, float] = field(default_factory=dict)
    selected_graph_id: str | None = None
    selected_node_id: str | None = None


# --- Stage contracts (fixed I/O shapes) -------------------------------------


@runtime_checkable
class QueryStrategy(Protocol):
    """Work out what kind of bits the user needs right now.

    Awaited so a strategy can be an agent that reads the user's goals, diary,
    calendar and existing bits through tools.
    """

    async def build(self, ctx: PipelineContext) -> Query: ...


@runtime_checkable
class GeneratorStrategy(Protocol):
    """Produce candidate bits for a query."""

    async def generate(self, query: Query, limit: int) -> list[KBCandidate]: ...


@runtime_checkable
class ScreenStrategy(Protocol):
    """Drop unwanted candidates (duplicates, empties, irrelevant)."""

    def screen(
        self, candidates: list[KBCandidate], ctx: PipelineContext
    ) -> list[KBCandidate]: ...


@runtime_checkable
class RankStrategy(Protocol):
    """Order screened candidates best-first."""

    def rank(self, candidates: list[KBCandidate], query: Query) -> list[KBCandidate]: ...


# --- Registry ---------------------------------------------------------------

T = TypeVar("T")


class Registry(Generic[T]):
    """A named collection of strategies for one stage, with a default.

    Usage::

        QUERY_STRATEGIES: Registry[QueryStrategy] = Registry("query")

        @QUERY_STRATEGIES.register("goals_profile", default=True)
        class GoalsProfileQuery: ...
    """

    def __init__(self, stage: str) -> None:
        self.stage = stage
        self._items: dict[str, T] = {}
        self._default: str | None = None

    def register(self, name: str, *, default: bool = False):
        """Class decorator that instantiates and registers a strategy by name."""

        def decorator(cls: type[T]) -> type[T]:
            if name in self._items:
                raise ValueError(
                    f"Strategy '{name}' already registered for stage '{self.stage}'"
                )
            self._items[name] = cls()
            if default or self._default is None:
                self._default = name
            return cls

        return decorator

    def get(self, name: str | None) -> T:
        """Resolve a strategy by name, or the default when ``name`` is falsy."""
        key = name or self._default
        if key is None:
            raise LookupError(f"No strategies registered for stage '{self.stage}'")
        try:
            return self._items[key]
        except KeyError:
            raise KeyError(
                f"Unknown {self.stage} strategy '{name}'. "
                f"Available: {', '.join(self.names()) or '(none)'}"
            )

    def names(self) -> list[str]:
        return sorted(self._items)

    @property
    def default(self) -> str | None:
        return self._default
