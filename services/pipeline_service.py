"""Orchestrate persistent one-time analysis outside Streamlit caching."""
from __future__ import annotations

from collections.abc import Callable

from services.ai_service import AnalysisUnavailable, analyze_review
from services.supabase_service import DataServiceError, claim_review, fetch_reviews, mark_analysis_failed, save_analysis


def analyze_pending(limit: int = 50, progress: Callable[[int, int], None] | None = None) -> dict:
    reviews = fetch_reviews()
    queue = reviews[reviews["analysis_status"].isin(["pending", "failed"])].head(limit)
    result = {"total": len(queue), "done": 0, "failed": 0, "errors": []}
    for position, (_, review) in enumerate(queue.iterrows(), start=1):
        review_id = str(review["id"])
        try:
            if not claim_review(review_id):
                continue
            analysis, provider = analyze_review(str(review["review_text"]), int(review["rating"]), str(review["source"]))
            save_analysis(review_id, analysis, provider)
            result["done"] += 1
        except (AnalysisUnavailable, DataServiceError) as exc:
            result["failed"] += 1
            result["errors"].append(str(exc))
            try:
                mark_analysis_failed(review_id)
            except DataServiceError:
                pass
        if progress:
            progress(position, len(queue))
    return result
