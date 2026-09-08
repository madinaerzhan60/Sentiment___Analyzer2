"""Environment configuration with no import-time network side effects."""
from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    supabase_url: str = os.getenv("SUPABASE_URL", "").strip()
    supabase_key: str = os.getenv("SUPABASE_KEY", "").strip()
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    groq_api_key: str = os.getenv("GROQ_API_KEY", "").strip()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
    apify_token: str = os.getenv("APIFY_TOKEN", "").strip()
    apify_2gis_actor: str = os.getenv("APIFY_2GIS_ACTOR", "getascraper/2gis-reviews-scraper").strip()
    apify_instagram_actor: str = os.getenv("APIFY_INSTAGRAM_ACTOR", "apify/instagram-comment-scraper").strip()
    apify_instagram_posts_actor: str = os.getenv("APIFY_INSTAGRAM_POSTS_ACTOR", "apify/instagram-scraper").strip()
    apify_facebook_actor: str = os.getenv("APIFY_FACEBOOK_ACTOR", "unseenuser/fb-posts").strip()
    grata_2gis_firm_id: str = os.getenv("GRATA_2GIS_FIRM_ID", "9429940000842633").strip()

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @property
    def ai_configured(self) -> bool:
        return bool(self.gemini_api_key or self.groq_api_key)


settings = Settings()
