-- 0011_enforce_silver_demo_sample_orders_pk.sql
-- Enforce the declared grain of silver.demo_sample_orders.
--
-- 0005 declares "Grain: one order line. PK = (order_id)" in its header but never
-- adds the constraint, unlike 0003 / 0006 / 0007, which all enforce their silver
-- primary key physically (audit C36). A duplicated order_id would otherwise land
-- in silver silently. Follow-up migration so 0005 is not edited in place; apply
-- AFTER 0005 and re-apply whenever 0005 is re-applied (0005 is a DROP+CREATE).
--
-- Idempotent: the constraint is dropped-if-exists before it is added.
-- ASCII only; UTF-8 no BOM.

SET client_encoding TO 'UTF8';

BEGIN;

ALTER TABLE silver.demo_sample_orders DROP CONSTRAINT IF EXISTS pk_demo_sample_orders;
ALTER TABLE silver.demo_sample_orders
  ADD CONSTRAINT pk_demo_sample_orders PRIMARY KEY (order_id);

COMMIT;
