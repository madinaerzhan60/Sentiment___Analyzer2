"""Small Supabase data-access layer. Reads may be cached by the UI; writes never are."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import pandas as pd

from utils.config import ROOT, settings


class DataServiceError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_client():
    if not settings.supabase_configured:
        raise DataServiceError("Supabase is not configured.")
    try:
        from supabase import create_client
        return create_client(settings.supabase_url, settings.supabase_key)
    except Exception as exc:
        raise DataServiceError(f"Could not initialize Supabase: {exc}") from exc


def fetch_reviews() -> pd.DataFrame:
    """Return reviews; use bundled analyzed data only when Supabase is unconfigured."""
    if not settings.supabase_configured:
        try:
            return normalize_reviews(pd.read_csv(ROOT / "data" / "sample_reviews.csv"))
        except Exception as exc:
            raise DataServiceError(f"Could not load demo data: {exc}") from exc
    try:
        result = get_client().table("reviews").select("*").order("published_at", desc=True).execute()
        return normalize_reviews(pd.DataFrame(result.data or []))
    except Exception as exc:
        raise DataServiceError(f"Could not load reviews from Supabase: {exc}") from exc


def normalize_reviews(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    defaults = {
        "id": "", "source": "Unknown", "author": "Anonymous", "rating": 0,
        "review_text": "", "source_url": "", "external_id": "",
        "published_at": pd.NaT, "created_at": pd.NaT,
        "sentiment": "", "category": "other", "severity": "",
        "risk_score": 0, "summary": "", "recommendation": "",
        "suggested_response": "", "analysis_status": "pending",
        "action_status": "pending_review", "analysis_provider": "",
    }
    for column, default in defaults.items():
        if column not in df:
            df[column] = default
    for column in ("published_at", "created_at"):
        df[column] = pd.to_datetime(df[column], errors="coerce", utc=True, format="mixed")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0).astype(int)
    df["risk_score"] = pd.to_numeric(df["risk_score"], errors="coerce").fillna(0).clip(0, 100)
    return df


def insert_reviews(rows: list[dict[str, Any]]) -> int:
    if not settings.supabase_configured:
        raise DataServiceError("Configure Supabase before importing reviews.")
    try:
        client = get_client()
        deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
        without_external: list[dict[str, Any]] = []
        for row in rows:
            external_id = str(row.get("external_id") or "").strip()
            if external_id:
                deduplicated[(str(row.get("source", "")), external_id)] = row
            else:
                without_external.append(row)

        new_rows: list[dict[str, Any]] = []
        for source in {key[0] for key in deduplicated}:
            source_rows = {key[1]: value for key, value in deduplicated.items() if key[0] == source}
            existing = (client.table("reviews").select("id,external_id").eq("source", source)
                        .in_("external_id", list(source_rows)).execute())
            existing_by_external = {str(item["external_id"]): str(item["id"]) for item in (existing.data or [])}
            for external_id, row in source_rows.items():
                if external_id in existing_by_external:
                    raw_update = {key: value for key, value in row.items() if key not in {
                        "sentiment", "category", "severity", "risk_score", "summary",
                        "recommendation", "suggested_response", "analysis_status",
                        "analysis_provider", "analyzed_at", "action_status",
                    }}
                    client.table("reviews").update(raw_update).eq("id", existing_by_external[external_id]).execute()
                else:
                    new_rows.append(row)

        pending = new_rows + without_external
        if pending:
            client.table("reviews").upsert(
                pending, on_conflict="source,author,published_at,review_text"
            ).execute()
        return len(deduplicated) + len(without_external)
    except Exception as exc:
        raise DataServiceError(f"Could not import reviews: {exc}") from exc


def claim_review(review_id: str) -> bool:
    """Atomically-ish claim a pending/failed row before an AI call."""
    try:
        result = (get_client().table("reviews").update({"analysis_status": "processing"})
                  .eq("id", review_id).in_("analysis_status", ["pending", "failed"]).execute())
        return bool(result.data)
    except Exception as exc:
        raise DataServiceError(f"Could not claim review {review_id}: {exc}") from exc


def save_analysis(review_id: str, analysis: dict[str, Any], provider: str) -> None:
    from datetime import datetime, timezone
    payload = {**analysis, "analysis_status": "done", "analysis_provider": provider,
               "analyzed_at": datetime.now(timezone.utc).isoformat()}
    try:
        get_client().table("reviews").update(payload).eq("id", review_id).execute()
    except Exception as exc:
        raise DataServiceError(f"Could not save analysis for {review_id}: {exc}") from exc


def mark_analysis_failed(review_id: str) -> None:
    try:
        get_client().table("reviews").update({"analysis_status": "failed"}).eq("id", review_id).execute()
    except Exception as exc:
        raise DataServiceError(f"Could not mark analysis failed for {review_id}: {exc}") from exc


def update_action_status(review_id: str, status: str) -> None:
    if status not in {"pending_review", "approved", "rejected", "resolved"}:
        raise ValueError("Invalid action status")
    if not settings.supabase_configured:
        raise DataServiceError("Actions are read-only in demo mode. Configure Supabase to save decisions.")
    try:
        get_client().table("reviews").update({"action_status": status}).eq("id", review_id).execute()
    except Exception as exc:
        raise DataServiceError(f"Could not update action status: {exc}") from exc
