"""Import real public feedback through configurable Apify actors."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
from typing import Any

import pandas as pd
import requests

from services.supabase_service import DataServiceError, insert_reviews
from utils.config import settings


class ImportServiceError(RuntimeError):
    pass


def _actor_endpoint(actor_id: str) -> str:
    actor = actor_id.replace("/", "~")
    return f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"


def _run_actor(actor_id: str, payload: dict[str, Any]) -> list[dict]:
    if not settings.apify_token:
        raise ImportServiceError("Добавьте APIFY_TOKEN в файл .env.")
    try:
        response = requests.post(
            _actor_endpoint(actor_id), params={"timeout": 240},
            headers={"Authorization": f"Bearer {settings.apify_token}"}, json=payload, timeout=270,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError("Сервис вернул неожиданный формат данных")
        return data
    except requests.Timeout as exc:
        raise ImportServiceError("Сбор занял слишком много времени. Попробуйте ещё раз.") from exc
    except (requests.RequestException, ValueError) as exc:
        detail = ""
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            detail = f" (HTTP {exc.response.status_code})"
        raise ImportServiceError(f"Не удалось получить данные из Apify{detail}.") from exc


def _pick(item: dict, *keys, default=None):
    for key in keys:
        value = item.get(key)
        if value is not None and value != "":
            return value
    return default


def _date(item: dict) -> str:
    value = _pick(item, "commentPublishTimeIso", "dateCreated", "timestamp", "createdAt", "created_time", "publishTimeIso", "time", "date")
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return (parsed if pd.notna(parsed) else pd.Timestamp.now(tz="UTC")).isoformat()


def _normalize(items: list[dict], source: str, fallback_url: str) -> list[dict]:
    rows: list[dict] = []
    actor_errors: list[str] = []
    for item in items:
        if item.get("error"):
            actor_errors.append(str(item["error"]))
        text = str(_pick(item, "commentText", "text", "comment", "message", "reviewText", default="")).strip()
        if not text:
            continue
        author = str(_pick(item, "commentAuthorName", "authorName", "ownerUsername", "username", "profileName", "name", default="Анонимный автор"))
        external = str(_pick(item, "commentId", "reviewId", "id", "pk", default="")).strip()
        if not external:
            external = hashlib.sha256(f"{source}|{author}|{text}".encode()).hexdigest()[:32]
        raw_rating = _pick(item, "rating", "reviewRating", "stars", default=0)
        try: rating = max(0, min(5, int(float(raw_rating))))
        except (TypeError, ValueError): rating = 0
        rows.append({
            "source": source, "author": author[:200], "rating": rating,
            "review_text": text, "published_at": _date(item),
            "external_id": external, "source_url": str(_pick(item, "commentPermalink", "permalink", "url", "postUrl", "facebookUrl", "inputUrl", "firmUrl", default=fallback_url)),
            "analysis_status": "pending", "action_status": "pending_review",
        })
    if not rows and actor_errors:
        detail = actor_errors[0]
        raise ImportServiceError(
            f"{source} не дал доступ к комментариям ({detail}). "
            "Попробуйте ссылки на отдельные публичные публикации или повторите сбор позже."
        )
    return rows


def _with_nested_replies(items: list[dict]) -> list[dict]:
    """Flatten reply objects while retaining their parent post context."""
    expanded: list[dict] = []
    for item in items:
        expanded.append(item)
        replies = _pick(item, "commentReplies", "replies", "comments", default=[])
        if not isinstance(replies, list):
            continue
        for reply in replies:
            if isinstance(reply, dict):
                expanded.append({**item, **reply, "commentReplies": [], "replies": [], "comments": []})
    return expanded


def collect_2gis(url: str, limit: int = 30) -> list[dict]:
    match = re.search(r"/firm/(\d+)", url)
    if not match:
        raise ImportServiceError("Используйте полную ссылку 2GIS вида 2gis.kz/.../firm/123456/tab/reviews.")
    firm_id = match.group(1)
    items = _run_actor(settings.apify_2gis_actor, {
        "firmIds": [firm_id], "urls": [], "maxItemsPerFirm": limit, "withTextOnly": True,
        "sortBy": "date_created", "includeRawData": False,
    })
    rows = _normalize(items, "2GIS", url)
    verified = [row for row in rows if firm_id in str(row.get("source_url", ""))]
    if not verified and rows:
        raise ImportServiceError("Сборщик вернул данные другой организации; импорт остановлен.")
    return verified[:limit]


def collect_instagram(post_urls: list[str], limit: int = 500, max_posts: int = 50) -> list[dict]:
    direct_post_urls = [url for url in post_urls if re.search(r"instagram\.com/(?:p|reel|tv)/", url)]
    profile_urls = [url for url in post_urls if url not in direct_post_urls]
    if profile_urls:
        posts = _run_actor(settings.apify_instagram_posts_actor, {
            "directUrls": profile_urls, "resultsType": "posts", "resultsLimit": max_posts,
        })
        discovered: list[str] = []
        for post in posts:
            url = _pick(post, "url", "postUrl")
            if not url and post.get("shortCode"):
                url = f"https://www.instagram.com/p/{post['shortCode']}/"
            if url:
                discovered.append(str(url))
        direct_post_urls.extend(discovered)
    direct_post_urls = list(dict.fromkeys(direct_post_urls))
    if not direct_post_urls:
        raise ImportServiceError("Instagram не вернул публичные публикации этого профиля.")
    items = _run_actor(settings.apify_instagram_actor, {
        "directUrls": direct_post_urls, "resultsLimit": limit,
    })
    return _normalize(_with_nested_replies(items), "Instagram", post_urls[0])


def collect_facebook(post_urls: list[str], limit: int = 500, max_posts: int = 0) -> list[dict]:
    items = _run_actor(settings.apify_facebook_actor, {
        "sources": post_urls, "maxPosts": max_posts, "maxCommentsPerPost": limit,
        "fetchAllComments": True, "fetchCommentReplies": True,
    })
    return _normalize(_with_nested_replies(items), "Facebook", post_urls[0])


def save_collected(rows: list[dict]) -> int:
    if not rows:
        return 0
    try:
        return insert_reviews(rows)
    except DataServiceError as exc:
        raise ImportServiceError(str(exc)) from exc
