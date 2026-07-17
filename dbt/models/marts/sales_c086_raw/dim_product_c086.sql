-- Governed shadow gold dim: product. Mirrors warehouse/gold (dim_product_c086).
-- material is the natural key; the rest are its 1:1/flat-denorm attributes.
-- Excludes material='UNKNOWN' from the natural population (the sentinel maps to the
-- -1 unknown member, never a real dim row -- a real row sharing the sentinel label
-- would fan out facts via a 1:many join). SK is row_number() here (migration used
-- IDENTITY); parity never compares SK values, only member counts.
with natural_members as (
    select
        material,
        max(material_desc) as material_desc,
        max(category)      as category,
        max(subcategory)   as subcategory,
        max(segment)       as segment,
        max(division)      as division,
        max(brand)         as brand,
        max(item_cluster)  as item_cluster
    from {{ ref('stg_sales_c086_raw') }}
    where material <> 'UNKNOWN'
    group by material
),

keyed_members as (
    select
        row_number() over (order by material)::integer as product_sk,
        material, material_desc, category, subcategory,
        segment, division, brand, item_cluster
    from natural_members
)

select
    -1::integer as product_sk,
    'UNKNOWN'::text as material,
    'UNKNOWN'::text as material_desc,
    'UNKNOWN'::text as category,
    'UNKNOWN'::text as subcategory,
    'UNKNOWN'::text as segment,
    'UNKNOWN'::text as division,
    'UNKNOWN'::text as brand,
    'UNKNOWN'::text as item_cluster
union all
select
    product_sk, material, material_desc, category, subcategory,
    segment, division, brand, item_cluster
from keyed_members
