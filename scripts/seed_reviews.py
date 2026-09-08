"""Import raw or pre-analyzed CSV reviews into Supabase."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.supabase_service import DataServiceError, insert_reviews  # noqa: E402
from utils.config import ROOT  # noqa: E402


def prepare(path: Path, raw_only: bool) -> list[dict]:
    df = pd.read_csv(path)
    required = {"source", "author", "rating", "review_text", "published_at"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")
    allowed = {
        "source", "author", "rating", "review_text", "published_at", "sentiment",
        "category", "severity", "risk_score", "summary", "recommendation",
        "suggested_response", "analysis_status", "action_status", "analysis_provider",
    }
    df = df[[c for c in df.columns if c in allowed]].where(pd.notna(df), None)
    if raw_only:
        for col in ["sentiment", "category", "severity", "risk_score", "summary",
                    "recommendation", "suggested_response", "analysis_provider"]:
            if col in df: df[col] = None
        df["analysis_status"] = "pending"
        df["action_status"] = "pending_review"
    return df.to_dict(orient="records")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import CSV reviews into Supabase")
    parser.add_argument("path", nargs="?", type=Path, default=ROOT / "data" / "sample_reviews.csv")
    parser.add_argument("--raw-only", action="store_true", help="Discard supplied analysis and queue AI analysis")
    args = parser.parse_args()
    try:
        count = insert_reviews(prepare(args.path, args.raw_only))
        print(f"Imported {count} reviews.")
        return 0
    except (ValueError, DataServiceError, FileNotFoundError) as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

