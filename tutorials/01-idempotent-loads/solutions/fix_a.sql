-- Fix A, part 1: give the target a key.
-- Run after reset.sh (it only succeeds on a table with no duplicates).
ALTER TABLE orders ADD PRIMARY KEY (order_id);
