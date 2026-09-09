import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import pandas as pd
from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend.main import app, snapshot, parse_csv, period_filter
from services.supabase_service import normalize_reviews, DataServiceError, insert_reviews, fetch_reviews
from services.ai_service import _short_social_comment, _validate


def review(**extra):
    return {"id": "one", "source": "Instagram", "author": "Test", "review_text": "Great!", "published_at": pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=2), "sentiment": "positive", "severity": "low", "risk_score": 0, "analysis_status": "done", **extra}


class ProductTests(unittest.TestCase):
    def test_empty_has_no_fake_score(self):
        with patch("backend.main.fetch_reviews", return_value=normalize_reviews(pd.DataFrame())):
            result = snapshot()
        self.assertIsNone(result["metrics"]["health"])
        self.assertEqual(result["items"], [])

    def test_database_failure_no_fallback_or_details(self):
        with patch("backend.main.fetch_reviews", side_effect=DataServiceError("secret-key")):
            response = TestClient(app).get("/api/dashboard")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret-key", response.text)

    def test_comparison_uses_previous_period_before_filtering(self):
        old = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=40)
        data = normalize_reviews(pd.DataFrame([review(), review(id="two", published_at=old, sentiment="negative")]))
        with patch("backend.main.fetch_reviews", return_value=data):
            result = snapshot(30)
        self.assertEqual(result["metrics"]["total"], 1)
        self.assertEqual(result["metrics"]["health_delta"], 45)

    def test_comparison_missing_is_not_zero(self):
        with patch("backend.main.fetch_reviews", return_value=normalize_reviews(pd.DataFrame([review()]))):
            self.assertIsNone(snapshot(30)["metrics"]["health_delta"])

    def test_unknown_date_only_in_all_time(self):
        data = normalize_reviews(pd.DataFrame([review(published_at=None)]))
        self.assertEqual(len(period_filter(data)), 1)
        self.assertEqual(len(period_filter(data, 30)), 0)

    def test_custom_includes_entire_end_date(self):
        data = normalize_reviews(pd.DataFrame([review(published_at="2025-01-02T23:59:00Z")]))
        self.assertEqual(len(period_filter(data, start=date(2025,1,2), end=date(2025,1,2))), 1)

    def test_invalid_range(self):
        with self.assertRaises(HTTPException):
            period_filter(normalize_reviews(pd.DataFrame()), start=date(2025,2,1), end=date(2025,1,1))

    def test_csv_original_and_missing_date_preserved(self):
        rows = parse_csv('source,review_text\nInstagram,"Спасибо, керемет!"')
        self.assertEqual(rows[0]["review_text"], "Спасибо, керемет!")
        self.assertIsNone(rows[0]["published_at"])
        self.assertEqual(rows[0]["analysis_status"], "pending")

    def test_csv_unsafe_url_invalid_date_rating(self):
        for field, value in [("source_url", "javascript:alert(1)"), ("published_at", "garbage"), ("rating", "8"), ("published_at", "2099-01-01")]:
            with self.subTest(field=field), self.assertRaises(HTTPException):
                parse_csv(f"source,review_text,{field}\nInstagram,Hi,{value}")

    def test_csv_yandex(self):
        self.assertEqual(parse_csv("source,review_text\nYandex Maps,Thank you")[0]["source"], "Yandex")

    def test_local_reactions_not_complaints(self):
        self.assertEqual(_short_social_comment("🔥🔥🔥", "Instagram")["sentiment"], "positive")
        self.assertEqual(_short_social_comment("Finance", "Instagram")["sentiment"], "neutral")
        self.assertIsNone(_short_social_comment("Awful service 🔥", "Instagram"))
        self.assertIsNone(_short_social_comment("күттік", "Instagram"))

    def test_json_fences(self):
        import json
        payload = _short_social_comment("👏", "Instagram")
        self.assertEqual(_validate("Output: ```json\n"+json.dumps(payload)+"\n```"), payload)

    def test_dedup_does_not_overwrite(self):
        row = review(external_id="123")
        client = MagicMock()
        with patch("services.supabase_service.settings", SimpleNamespace(supabase_configured=True)), patch("services.supabase_service.get_client", return_value=client), patch("services.supabase_service.fetch_reviews", return_value=normalize_reviews(pd.DataFrame([row]))):
            self.assertEqual(insert_reviews([row, row]), 0)
        client.table.assert_not_called()

    def test_pagination_beyond_default_limit(self):
        client = MagicMock()
        client.table.return_value.select.return_value.order.return_value.range.return_value.execute.side_effect = [SimpleNamespace(data=[review(id=str(i)) for i in range(500)]), SimpleNamespace(data=[review(id="last")])]
        with patch("services.supabase_service.settings", SimpleNamespace(supabase_configured=True)), patch("services.supabase_service.get_client", return_value=client):
            self.assertEqual(len(fetch_reviews()), 501)

    def test_unverified_2gis_is_retained_but_excluded(self):
        data = normalize_reviews(pd.DataFrame([review(source="2GIS", source_url="https://2gis.kz/firm/other")]))
        with patch("backend.main.fetch_reviews", return_value=data):
            result = snapshot()
        self.assertEqual(result["meta"]["excluded_unverified"], 1)
        self.assertEqual(len(data), 1)

    def test_routes_and_static(self):
        client = TestClient(app)
        for route in ["/", "/api/health", "/static/app.js", "/static/brand.css", "/fonts/TTNormsPro-Regular.ttf"]:
            self.assertEqual(client.get(route).status_code, 200)
        with patch("backend.main.settings", SimpleNamespace(supabase_configured=False)):
            self.assertEqual(client.post("/api/sync").status_code, 400)

if __name__ == "__main__":
    unittest.main()
