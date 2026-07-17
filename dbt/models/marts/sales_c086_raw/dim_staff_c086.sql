-- Governed shadow gold dim: staff. Mirrors warehouse/gold (dim_staff_c086).
-- staff_code is the natural key; staff_name_masked (md5 pseudonym, PII ruling) and
-- staff_position are its attributes.
--
-- SENTINEL-EXCLUSION SAFEGUARD (the bug the migration caught on its first live run):
-- staff blanks coalesce to the literal 'UNKNOWN' in staging. A plain GROUP BY would
-- build a REAL dim row for 'UNKNOWN' colliding with the -1 sentinel member (same label),
-- and every staff_code='UNKNOWN' fact row would fan out across BOTH -- silently
-- duplicating facts. Excluding the sentinel from the natural population fixes it; those
-- rows COALESCE to the single -1 member in the fact load.
with natural_members as (
    select
        staff_code,
        max(staff_name_masked) as staff_name_masked,
        max(staff_position)    as staff_position
    from {{ ref('stg_sales_c086_raw') }}
    where staff_code <> 'UNKNOWN'
    group by staff_code
),

keyed_members as (
    select
        row_number() over (order by staff_code)::integer as staff_sk,
        staff_code,
        staff_name_masked,
        staff_position
    from natural_members
)

select
    -1::integer as staff_sk,
    'UNKNOWN'::text as staff_code,
    'UNKNOWN'::text as staff_name_masked,
    'UNKNOWN'::text as staff_position
union all
select staff_sk, staff_code, staff_name_masked, staff_position
from keyed_members
