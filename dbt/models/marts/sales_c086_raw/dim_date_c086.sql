-- Governed shadow gold dim: date. Mirrors warehouse/gold (dim_date_c086).
-- CONTIGUOUS calendar over the approved span 2023-01-01..2025-12-31 (RC15; never
-- SELECT DISTINCT date). Smart key YYYYMMDD. NO -1 unknown member: this is a marked
-- date table (rule S8) -- an unmatched fact date is rejected by date_sk NOT NULL in
-- the fact, never bucketed to a sentinel.
with date_spine as (
    select d::date as full_date
    from generate_series(
        date '2023-01-01',
        date '2025-12-31',
        interval '1 day'
    ) as generated(d)
)

select
    to_char(full_date, 'YYYYMMDD')::integer as date_sk,
    full_date,
    extract(year from full_date)::smallint     as year,
    extract(quarter from full_date)::smallint  as quarter,
    extract(month from full_date)::smallint    as month,
    to_char(full_date, 'Month')                as month_name,
    extract(day from full_date)::smallint      as day,
    to_char(full_date, 'Day')                  as day_name,
    extract(week from full_date)::smallint     as iso_week,
    (extract(isodow from full_date) >= 6)      as is_weekend
from date_spine
