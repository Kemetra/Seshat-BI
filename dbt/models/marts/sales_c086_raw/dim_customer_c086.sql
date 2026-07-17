-- Governed shadow gold dim: customer. Mirrors warehouse/gold (dim_customer_c086).
-- customer is the natural key; customer_name is its 1:1 attribute (PII ruled low-risk,
-- predominantly B2B/institutional -- kept as-is). Sentinel-exclusion safeguard as elsewhere.
with natural_members as (
    select
        customer,
        max(customer_name) as customer_name
    from {{ ref('stg_sales_c086_raw') }}
    where customer <> 'UNKNOWN'
    group by customer
),

keyed_members as (
    select
        row_number() over (order by customer)::integer as customer_sk,
        customer,
        customer_name
    from natural_members
)

select
    -1::integer as customer_sk,
    'UNKNOWN'::text as customer,
    'UNKNOWN'::text as customer_name
union all
select customer_sk, customer, customer_name
from keyed_members
