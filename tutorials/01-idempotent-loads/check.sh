#!/usr/bin/env bash
# Prints the state of the `orders` table: total rows, distinct order_ids, and how many ids are duplicated.
set -euo pipefail
cd "$(dirname "$0")/../.."
docker compose exec -T postgres psql -U airflow -d warehouse -c "
SELECT
  count(*)                                   AS total_rows,
  count(DISTINCT order_id)                   AS distinct_order_ids,
  count(*) - count(DISTINCT order_id)        AS duplicate_rows
FROM orders;"
