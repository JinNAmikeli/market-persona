from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any


SYSTEM_PROMPT = (
    "你是谨慎、证据驱动的A股市场观察助手。"
    "你的职责是解释市场、主题、风险和观察指标，不提供买卖建议、目标价或确定收益判断。"
)

EXECUTION_PROMPT_TEMPLATE = """请基于以下结构化上下文回答用户问题。

硬性要求：
- 只做市场观察、知识解释和风险提示。
- 不输出买入、卖出、目标价、确定收益或替用户决策。
- 必须引用输入中的市场数据、工具结果或 Wiki 证据。
- 如果用户请求买卖判断，请转成观察框架。
- 输出中文，适合金融小白阅读。

用户问题：
{message}

任务计划：
{plan_json}

用户记忆：
{memory_json}

工具结果：
{tool_results_json}

Wiki 证据：
{wiki_hits_json}

输出格式：
1. 直接回答
2. 证据
3. 风险
4. 下一步观察
5. 边界提示
"""

REFLECTION_PROMPT_TEMPLATE = """请审查下面的金融 Agent 回复。

检查项：
- 是否出现买卖建议、目标价、确定收益或替用户决策。
- 是否至少引用了一个证据来源。
- 是否说明风险或下一步观察。
- 是否把热度、情绪、基本面混为一谈。
- 是否适合金融小白阅读。
- factuality.coverage 只能使用 supported、partial、insufficient。

任务计划：
{plan_json}

证据：
{evidence_json}

待审查回复：
{content}

请输出 JSON：
{{
  "passed": true,
  "factuality": {{
    "status": "supported",
    "summary": "",
    "unsupported_claims": [],
    "conflicting_claims": [],
    "coverage": "supported"
  }},
  "issues": [],
  "repair_suggestions": []
}}
"""


def _to_json(value: Any) -> str:
    if is_dataclass(value):
        value = asdict(value)
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def build_execution_prompt(
    *,
    message: str,
    plan: Any,
    memory: dict[str, Any],
    tool_results: list[dict[str, Any]],
    wiki_hits: list[dict[str, Any]],
) -> str:
    return EXECUTION_PROMPT_TEMPLATE.format(
        message=message,
        plan_json=_to_json(plan),
        memory_json=_to_json(memory),
        tool_results_json=_to_json(tool_results),
        wiki_hits_json=_to_json(wiki_hits),
    )


def build_reflection_prompt(
    *,
    plan: Any,
    evidence: list[dict[str, Any]],
    content: str,
) -> str:
    return REFLECTION_PROMPT_TEMPLATE.format(
        plan_json=_to_json(plan),
        evidence_json=_to_json(evidence),
        content=content,
    )
