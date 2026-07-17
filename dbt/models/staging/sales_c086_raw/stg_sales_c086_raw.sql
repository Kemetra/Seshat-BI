-- Governed shadow staging (silver) for sales_c086_raw.
-- Faithful dbt translation of warehouse/silver/0001_create_silver_sales_c086_raw.sql
-- (the migration is the parity oracle). Same decisions, expressed as a dbt model
-- materialized into the shadow silver schema.
--
-- Grain: one billing-document line item. PK = (reference_no, item_no).
-- Row filter applied on the TRIMMED, PRE-sentinel division ('' not 'UNKNOWN') so the
-- 3 genuinely-blank-division rows are excluded, not leaked as 'UNKNOWN'. Post-filter
-- silver row count = 248,593 (not the 249,106 bronze count).
with src as (
    -- TRIM every text column up front (kills whitespace-variant phantom distincts).
    select
        trim(reference_no)   as reference_no,
        trim(item_no)        as item_no,
        trim(material)       as material,
        trim(material_desc)  as material_desc,
        trim(category)       as category,
        trim(subcategory)    as subcategory,
        trim(segment)        as segment,
        trim(division)       as division,
        trim(brand)          as brand,
        trim(item_cluster)   as item_cluster,
        trim(billing_type)   as billing_type,
        trim(billing_type_2) as billing_type_2,
        trim(quantity)       as quantity,
        trim(gross_sales)    as gross_sales,
        trim("date")         as sale_date,
        trim(customer)       as customer,
        trim(customer_name)  as customer_name,
        trim(personel_number) as staff_code,
        trim(person_name)    as person_name,
        trim("position")     as staff_position
    from {{ source('bronze', 'sales_c086_raw') }}
),

translated as (
    -- Arabic -> English translation happens ONCE here so both the final billing_type
    -- column AND the is_return derivation read the same translated value -- a single
    -- source of truth, not two independent classifications that could drift apart.
    select
        src.*,
        case billing_type
            when 'اجل'                 then 'Credit Sale'
            when 'فورى'                 then 'Cash Sale'
            when 'مرتجع اجل'            then 'Credit Return'
            when 'مرتجع فورى'           then 'Cash Return'
            when 'Pick-Up Order'        then 'Pick-Up Order'
            when 'Pick-Up Order Return' then 'Pick-Up Order Return'
            when 'توصيل'                 then 'Delivery'
            when 'مرتجع توصيل'          then 'Delivery Return'
            when 'توصيل - اجل'           then 'Delivery - Credit'
            when 'مرتجع توصيل - اجل'    then 'Delivery - Credit Return'
            when '' then 'UNKNOWN'
            else 'UNKNOWN'  -- an untranslated value surfaces as UNKNOWN, never passes through
        end as billing_type_en
    from src
)

select
    -- identity / grain key (RULED: reference_no+item_no, NOT billing_document).
    coalesce(nullif(reference_no, ''), 'UNKNOWN') as reference_no,
    coalesce(nullif(item_no, ''), 'UNKNOWN')      as item_no,

    -- product (material is the natural key; the rest are its attributes). Sentinel 'UNKNOWN'.
    coalesce(nullif(material, ''), 'UNKNOWN')      as material,
    coalesce(nullif(material_desc, ''), 'UNKNOWN') as material_desc,
    coalesce(nullif(category, ''), 'UNKNOWN')      as category,
    coalesce(nullif(subcategory, ''), 'UNKNOWN')   as subcategory,
    coalesce(nullif(segment, ''), 'UNKNOWN')       as segment,
    coalesce(nullif(division, ''), 'UNKNOWN')      as division,
    coalesce(nullif(brand, ''), 'UNKNOWN')         as brand,
    coalesce(nullif(item_cluster, ''), 'UNKNOWN')  as item_cluster,

    -- billing / returns (billing_type is the AUTHORITATIVE returns source, RC8).
    billing_type_en                                as billing_type,
    coalesce(nullif(billing_type_2, ''), 'UNKNOWN') as billing_type_code,

    -- measures (RC7: money/qty -> exact NUMERIC; '' -> NULL, never sentinel/zero).
    nullif(quantity, '')::numeric(14, 3)           as quantity,
    nullif(gross_sales, '')::numeric(18, 2)        as gross_sales,

    -- date (RC7: '' -> NULL; cannot hold the text sentinel).
    nullif(sale_date, '')::date                    as sale_date,

    -- customer (customer_name PII ruled low-risk: kept as-is). Sentinel 'UNKNOWN'.
    coalesce(nullif(customer, ''), 'UNKNOWN')      as customer,
    coalesce(nullif(customer_name, ''), 'UNKNOWN') as customer_name,

    -- staff (person_name PII ruled mask/pseudonymize: deterministic md5, or 'UNKNOWN' on blank).
    coalesce(nullif(staff_code, ''), 'UNKNOWN')    as staff_code,
    case
        when nullif(person_name, '') is null then 'UNKNOWN'
        else md5(person_name)
    end                                            as staff_name_masked,
    coalesce(nullif(staff_position, ''), 'UNKNOWN') as staff_position,

    -- is_return (RC8): derived from the TRANSLATED English label, NOT the quantity sign
    -- and NOT the Arabic prefix (which missed the 376 already-English Pick-Up Order Return rows).
    (billing_type_en like '%Return%')              as is_return

from translated
-- ROW FILTER: checked on the TRIMMED, PRE-sentinel division ('' not 'UNKNOWN') so the
-- blank-division rows are excluded exactly and cannot be defeated by the COALESCE step.
where division not in ('ARCHIVE', 'AUX', '', 'EL EZABY SERVICES')
