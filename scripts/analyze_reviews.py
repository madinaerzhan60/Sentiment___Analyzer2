"""One-time batch analysis of pending Supabase reviews."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.ai_service import AnalysisUnavailable, analyze_review  # noqa: E402
from services.supabase_service import (  # noqa: E402
    DataServiceError, claim_review, fetch_reviews, mark_analysis_failed, save_analysis,
)


def main() -> int:
    try:
        reviews = fetch_reviews()
    except DataServiceError as exc:
        print(f"Load failed: {exc}", file=sys.stderr)
        return 1
    pending = reviews[reviews["analysis_status"].isin(["pending", "failed"])]
    if pending.empty:
        print("No reviews need analysis.")
        return 0
    done = failed = 0
    for _, review in pending.iterrows():
        review_id = str(review["id"])
        try:
            if not claim_review(review_id):
                continue
            result, provider = analyze_review(str(review["review_text"]), int(review["rating"]), str(review["source"]))
            save_analysis(review_id, result, provider)
            done += 1
            print(f"Analyzed {review_id} with {provider}.")
        except (AnalysisUnavailable, DataServiceError) as exc:
            failed += 1
            try: mark_analysis_failed(review_id)
            except DataServiceError: pass
            print(f"Failed {review_id}: {exc}", file=sys.stderr)
    print(f"Completed: {done}; failed: {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
