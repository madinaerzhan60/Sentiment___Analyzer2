"""Deterministic, explainable management analytics."""
from __future__ import annotations

import pandas as pd

CATEGORY_LABELS = {
    "response_time": "Скорость ответа", "staff_behavior": "Поведение сотрудников",
    "service_quality": "Качество обслуживания", "product_quality": "Качество продукта",
    "pricing": "Цены", "communication": "Общение",
    "waiting_time": "Время ожидания", "other": "Другое",
}

# Star-rated review platforms reflect an explicit client experience. Short social
# reactions are still monitored, but have a deliberately smaller impact on the
# executive score.
SOURCE_WEIGHTS = {"2GIS": 1.0, "Google": 1.0, "Yandex": 1.0, "CSV": 1.0,
                  "Instagram": 0.05, "Facebook": 0.05, "LinkedIn": 0.05}


def analyzed(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["analysis_status"].eq("done")].copy() if not df.empty else df.copy()


def brand_health_score(df: pd.DataFrame) -> int:
    """Weighted score: review platforms count fully; social comments count at 5%."""
    data = analyzed(df)
    if data.empty:
        return 0
    weights = data["source"].map(SOURCE_WEIGHTS).fillna(1.0)
    total_weight = weights.sum()
    negative_share = (weights * data["sentiment"].eq("negative")).sum() / total_weight
    critical_share = (weights * (data["severity"].eq("critical") | data["risk_score"].ge(85))).sum() / total_weight
    avg_risk = (weights * data["risk_score"]).sum() / total_weight / 100
    return round(max(0, min(100, 100 - 45 * negative_share - 25 * critical_share - 30 * avg_risk)))


def brand_health_breakdown(df: pd.DataFrame) -> dict:
    """Return the exact, human-readable components used for the current score."""
    data = analyzed(df)
    if data.empty:
        return {"rated_reviews": 0, "social_comments": 0, "weighted_records": 0,
                "negative_penalty": 0, "critical_penalty": 0, "risk_penalty": 0, "score": None}
    weights = data["source"].map(SOURCE_WEIGHTS).fillna(1.0)
    total_weight = weights.sum()
    negative_penalty = 45 * (weights * data["sentiment"].eq("negative")).sum() / total_weight
    critical_penalty = 25 * (weights * (data["severity"].eq("critical") | data["risk_score"].ge(85))).sum() / total_weight
    risk_penalty = 30 * (weights * data["risk_score"]).sum() / total_weight / 100
    social = data["source"].isin(["Instagram", "Facebook", "LinkedIn"])
    return {
        "rated_reviews": int((~social).sum()), "social_comments": int(social.sum()),
        "weighted_records": round(float(total_weight), 2),
        "negative_penalty": round(float(negative_penalty), 1),
        "critical_penalty": round(float(critical_penalty), 1),
        "risk_penalty": round(float(risk_penalty), 1),
        "score": brand_health_score(data),
    }


def kpis(df: pd.DataFrame) -> dict:
    data = analyzed(df)
    total = len(data)
    negative = int(data["sentiment"].eq("negative").sum()) if total else 0
    critical = int(data["severity"].eq("critical").sum()) if total else 0
    return {"health": brand_health_score(data), "total": total, "negative": negative,
            "negative_pct": (negative / total * 100 if total else 0), "critical": critical}


def trend(df: pd.DataFrame) -> pd.DataFrame:
    data = analyzed(df).dropna(subset=["published_at"])
    if data.empty:
        return pd.DataFrame(columns=["date", "sentiment", "reviews"])
    data["date"] = data["published_at"].dt.date
    return data.groupby(["date", "sentiment"], observed=True).size().rename("reviews").reset_index()


def platform_stats(df: pd.DataFrame) -> pd.DataFrame:
    data = analyzed(df)
    if data.empty:
        return pd.DataFrame(columns=["source", "reviews", "negative_pct"])
    return (data.groupby("source").agg(
        reviews=("id", "size"), negative_pct=("sentiment", lambda s: s.eq("negative").mean() * 100)
    ).reset_index().sort_values("reviews", ascending=False))


def issue_stats(df: pd.DataFrame) -> pd.DataFrame:
    data = analyzed(df)
    complaints = data[data["sentiment"].eq("negative")]
    if complaints.empty:
        return pd.DataFrame(columns=["category", "issue", "reviews", "percentage"])
    result = complaints.groupby("category").size().rename("reviews").reset_index()
    result["percentage"] = result["reviews"] / len(complaints) * 100
    result["issue"] = result["category"].map(CATEGORY_LABELS).fillna("Other")
    return result.sort_values("reviews", ascending=True)


def issue_platform_matrix(df: pd.DataFrame) -> pd.DataFrame:
    data = analyzed(df)
    data = data[data["sentiment"].eq("negative")].copy()
    if data.empty:
        return pd.DataFrame()
    matrix = pd.crosstab(data["category"], data["source"])
    matrix.index = matrix.index.map(lambda x: CATEGORY_LABELS.get(x, "Other"))
    return matrix


def key_findings(df: pd.DataFrame) -> list[str]:
    data = analyzed(df)
    if data.empty:
        return ["No analyzed reviews are available for this period."]
    findings: list[str] = []
    platforms = platform_stats(data)
    if not platforms.empty:
        row = platforms.sort_values(["negative_pct", "reviews"], ascending=False).iloc[0]
        findings.append(f"На площадке {row.source} самая высокая доля негатива — {row.negative_pct:.0f}%.")
    issues = issue_stats(data)
    if not issues.empty:
        row = issues.iloc[-1]
        findings.append(f"Самая частая проблема — «{row.issue.lower()}» ({int(row.reviews)} отзывов).")
    staff = data[(data["sentiment"] == "negative") & (data["category"] == "staff_behavior")]
    if not staff.empty:
        top = staff["source"].value_counts().index[0]
        findings.append(f"Больше всего жалоб на сотрудников поступило с площадки {top}.")
    critical = int(data["severity"].eq("critical").sum())
    findings.append(f"Критических случаев за выбранный период: {critical}.")
    return findings


def executive_summary(df: pd.DataFrame) -> dict:
    stats = kpis(df)
    risk = "НИЗКИЙ РИСК" if stats["health"] >= 75 else "СРЕДНИЙ РИСК" if stats["health"] >= 50 else "ВЫСОКИЙ РИСК"
    issues = issue_stats(df)
    priority = "Продолжать следить за отзывами и сохранять сильные стороны обслуживания."
    if not issues.empty:
        priority = f"В первую очередь улучшить направление «{issues.iloc[-1].issue.lower()}» и разобрать рискованные обращения."
    return {"status": risk, "findings": key_findings(df)[:3], "priority": priority}


def risk_factors(row: pd.Series) -> list[str]:
    factors = []
    if row.get("sentiment") == "negative": factors.append("негативная тональность")
    if 0 < int(row.get("rating", 0)) <= 2: factors.append(f"оценка {int(row.rating)}/5")
    if row.get("severity") in {"high", "critical"}: factors.append("серьёзная жалоба")
    if row.get("category") in {"response_time", "staff_behavior", "communication"}:
        factors.append(CATEGORY_LABELS.get(row.category, row.category).lower())
    published = row.get("published_at")
    if pd.notna(published) and published >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7):
        factors.append("свежий отзыв")
    return factors or ["контекст, определённый AI"]
