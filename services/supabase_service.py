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
    """Read every page. Never substitute sample data for production failures."""
    if not settings.supabase_configured:
        raise DataServiceError("Supabase is not configured.")
    try:
        rows = []
        while True:
            page = (get_client().table("reviews").select("*").order("id")
                    .range(len(rows), len(rows) + 499).execute()).data or []
            rows.extend(page)
            if len(page) < 500:
                break
        return normalize_reviews(pd.DataFrame(rows))
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
    """Insert only new identities; preserve existing originals and saved analysis."""
    import hashlib
    if not settings.supabase_configured:
        raise DataServiceError("Configure Supabase before importing reviews.")
    try:
        existing = fetch_reviews()
        identities = {(str(r.source), str(r.external_id)) for r in existing.itertuples() if r.external_id}
        def identity(row):
            date = pd.to_datetime(row.get("published_at"), errors="coerce", utc=True)
            return (str(row.get("source", "")), str(row.get("author") or "Anonymous"),
                    str(row.get("review_text", "")).strip(), date.isoformat() if pd.notna(date) else "")
        raw_keys = {identity(r) for r in existing.to_dict("records")}
        count = 0
        for original in rows:
            row = dict(original)
            raw_key = identity(row)
            external = str(row.get("external_id") or "").strip()
            if not external:
                external = "sha256:" + hashlib.sha256(json_identity(raw_key).encode()).hexdigest()
            key = (row["source"], external)
            if key in identities or raw_key in raw_keys:
                continue
            row["external_id"] = external
            try:
                result = get_client().table("reviews").insert(row).execute()
                count += len(result.data or [])
            except Exception as exc:
                # A concurrent import may win the unique constraint. Never overwrite it.
                if str(getattr(exc, "code", "")) != "23505":
                    raise
            identities.add(key)
            raw_keys.add(raw_key)
        return count
    except Exception as exc:
        raise DataServiceError("Could not import reviews. Check database schema and permissions.") from exc


def json_identity(value) -> str:
    import json
    return json.dumps(value, ensure_ascii=False)


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
