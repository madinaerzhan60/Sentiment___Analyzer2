-- Additive compatibility update: preserves every existing review and AI result.
begin;
alter table public.reviews alter column published_at drop not null;
alter table public.reviews drop constraint if exists reviews_source_check;
alter table public.reviews add constraint reviews_source_check
  check (source in ('Facebook', 'Instagram', '2GIS', 'Google', 'Yandex', 'CSV'));
commit;
