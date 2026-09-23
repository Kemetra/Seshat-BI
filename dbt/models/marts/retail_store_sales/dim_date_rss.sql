with date_spine as (
    select day::date as full_date
    from generate_series(
        date '2022-01-01',
        date '2025-01-18',
        interval '1 day'
    ) as generated(day)
)

select
    to_char(full_date, 'YYYYMMDD')::integer as date_sk,
    full_date,
    extract(year from full_date)::smallint as year,
    extract(quarter from full_date)::smallint as quarter,
    extract(month from full_date)::smallint as month,
    to_char(full_date, 'FMMonth') as month_name,
    extract(day from full_date)::smallint as day,
    to_char(full_date, 'FMDay') as day_name,
    extract(week from full_date)::smallint as iso_week,
    (extract(isodow from full_date) >= 6) as is_weekend
from date_spine
