-- Governed shadow gold fact. Mirrors warehouse/gold (fct_sales_c086).
-- Grain: one billing-document line item, business key (reference_no, item_no).
-- reference_no + item_no + is_return are DEGENERATE dims (live on the fact).
-- Entity-dim FKs COALESCE a missed lookup to -1; date_sk does NOT (an unmatched/NULL
-- fact date yields NULL and would fail loud -- a real calendar-coverage bug -- never
-- silently bucketed). Measures: gross_sales (the standing "sales" measure) + quantity.
-- No net_sales, no tax/discount columns (all dropped from the model).
with sales as (
    select * from {{ ref('stg_sales_c086_raw') }}
)

select
    row_number() over (order by s.reference_no, s.item_no)::integer as fct_sales_c086_sk,
    -- degenerate dimensions (also the declared grain key)
    s.reference_no,
    s.item_no,
    s.is_return,
    -- foreign keys to dims (entity dims COALESCE to the -1 unknown member)
    coalesce(dp.product_sk, -1)       as product_sk,
    coalesce(dbt_.billing_type_sk, -1) as billing_type_sk,
    coalesce(dc.customer_sk, -1)      as customer_sk,
    coalesce(dst.staff_sk, -1)        as staff_sk,
    dd.date_sk,  -- NO coalesce: unmatched date -> NULL -> rejected by date_sk not_null
    -- measures
    s.quantity,
    s.gross_sales
from sales as s
left join {{ ref('dim_product_c086') }}      as dp   on dp.material        = s.material
left join {{ ref('dim_billing_type_c086') }} as dbt_ on dbt_.billing_type  = s.billing_type
left join {{ ref('dim_customer_c086') }}     as dc   on dc.customer        = s.customer
left join {{ ref('dim_staff_c086') }}        as dst  on dst.staff_code     = s.staff_code
left join {{ ref('dim_date_c086') }}         as dd   on dd.full_date       = s.sale_date
