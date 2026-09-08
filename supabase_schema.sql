create extension if not exists pgcrypto;

create table if not exists public.reviews (
  id uuid primary key default gen_random_uuid(),
  source text not null check (source in ('Facebook', 'Instagram', '2GIS', 'Google', 'CSV')),
  author text not null default 'Anonymous',
  rating smallint not null default 0 check (rating between 0 and 5),
  review_text text not null,
  external_id text,
  source_url text,
  published_at timestamptz not null,
  created_at timestamptz not null default now(),
  sentiment text check (sentiment in ('positive', 'neutral', 'negative')),
  category text check (category in ('response_time', 'staff_behavior', 'service_quality', 'product_quality', 'pricing', 'communication', 'waiting_time', 'other')),
  severity text check (severity in ('low', 'medium', 'high', 'critical')),
  risk_score smallint check (risk_score between 0 and 100),
  summary text,
  recommendation text,
  suggested_response text,
  analysis_status text not null default 'pending' check (analysis_status in ('pending', 'processing', 'done', 'failed')),
  action_status text not null default 'pending_review' check (action_status in ('pending_review', 'approved', 'rejected', 'resolved')),
  analysis_provider text,
  analyzed_at timestamptz,
  constraint review_identity unique (source, author, published_at, review_text)
);

create unique index if not exists reviews_source_external_id_idx
  on public.reviews (source, external_id) where external_id is not null;

create index if not exists reviews_published_at_idx on public.reviews (published_at desc);
create index if not exists reviews_risk_idx on public.reviews (risk_score desc) where sentiment = 'negative';
create index if not exists reviews_analysis_status_idx on public.reviews (analysis_status);

alter table public.reviews enable row level security;
-- This MVP is intended for a private management dashboard. Use a server-side service-role
-- key, or add authenticated policies appropriate to your organisation. Never expose that key.

grant usage on schema public to service_role;
grant select, insert, update, delete on table public.reviews to service_role;
grant usage, select on all sequences in schema public to service_role;
