"""Private management UI: consistent snapshots and explicit imports."""
from datetime import date
from threading import Lock
from threading import Thread
from urllib.parse import urlparse
import csv
import io
import json
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from services.analytics_service import brand_health_score, issue_stats, platform_stats, trend
from services.pipeline_service import analyze_missing_confidence, analyze_pending
from services.supabase_service import DataServiceError, fetch_reviews, insert_reviews
from services.import_service import ImportServiceError, collect_linkedin, save_collected
from utils.config import ROOT, settings

app = FastAPI(title="Sentiment Analyzer", version="3.0.0")
app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")
app.mount("/fonts", StaticFiles(directory=ROOT / "TTF"), name="fonts")
write_lock = Lock()
SOURCES = ["Google", "2GIS", "Yandex", "Instagram", "Facebook", "LinkedIn", "CSV"]
TOPICS = {"response_time": "Response time", "staff_behavior": "Staff conduct", "service_quality": "Service quality", "product_quality": "Product quality", "pricing": "Pricing", "communication": "Communication", "waiting_time": "Waiting time", "other": "Other feedback"}

def _backfill_confidence() -> None:
    """One-time background enrichment for saved analyses that predate confidence."""
    if not settings.supabase_configured or not settings.ai_configured:
        return
    try:
        while True:
            result = analyze_missing_confidence(limit=50)
            if result["total"] == 0:
                break
    except Exception:
        # The dashboard remains available if an AI provider or the migration is unavailable.
        return

@app.on_event("startup")
def start_confidence_backfill() -> None:
    Thread(target=_backfill_confidence, daemon=True).start()

def records(df):
    return json.loads(df.to_json(orient="records", date_format="iso"))

def period_filter(df, days=None, start=None, end=None):
    now = pd.Timestamp.now(tz="UTC")
    if start and end and start > end:
        raise HTTPException(400, "Start date must be before end date.")
    if days is None and start is None and end is None:
        return df.copy()
    dates = df["published_at"]
    mask = dates.le(now)
    if days:
        mask &= dates.ge(now - pd.Timedelta(days=days))
    if start:
        mask &= dates.ge(pd.Timestamp(start, tz="UTC"))
    if end:
        mask &= dates.lt(pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1))
    return df[mask].copy()

def snapshot(days=None, start=None, end=None):
    try:
        raw = fetch_reviews()
    except DataServiceError as exc:
        raise HTTPException(503, "Could not load reviews. Check the database connection in Settings and try again.") from exc
    excluded = 0
    if settings.grata_2gis_firm_id and not raw.empty:
        verified = ~raw.source.eq("2GIS") | raw.source_url.fillna("").str.contains(settings.grata_2gis_firm_id, regex=False)
        excluded = int((~verified).sum())
        raw = raw[verified].copy()
    data = period_filter(raw, days, start, end)
    analyzed = data[data.analysis_status.eq("done") & data.sentiment.isin(["positive", "neutral", "negative"])].copy()
    critical = analyzed.severity.eq("critical") | analyzed.risk_score.ge(85)
    attention = analyzed.sentiment.eq("negative") | analyzed.severity.isin(["high", "critical"]) | analyzed.risk_score.ge(85)
    now = pd.Timestamp.now(tz="UTC")
    all_done = raw[raw.analysis_status.eq("done")]
    current = all_done[all_done.published_at.ge(now - pd.Timedelta(days=30)) & all_done.published_at.le(now)]
    previous = all_done[all_done.published_at.ge(now - pd.Timedelta(days=60)) & all_done.published_at.lt(now - pd.Timedelta(days=30))]
    topics = issue_stats(analyzed)
    if not topics.empty:
        topics["issue"] = topics.category.map(TOPICS).fillna("Other feedback")
        topics = topics.sort_values("reviews", ascending=False)
    positive = analyzed[analyzed.sentiment.eq("positive")].groupby("category").size().reset_index(name="reviews")
    positive["issue"] = positive.category.map(TOPICS).fillna("Other feedback")
    return {
        "items": records(data.sort_values("published_at", ascending=False, na_position="last")),
        "meta": {"checked_at": now.isoformat(), "excluded_unverified": excluded, "latest": None if raw.published_at.dropna().empty else raw.published_at.max().isoformat(), "total_raw": len(raw), "unknown_dates": int(raw.published_at.isna().sum())},
        "metrics": {"total": len(data), "analyzed": len(analyzed), "health": brand_health_score(analyzed) if len(analyzed) else None, "health_delta": brand_health_score(current) - brand_health_score(previous) if len(current) and len(previous) else None, "attention": int(attention.sum()), "critical": int(critical.sum()), "active_sources": int(data.source.nunique())},
        "sentiments": {s: int(analyzed.sentiment.eq(s).sum()) for s in ["positive", "neutral", "negative"]},
        "issues": records(topics), "positive_themes": records(positive.sort_values("reviews", ascending=False)),
        "platforms": records(platform_stats(analyzed)), "trend": records(trend(analyzed)),
        "volume": records(data.dropna(subset=["published_at"]).assign(month=lambda x: x.published_at.dt.strftime("%Y-%m")).groupby("month").size().reset_index(name="reviews")),
        "sources": [{"name": s, "count": int(data.source.eq(s).sum()), "total": int(raw.source.eq(s).sum()), "latest": None if raw.loc[raw.source.eq(s), "created_at"].dropna().empty else raw.loc[raw.source.eq(s), "created_at"].max().isoformat(), "status": "Manual Import"} for s in dict.fromkeys(SOURCES + raw.source.tolist())],
        "config": {"supabase": settings.supabase_configured, "ai": settings.ai_configured},
    }

@app.get("/")
def index():
    return FileResponse(ROOT / "frontend" / "index.html")

@app.get("/api/dashboard")
def dashboard(days: int | None = Query(None, ge=1, le=3650), start: date | None = None, end: date | None = None):
    return snapshot(days, start, end)

@app.get("/api/reviews")
def reviews(days: int | None = Query(None, ge=1, le=3650), start: date | None = None, end: date | None = None):
    return {"items": snapshot(days, start, end)["items"]}

@app.get("/api/config")
def config():
    return {"supabase": settings.supabase_configured, "ai": settings.ai_configured}

@app.post("/api/analyze")
def analyze(limit: int = Query(50, ge=1, le=500)):
    if not settings.supabase_configured or not settings.ai_configured:
        raise HTTPException(400, "Configure the database and an AI provider on the server first.")
    if not write_lock.acquire(blocking=False):
        raise HTTPException(409, "Another import or analysis is running. Please wait.")
    try:
        result = analyze_pending(limit)
        return {k: result[k] for k in ("total", "done", "failed")}
    except Exception as exc:
        raise HTTPException(502, "Analysis could not finish. Saved reviews are safe; try again later.") from exc
    finally:
        write_lock.release()

@app.post("/api/analyze-confidence")
def analyze_confidence(limit: int = Query(50, ge=1, le=500)):
    if not settings.supabase_configured or not settings.ai_configured:
        raise HTTPException(400, "Configure the database and an AI provider on the server first.")
    if not write_lock.acquire(blocking=False):
        raise HTTPException(409, "Another import or analysis is running. Please wait.")
    try:
        result = analyze_missing_confidence(limit)
        return {k: result[k] for k in ("total", "done", "failed")}
    except Exception as exc:
        raise HTTPException(502, "Confidence analysis could not finish. Existing review analysis remains unchanged.") from exc
    finally:
        write_lock.release()

class CSVImport(BaseModel):
    content: str = Field(max_length=2_000_000)

def parse_csv(content):
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    if not {"source", "review_text"}.issubset(reader.fieldnames or []):
        raise HTTPException(400, "CSV requires source and review_text columns.")
    rows = []
    for number, item in enumerate(reader, 2):
        if number > 1001:
            raise HTTPException(400, "Import at most 1,000 rows at a time.")
        source = (item.get("source") or "").strip()
        source = {"Google Maps": "Google", "Yandex Maps": "Yandex", "CSV Import": "CSV"}.get(source, source)
        text = (item.get("review_text") or "").strip()
        if source not in SOURCES or not text or len(text) > 20000:
            raise HTTPException(400, f"Row {number}: choose a supported source and provide review text (up to 20,000 characters).")
        value = (item.get("published_at") or item.get("review_date") or "").strip()
        parsed = pd.to_datetime(value, errors="coerce", utc=True) if value else pd.NaT
        if value and (pd.isna(parsed) or parsed > pd.Timestamp.now(tz="UTC")):
            raise HTTPException(400, f"Row {number}: review date is invalid or in the future.")
        try:
            rating = float(item.get("rating") or 0)
            if not rating.is_integer() or not 0 <= rating <= 5:
                raise ValueError()
        except ValueError:
            raise HTTPException(400, f"Row {number}: rating must be a whole number from 0 to 5.")
        url = (item.get("source_url") or "").strip()
        if url and (urlparse(url).scheme not in {"https", "http"} or not urlparse(url).hostname):
            raise HTTPException(400, f"Row {number}: original URL must use HTTP or HTTPS.")
        rows.append({"source": source, "review_text": text, "author": (item.get("author") or "Anonymous").strip(), "published_at": parsed.isoformat() if pd.notna(parsed) else None, "rating": int(rating), "source_url": url or None, "external_id": item.get("external_id") or None, "analysis_status": "pending"})
    if not rows:
        raise HTTPException(400, "The CSV contains no reviews.")
    return rows

@app.post("/api/import")
def import_csv(request: CSVImport):
    rows = parse_csv(request.content)
    if not write_lock.acquire(blocking=False):
        raise HTTPException(409, "Another import or analysis is running. Please wait.")
    try:
        saved = insert_reviews(rows)
        return {"found": len(rows), "saved": saved, "duplicates": len(rows) - saved}
    except DataServiceError as exc:
        raise HTTPException(502, "Import could not finish. Check database permissions and the optional-date/Yandex migration. Retry safely; duplicates are skipped.") from exc
    finally:
        write_lock.release()

@app.post("/api/sync")
def sync():
    raise HTTPException(409, "Automatic platform collection is not enabled. Import an authorized CSV export from Sources.")

class LinkedInCollection(BaseModel):
    company_url: str = Field(min_length=20, max_length=500)
    limit: int = Field(default=70, ge=1, le=70)

@app.post("/api/collect/linkedin")
def collect_linkedin_comments(request: LinkedInCollection):
    if not settings.supabase_configured:
        raise HTTPException(400, "Configure Supabase first.")
    if not settings.apify_token:
        raise HTTPException(400, "Add APIFY_TOKEN on the server first.")
    parsed = urlparse(request.company_url)
    if parsed.hostname not in {"www.linkedin.com", "linkedin.com"} or "/company/" not in parsed.path:
        raise HTTPException(400, "Use a public LinkedIn company-page URL.")
    if not write_lock.acquire(blocking=False):
        raise HTTPException(409, "Another import or analysis is running. Please wait.")
    try:
        rows = collect_linkedin([request.company_url], request.limit)
        saved = save_collected(rows)
        return {"found": len(rows), "saved": saved, "duplicates": len(rows) - saved}
    except ImportServiceError as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        write_lock.release()

@app.get("/api/health")
def health():
    return {"ok": True}
