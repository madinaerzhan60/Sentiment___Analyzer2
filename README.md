# Sentiment Analyzer · GRATA International

Private client-feedback dashboard. HTML/CSS/JavaScript frontend, FastAPI Python backend, Pandas analytics, Supabase/PostgreSQL storage, Gemini → Groq structured analysis, python-dotenv configuration. Local TT Norms Pro and the supplied GRATA logo are preserved.

## Run locally
```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8501
```
Open http://127.0.0.1:8501. Set SUPABASE_URL and SUPABASE_KEY in the server's .env. Set GEMINI_API_KEY and optionally GROQ_API_KEY for analysis. GEMINI_MODEL and GROQ_MODEL are configurable. Never commit secrets. The browser receives no keys.

## Existing database
For a new database run supabase_schema.sql. For an existing database run migrations/001_optional_dates_and_yandex.sql in Supabase SQL Editor before importing missing dates or Yandex reviews. This removes the required-date restriction and extends the supported source constraint; it does not delete or rewrite reviews. The migration is provided, not applied automatically.

Missing or unavailable databases show an explicit error, never demo reviews. The application reads every page, not only Supabase's default result limit. Stored records and completed AI analyses remain unchanged.

Existing 2GIS rows without the configured GRATA firm ID in their source reference are excluded from the GRATA dashboard, not deleted. The excluded count is displayed. Source ownership for manually imported social comments remains the importer's responsibility.

## Pages
- Dashboard: score, review count, attention count, source count, sentiment, concerns, source distribution, recent feedback.
- Reviews: search, source/sentiment filters, pagination, keyboard-accessible detail dialog, original text and safe source links.
- Analytics: monthly sentiment counts, volume (including pending records), source totals, complaint topics and positive themes.
- AI Insights: critical, attention, positive and watch groups; explicitly runs analysis for up to 50 pending/failed rows.
- Sources: six manual-import channels, stored counts and dates, validated UTF-8 CSV import.
- Reports: five report views, browser Print / Save as PDF and period-review CSV export. Reports are not stored.
- Settings: honest configuration information; no simulated user management or notifications.

All interface copy is English. Original feedback is never translated or changed. Legacy non-English analysis is represented by a short English description grounded in its saved classification, not presented as a translation. New model summaries and actions are requested in English.

## Import and analysis
CSV requires source and review_text. Optional columns: author, published_at (ISO date), rating (0–5, 0 means unavailable), external_id, source_url. Up to 1,000 rows and 2 MB. Supported names: Google / Google Maps, 2GIS, Yandex / Yandex Maps, Instagram, Facebook, CSV / CSV Import.

Missing dates remain null; invalid/future dates and unsafe URL schemes are rejected. All time includes unknown dates; dated filters do not. Original text is retained. Identity is source + external_id, with a deterministic source/author/text/date fallback. Reimports skip existing identities without overwriting their analysis. Partial import failures can be retried safely.

The import screen can analyze pending reviews after saving (up to 50). Other pending reviews may be included in that batch. Completed analysis is never repeated. Provider failures leave records available for retry. Refresh only rereads the database: it does not collect from social platforms and does not incur AI calls.

Legacy Apify functions remain in services/import_service.py for reference but the web collection endpoint is disabled. No official platform authorization or scheduled collection is implemented. Use authorized manual exports; do not assume an API token establishes permitted access.

## Score and interpretation
100 − 45 × negative share − 25 × critical share − 30 × average risk / 100.
Critical means severity critical or triage score ≥ 85. Shares use analyzed feedback only. Empty analysis shows no score. This is an explainable triage indicator, not a scientific probability.

Needs Attention counts negative, high/critical severity or score ≥ 85 reviews once. Critical is a subset, not an additional count. Resolved workflow tracking is not implemented.

The comparison is explicitly the most recent 30 days versus preceding 30 days, regardless of the selected display period. If either period has no analysis, comparison is unavailable. Executive findings are calculated from saved classifications, not fresh AI audits.

## Code layout
backend/main.py serves the API and frontend. services/ contains the retained database, analytics and analysis code. frontend/brand.css is the active consolidated stylesheet; styles.css and pages/components are legacy Streamlit assets, not loaded by this app. No new Streamlit pages should be added to the FastAPI UI.

## Safety and deployment
This is an internal app without built-in authentication. Bind locally or deploy behind an authenticated organizational proxy/VPN and HTTPS. Do not expose a service-role-backed write API publicly. No public deployment or Git push is performed by the UI update.

## Tests
```sh
python3 -m unittest discover -s tests -v
node --check frontend/app.js
```
Tests use mocked data/services and do not modify Supabase or call paid AI providers. They cover empty/error states, filters, period comparison, source verification, date preservation, CSV validation, safe URL handling, deduplication, paginated reads, social-reaction rules, JSON recovery and static/API routes.

## Icon provenance
Google Maps, Instagram and Facebook shapes: Simple Icons 13.21.0 (CC0; brand trademarks remain their owners'). 2GIS logo: official docs.2gis.com/en/assets/logo/2gis/en/logo-light.svg. Yandex Maps: official maps.yastatic.net favicon asset. Assets are local; no third-party asset requests are required at runtime. Use the supplied TT Norms Pro font only where your license permits.
