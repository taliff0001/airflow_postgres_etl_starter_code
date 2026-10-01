#!/usr/bin/env bash
# Returns the tutorial to its starting state: fresh tables, chaos switch off.
# Your DAG file edits are NOT touched.
set -euo pipefail
cd "$(dirname "$0")/../.."
echo "==> Recreating raw_orders and orders (empty, no primary key)"
docker compose exec -T postgres psql -U airflow -d warehouse -q -f - < tutorials/01-idempotent-loads/seed.sql
echo "==> Setting TUTORIAL_FAIL_AFTER_ROWS = 0 (no simulated failure)"
docker compose exec -T airflow-scheduler airflow variables set TUTORIAL_FAIL_AFTER_ROWS 0 >/dev/null
echo "Done. Run tutorials/01-idempotent-loads/check.sh to confirm orders is empty."
