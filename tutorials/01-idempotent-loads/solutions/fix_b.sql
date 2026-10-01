-- Fix B, part 1: a staging table shaped like the target.
-- Run after reset.sh and fix_a.sql.
CREATE TABLE IF NOT EXISTS orders_stage (LIKE orders INCLUDING DEFAULTS);
