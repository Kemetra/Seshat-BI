CREATE SCHEMA gold;
CREATE TABLE gold.fct_sales (
    sale_id BIGINT,
    raw_amount NUMERIC
);
SELECT raw_amount FROM gold.fct_sales;
