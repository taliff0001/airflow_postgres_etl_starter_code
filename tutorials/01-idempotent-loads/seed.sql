-- Tutorial 01: Idempotent loads
-- Creates (or recreates) the source and target tables in the `warehouse` database.
-- Safe to re-run at any time: it drops everything the tutorial created.

DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS orders_stage;
DROP TABLE IF EXISTS raw_orders;

-- Source: 1,000 orders, as if they arrived from an upstream system.
CREATE TABLE raw_orders (
    order_id    integer       NOT NULL,
    customer_id integer       NOT NULL,
    amount      numeric(10,2) NOT NULL,
    updated_at  timestamptz   NOT NULL
);

INSERT INTO raw_orders (order_id, customer_id, amount, updated_at)
SELECT
    g,
    1 + (g * 7919) % 250,                       -- 250 customers, spread around
    round((10 + (g * 31) % 490)::numeric, 2),   -- amounts between 10 and 499
    timestamptz '2026-09-01 00:00:00+00' + (g || ' minutes')::interval
FROM generate_series(1, 1000) AS g;

-- Target: what the pipeline loads into.
-- Deliberately has NO primary key or unique constraint. That's the bug you're about to meet.
CREATE TABLE orders (
    order_id    integer       NOT NULL,
    customer_id integer       NOT NULL,
    amount      numeric(10,2) NOT NULL,
    updated_at  timestamptz   NOT NULL,
    loaded_at   timestamptz   NOT NULL DEFAULT now()
);
