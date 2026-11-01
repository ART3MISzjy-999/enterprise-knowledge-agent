from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    question: str
    history: list[dict[str, str]] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    evidence: dict[str, dict[str, Any]] = field(default_factory=dict)
    feedback: list[str] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: int = 0
    successful_signatures: set[str] = field(default_factory=set)

    def model_view(self, step: int, max_steps: int, max_tool_calls: int) -> dict:
        from .context import user_facts
        return {
            "user_statement_ledger": user_facts(self),
            "question": self.question,
            "history": self.history,
            "observations": self.observations,
            "validation_feedback": self.feedback,
            "budget": {"step": step, "max_steps": max_steps,
                       "tool_calls": self.tool_calls, "max_tool_calls": max_tool_calls},
        }
