"""
ML-comparison mode.

ClearQueue's primary scoring engine (scoring.py) is rule-based by design —
every point is named and traceable. This module adds an optional, clearly
separate comparison: train a small gradient-boosted model to reproduce the
rule engine's own scores from the same raw fields, then explain *that*
model's predictions with SHAP.

The point is not "the ML model is better." It's a controlled comparison of
two explainability approaches on the same data: does a black-box model,
explained after the fact with a standard technique, actually agree with a
rule engine a human can read line by line? Where the two disagree is often
more interesting than where they agree, and is exactly the kind of
discrepancy a responsible deployment would want surfaced, not hidden.

This model is NOT trained on real historical outcomes — there aren't any
for a synthetic/demo dataset. It's trained to imitate the rule engine, so
its SHAP attributions can be compared apples-to-apples against
scoring.py's own factor breakdown for the same cases.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:  # pragma: no cover - environment-dependent
    SHAP_AVAILABLE = False


class MLCompareError(Exception):
    """Raised for any condition that prevents running the comparison."""


FEATURE_NAMES = ["amount", "days_open", "missing_information", "urgency_score", "dependencies"]
FEATURE_LABELS = {
    "amount": "Financial impact",
    "days_open": "Case age",
    "missing_information": "Missing information",
    "urgency_score": "Urgency",
    "dependencies": "Blocking dependencies",
}

MIN_CASES_TO_TRAIN = 6


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value > 0
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _urgency_to_score(urgency) -> float:
    if urgency is None:
        return 1.0
    u = str(urgency).strip().lower()
    return {"low": 0.0, "medium": 1.0, "high": 2.0}.get(u, 1.0)


def _to_feature_row(case: dict) -> list[float]:
    amount = case.get("amount")
    days_open = case.get("days_open")
    return [
        float(amount) if amount is not None else 0.0,
        float(days_open) if days_open is not None else 0.0,
        1.0 if _truthy(case.get("missing_information")) else 0.0,
        _urgency_to_score(case.get("urgency")),
        float(case.get("dependencies")) if case.get("dependencies") is not None else 0.0,
    ]


def run_ml_comparison(scored_cases: list[dict]) -> dict:
    """scored_cases: list of case dicts, each already carrying a 'priority'
    key produced by scoring.score_dataset (i.e. the rule-based result)."""
    if not SHAP_AVAILABLE:
        raise MLCompareError(
            "The 'shap' package isn't installed in this environment. Add "
            "'shap' to requirements.txt and reinstall to enable this mode."
        )
    usable = [c for c in scored_cases if c.get("priority") and "score" in c["priority"]]
    if len(usable) < MIN_CASES_TO_TRAIN:
        raise MLCompareError(
            f"Need at least {MIN_CASES_TO_TRAIN} scored cases to train a "
            "meaningful comparison model — load a larger dataset first."
        )

    X = np.array([_to_feature_row(c) for c in usable])
    y = np.array([c["priority"]["score"] for c in usable], dtype=float)

    model = GradientBoostingRegressor(n_estimators=60, max_depth=3, random_state=42)
    model.fit(X, y)
    predictions = model.predict(X)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    base_value = float(np.ravel(explainer.expected_value)[0])

    abs_importance = np.abs(shap_values).mean(axis=0)
    total = abs_importance.sum()
    importance_pct = (abs_importance / total * 100) if total > 0 else abs_importance

    results = []
    for i, case in enumerate(usable):
        contributions = sorted(
            [
                {
                    "feature": FEATURE_NAMES[j],
                    "label": FEATURE_LABELS[FEATURE_NAMES[j]],
                    "shap_value": round(float(shap_values[i][j]), 2),
                }
                for j in range(len(FEATURE_NAMES))
            ],
            key=lambda d: abs(d["shap_value"]),
            reverse=True,
        )
        results.append({
            "case_id": case.get("case_id"),
            "rule_based_score": case["priority"]["score"],
            "ml_predicted_score": round(float(predictions[i]), 1),
            "difference": round(float(predictions[i]) - case["priority"]["score"], 1),
            "base_value": round(base_value, 1),
            "shap_contributions": contributions,
        })

    # Surface the biggest rule-vs-ML disagreements first — that's the
    # actually interesting part of this comparison for a reviewer.
    results.sort(key=lambda r: abs(r["difference"]), reverse=True)

    return {
        "cases": results,
        "global_feature_importance": [
            {
                "feature": FEATURE_NAMES[j],
                "label": FEATURE_LABELS[FEATURE_NAMES[j]],
                "importance_pct": round(float(importance_pct[j]), 1),
            }
            for j in range(len(FEATURE_NAMES))
        ],
        "note": (
            "This model was trained to reproduce the rule-based engine's own "
            "scores from the same raw fields — a controlled comparison of "
            "explainability techniques, not a prediction trained on real "
            "outcomes. Cases are sorted by how much the two approaches "
            "disagree, largest disagreement first."
        ),
    }
