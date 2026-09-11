"""
ClearQueue scoring engine.

A transparent, rule-based priority scorer. Every point awarded is traceable
to a specific, named factor — there is no hidden model and no black box.

Expected (flexible) input columns, all optional except case_id:
    case_id                str   required, unique identifier
    category                str   free text, e.g. "billing", "safety"
    amount                  num   financial exposure of the case
    days_open               num   how many days the case has been open
    missing_information     bool/num  True/1/"yes" if info is missing
    urgency                 str   "low" | "medium" | "high"
    dependencies            num   count of other cases/steps blocked on this one

Any missing column is simply skipped (contributes 0 and is flagged as
"not available") rather than causing an error, so the engine works on
partial or messy real-world exports.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


# --- Weights -----------------------------------------------------------
# Every weight below is the single source of truth for both the score
# and the human-readable explanation, so they can never drift apart.

MAX_FINANCIAL = 25
MAX_AGE = 20
MAX_MISSING_INFO = 20
MAX_URGENCY = 25
MAX_DEPENDENCIES = 10
MAX_TOTAL = MAX_FINANCIAL + MAX_AGE + MAX_MISSING_INFO + MAX_URGENCY + MAX_DEPENDENCIES  # 100


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value > 0
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


@dataclass
class Factor:
    key: str
    label: str
    points: float
    max_points: float
    available: bool
    detail: str


@dataclass
class ScoreResult:
    score: int
    factors: list[Factor] = field(default_factory=list)
    recommended_action: str = ""
    reduction_suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "factors": [
                {
                    "key": f.key,
                    "label": f.label,
                    "points": round(f.points, 1),
                    "max_points": f.max_points,
                    "available": f.available,
                    "detail": f.detail,
                }
                for f in self.factors
            ],
            "recommended_action": self.recommended_action,
            "reduction_suggestions": self.reduction_suggestions,
        }


def _score_financial(amount, percentile_cutoffs: tuple[float, float, float]) -> Factor:
    if amount is None or (isinstance(amount, float) and amount != amount):  # NaN check
        return Factor("financial", "Financial impact", 0, MAX_FINANCIAL, False, "Amount not provided")
    p25, p50, p75 = percentile_cutoffs
    amount = float(amount)
    if amount >= p75:
        pts, detail = MAX_FINANCIAL, f"Top quartile financial exposure (€{amount:,.0f})"
    elif amount >= p50:
        pts, detail = MAX_FINANCIAL * 0.6, f"Above-median financial exposure (€{amount:,.0f})"
    elif amount >= p25:
        pts, detail = MAX_FINANCIAL * 0.32, f"Below-median financial exposure (€{amount:,.0f})"
    else:
        pts, detail = 0, f"Low financial exposure (€{amount:,.0f})"
    return Factor("financial", "Financial impact", pts, MAX_FINANCIAL, True, detail)


def _score_age(days_open) -> Factor:
    if days_open is None or (isinstance(days_open, float) and days_open != days_open):
        return Factor("age", "Case age", 0, MAX_AGE, False, "Days open not provided")
    days_open = float(days_open)
    if days_open >= 30:
        pts, detail = MAX_AGE, f"Open for {days_open:.0f} days"
    elif days_open >= 15:
        pts, detail = MAX_AGE * 0.6, f"Open for {days_open:.0f} days"
    elif days_open >= 5:
        pts, detail = MAX_AGE * 0.3, f"Open for {days_open:.0f} days"
    else:
        pts, detail = 0, f"Open for {days_open:.0f} days"
    return Factor("age", "Case age", pts, MAX_AGE, True, detail)


def _score_missing_info(missing_information) -> Factor:
    if missing_information is None or (isinstance(missing_information, float) and missing_information != missing_information):
        return Factor("missing_info", "Missing information", 0, MAX_MISSING_INFO, False, "Not provided")
    if _truthy(missing_information):
        return Factor("missing_info", "Missing information", MAX_MISSING_INFO, MAX_MISSING_INFO, True, "Required information is missing")
    return Factor("missing_info", "Missing information", 0, MAX_MISSING_INFO, True, "All required information present")


def _score_urgency(urgency) -> Factor:
    if urgency is None or (isinstance(urgency, float) and urgency != urgency) or str(urgency).strip() == "":
        return Factor("urgency", "Urgency", 0, MAX_URGENCY, False, "Not provided")
    u = str(urgency).strip().lower()
    mapping = {
        "high": (MAX_URGENCY, "High urgency"),
        "3": (MAX_URGENCY, "High urgency"),
        "medium": (MAX_URGENCY * 0.48, "Medium urgency"),
        "2": (MAX_URGENCY * 0.48, "Medium urgency"),
        "low": (0, "Low urgency"),
        "1": (0, "Low urgency"),
    }
    pts, detail = mapping.get(u, (MAX_URGENCY * 0.48, f"Urgency reported as '{urgency}'"))
    return Factor("urgency", "Urgency", pts, MAX_URGENCY, True, detail)


def _score_dependencies(dependencies) -> Factor:
    if dependencies is None or (isinstance(dependencies, float) and dependencies != dependencies):
        return Factor("dependencies", "Blocking dependencies", 0, MAX_DEPENDENCIES, False, "Not provided")
    try:
        n = float(dependencies)
    except (TypeError, ValueError):
        n = 1 if _truthy(dependencies) else 0
    if n > 0:
        detail = f"Blocking {int(n)} other case(s)" if n != 1 else "Blocking 1 other case"
        return Factor("dependencies", "Blocking dependencies", MAX_DEPENDENCIES, MAX_DEPENDENCIES, True, detail)
    return Factor("dependencies", "Blocking dependencies", 0, MAX_DEPENDENCIES, True, "No blocking dependencies")


def _recommended_action(score: int) -> str:
    if score >= 75:
        return "Review today"
    if score >= 50:
        return "Review this week"
    if score >= 25:
        return "Monitor"
    return "Low priority — monitor passively"


def _reduction_suggestions(factors: list[Factor]) -> list[str]:
    suggestions = []
    by_key = {f.key: f for f in factors}
    if by_key.get("missing_info") and by_key["missing_info"].points > 0:
        suggestions.append("Complete missing documentation")
    if by_key.get("dependencies") and by_key["dependencies"].points > 0:
        suggestions.append("Confirm and resolve blocking dependencies")
    if by_key.get("age") and by_key["age"].points >= MAX_AGE * 0.6:
        suggestions.append("Expedite review to reduce case age")
    if by_key.get("urgency") and by_key["urgency"].points >= MAX_URGENCY * 0.48:
        suggestions.append("Reassess urgency classification if circumstances have changed")
    if not suggestions:
        suggestions.append("No immediate action reduces this score — case is fundamentally low-risk")
    return suggestions


def score_case(case: dict, percentile_cutoffs: tuple[float, float, float]) -> ScoreResult:
    """Score a single case (a dict of column -> value)."""
    factors = [
        _score_financial(case.get("amount"), percentile_cutoffs),
        _score_age(case.get("days_open")),
        _score_missing_info(case.get("missing_information")),
        _score_urgency(case.get("urgency")),
        _score_dependencies(case.get("dependencies")),
    ]
    total = sum(f.points for f in factors)
    score = max(0, min(100, round(total)))
    return ScoreResult(
        score=score,
        factors=factors,
        recommended_action=_recommended_action(score),
        reduction_suggestions=_reduction_suggestions(factors),
    )


def amount_percentiles(amounts: list[float]) -> tuple[float, float, float]:
    """25th/50th/75th percentile cutoffs used to normalise financial impact
    against this dataset, so the same engine adapts to any domain (a €500
    ticket can be 'high impact' for support cases; a €50,000 claim is
    'high impact' for insurance) without hardcoded thresholds."""
    clean = sorted(a for a in amounts if a is not None and a == a)  # drop None/NaN
    if not clean:
        return (0.0, 0.0, 0.0)

    def pct(p):
        if len(clean) == 1:
            return clean[0]
        k = (len(clean) - 1) * p
        f, c = int(k), min(int(k) + 1, len(clean) - 1)
        if f == c:
            return clean[f]
        return clean[f] + (clean[c] - clean[f]) * (k - f)

    return (pct(0.25), pct(0.50), pct(0.75))


def score_dataset(cases: list[dict]) -> list[dict]:
    """Score a full list of case dicts and return them enriched with
    priority score + explanation, sorted highest priority first."""
    cutoffs = amount_percentiles([c.get("amount") for c in cases])
    results = []
    for case in cases:
        result = score_case(case, cutoffs)
        enriched = dict(case)
        enriched["priority"] = result.to_dict()
        results.append(enriched)
    results.sort(key=lambda c: c["priority"]["score"], reverse=True)
    return results


FAIRNESS_STATEMENT = {
    "model_type": "Rule-based scoring",
    "explainability": "100%",
    "human_review": "Required",
    "automated_decision": False,
    "excluded_attributes": [
        "Name", "Gender", "Ethnicity", "Religion", "Nationality",
        "Health information", "Postcode used as a proxy for personal characteristics",
    ],
    "statement": (
        "The score is a prioritisation recommendation, not an automated decision "
        "about a person. Every point awarded is traced to a named, inspectable "
        "factor. No personal or protected attributes are used as inputs."
    ),
}
