-- Governed shadow gold dim: billing_type. Mirrors warehouse/gold (dim_billing_type_c086).
-- billing_type (English, translated in staging) is the natural key; billing_type_code
-- is its 1:1 short-code attribute. Sentinel-exclusion safeguard as elsewhere.
with natural_members as (
    select
        billing_type,
        max(billing_type_code) as billing_type_code
    from {{ ref('stg_sales_c086_raw') }}
    where billing_type <> 'UNKNOWN'
    group by billing_type
),

keyed_members as (
    select
        row_number() over (order by billing_type)::integer as billing_type_sk,
        billing_type,
        billing_type_code
    from natural_members
)

select
    -1::integer as billing_type_sk,
    'UNKNOWN'::text as billing_type,
    'UNKNOWN'::text as billing_type_code
union all
select billing_type_sk, billing_type, billing_type_code
from keyed_members
