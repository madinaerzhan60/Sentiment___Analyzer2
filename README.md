# Sentiment Analyzer

Sentiment Analyzer turns imported customer reviews into an explainable management dashboard for one company. It highlights reputation health, sentiment trends, risky feedback, platform patterns, complaint themes, and AI-supported actions. The visual demo works immediately with 40 bundled Russian, Kazakh, and mixed-language reviews; Supabase enables persistent live data and human decisions.

## Architecture

- `app.py` — Streamlit shell, global filters, overview, and cached reads
- `pages/` — analytics, AI Risk Center, and searchable review registry
- `services/supabase_service.py` — Supabase reads and uncached writes
- `services/ai_service.py` — validated JSON analysis through Gemini, then Groq fallback
- `services/analytics_service.py` — Pandas calculations and management findings
- `components/` — reusable metrics, charts, and risk cards
- `scripts/` — CSV import and one-time batch analysis
- `supabase_schema.sql` — PostgreSQL table, constraints, and indexes

AI output is stored on each review. Streamlit reads that stored analysis; it does not call an AI model during page reruns.

## Install

Python 3.10+ is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Environment variables

Set values in `.env` (never commit it):

```dotenv
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-server-side-key
GEMINI_API_KEY=your-gemini-key
GROQ_API_KEY=optional-fallback-key
GEMINI_MODEL=gemini-3.6-flash
GROQ_MODEL=openai/gpt-oss-20b
APIFY_TOKEN=your-apify-token
```

Gemini is attempted first. Groq is used only if Gemini fails. If neither succeeds, the review is marked `failed` and the UI continues with a clear unavailable message. Errors never trigger fabricated regex recommendations.

For a private server deployment, keep the Supabase service-role key server-side. Do not place it in browser code or commit it. If using an authenticated/anon key instead, define suitable row-level security policies for your organization.

## Supabase setup

1. Create a Supabase project.
2. Open its SQL Editor and run `supabase_schema.sql`.
3. Add `SUPABASE_URL` and `SUPABASE_KEY` to `.env`.

The raw `review_text` is always retained. `analysis_status` moves through `pending → processing → done`; a provider failure becomes `failed`. The unique review identity makes repeated CSV imports safe. Writes are never Streamlit-cached.

## Import data

The in-app **Загрузить данные** page can collect real public 2GIS reviews and
Instagram/Facebook post comments through configurable Apify actors. This is an
unofficial scraping integration and may be affected by platform changes or actor
pricing. Use it only where your legal basis and the platforms' terms permit.

Import the bundled, pre-analyzed demo dataset:

```bash
python scripts/seed_reviews.py
```

Import any compatible CSV as raw reviews queued for AI analysis:

```bash
python scripts/seed_reviews.py path/to/reviews.csv --raw-only
```

Required CSV columns are `source`, `author`, `rating`, `review_text`, and `published_at`. Supported sources are Facebook, Instagram, 2GIS, Google, and CSV.

## Analyze pending reviews once

```bash
python scripts/analyze_reviews.py
```

The script claims only `pending` or `failed` rows, validates the structured result, and saves it permanently. Rows already marked `done` are skipped. Run this after an import—not from a Streamlit rerun. Retrying a failed row is intentional; completed rows do not incur another model call.

## Run

```bash
streamlit run app.py
```

Without Supabase credentials, the app enters a read-only demo mode using `data/sample_reviews.csv`. With credentials, it reads Supabase and action buttons persist management decisions. An empty database and connection errors are handled without an application traceback.

## Brand Health formula

The score is a consistent management indicator, not a scientifically validated probability:

`100 − (45 × negative share) − (25 × critical share) − (30 × normalized average risk)`

It is clamped to 0–100 and calculated only from successfully analyzed reviews in the selected period.

## MVP limitations

- The current MVP uses manually imported review data.
- Facebook, Instagram, Google, and 2GIS scraping is **not** implemented.
- Official platform API integrations, authentication, multi-tenancy, scheduled ingestion, and model-quality evaluation are future work.
- AI classifications and recommendations can be wrong; they are triage suggestions subject to human review.
- The bundled executive summary is derived from stored analysis with Pandas, avoiding repeated model calls.
