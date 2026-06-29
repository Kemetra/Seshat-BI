INSERT INTO gold.dim_date (day_key)
SELECT DISTINCT day_key FROM gold.thing;
