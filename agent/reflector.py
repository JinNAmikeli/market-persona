from __future__ import annotations

from market_radar.agent.schemas import ReflectionResult


BLOCKED_TERMS = ["可以买", "必须买", "必须卖", "满仓", "梭哈", "稳赚", "一定涨", "确定上涨", "目标价", "翻倍", "无风险"]
DISCLAIMER = "以上仅作市场观察和投资知识解释，不构成买卖建议。"


def review(content: str) -> ReflectionResult:
    blocked = [term for term in BLOCKED_TERMS if term in content]
    if blocked:
        return ReflectionResult(
            passed=False,
            compliance="failed",
            blocked_terms=blocked,
            repair_suggestions=["将买卖建议转写为观察维度", "补充风险提示和免责声明"],
        )
    return ReflectionResult(passed=True)


def repair(content: str) -> str:
    repaired = content
    replacements = {
        "可以买": "可以继续观察",
        "必须买": "需要谨慎观察",
        "必须卖": "需要重新评估风险",
        "满仓": "提高仓位前应先评估风险",
        "梭哈": "集中暴露风险较高",
        "稳赚": "不存在确定收益",
        "一定涨": "存在多种走势可能",
        "确定上涨": "并不具备确定性",
        "目标价": "观察区间",
        "翻倍": "大幅波动",
        "无风险": "风险较低但并非无风险",
    }
    for source, target in replacements.items():
        repaired = repaired.replace(source, target)
    if DISCLAIMER not in repaired:
        repaired = f"{repaired}\n\n{DISCLAIMER}"
    return repaired
