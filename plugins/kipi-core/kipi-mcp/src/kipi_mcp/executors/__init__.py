from dataclasses import dataclass, field


@dataclass
class ExecutorResult:
    records: list[dict] = field(default_factory=list)
    cursor_after: str | None = None
    error: str | None = None
    cost: float = 0.0
