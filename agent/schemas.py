from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentRequest:
    user_id: str
    message: str
    mode: str = "passive"
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentPlan:
    task_type: str
    intent: str
    required_tools: list[str]
    knowledge_queries: list[str]
    forbidden_outputs: list[str] = field(
        default_factory=lambda: ["buy_sell_instruction", "guaranteed_return", "target_price"]
    )


@dataclass
class ReflectionResult:
    passed: bool
    factuality: dict[str, Any] = field(
        default_factory=lambda: {
            "status": "supported",
            "summary": "",
            "checked_claims": 0,
            "supported_claims": 0,
            "unsupported_claims": [],
            "conflicting_claims": [],
            "evidence_count": 0,
            "coverage": "unknown",
        }
    )
    compliance: str = "passed"
    clarity: str = "passed"
    blocked_terms: list[str] = field(default_factory=list)
    repair_suggestions: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    layers: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentResponse:
    trace_id: str
    task_type: str
    content: str
    evidence: list[dict[str, Any]]
    risk_flags: list[str]
    next_watch: list[str]
    review: ReflectionResult
    execution: dict[str, Any] = field(default_factory=dict)
    repair: dict[str, Any] = field(default_factory=dict)
