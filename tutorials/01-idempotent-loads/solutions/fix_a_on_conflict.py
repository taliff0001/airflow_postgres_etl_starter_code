"""
Tutorial 01: Idempotent loads  --  FIX A: unique key + INSERT ... ON CONFLICT

Same batched load as the starting version. Two things changed:
  1. orders now has a primary key on order_id (see fix_a.sql)
  2. the INSERT says what to do when that key already exists: update the row instead of failing
A retry can now run as many times as it likes; every row ends up exactly once.
"""
from datetime import timedelta

import pendulum
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import DAG, Variable, get_current_context, task

BATCH_SIZE = 100

UPSERT_SQL = """
INSERT INTO orders (order_id, customer_id, amount, updated_at)
VALUES (%s, %s, %s, %s)
ON CONFLICT (order_id) DO UPDATE SET
    customer_id = EXCLUDED.customer_id,
    amount      = EXCLUDED.amount,
    updated_at  = EXCLUDED.updated_at,
    loaded_at   = now()
"""

with DAG(
    dag_id="load_orders",
    schedule=None,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    default_args={"retries": 1, "retry_delay": timedelta(seconds=10)},
    tags=["tutorial-01"],
):

    @task
    def load():
        fail_after = int(Variable.get("TUTORIAL_FAIL_AFTER_ROWS", default=0))
        attempt = get_current_context()["ti"].try_number
        print(f"attempt {attempt}; chaos switch TUTORIAL_FAIL_AFTER_ROWS={fail_after}")

        conn = PostgresHook(postgres_conn_id="warehouse_db").get_conn()
        cur = conn.cursor()
        cur.execute("SELECT order_id, customer_id, amount, updated_at FROM raw_orders ORDER BY order_id")
        rows = cur.fetchall()

        loaded = 0
        for start in range(0, len(rows), BATCH_SIZE):
            batch = rows[start : start + BATCH_SIZE]
            cur.executemany(UPSERT_SQL, batch)
            conn.commit()
            loaded += len(batch)
            print(f"committed {loaded}/{len(rows)} rows")
            if fail_after and attempt == 1 and loaded >= fail_after:
                raise RuntimeError(
                    f"Simulated crash on attempt 1 after {loaded} rows "
                    f"(TUTORIAL_FAIL_AFTER_ROWS={fail_after}). Airflow will retry."
                )

        print(f"load complete: {loaded} rows")

    load()
