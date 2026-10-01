"""
Tutorial 01: Idempotent loads  --  FIX B: staging table + MERGE

Two tasks instead of one:
  load_stage    truncates orders_stage, then does the batched (crash-prone) load into it
  merge_orders  one MERGE statement moves everything from orders_stage into orders

The crash-prone part now writes to a scratch table that is wiped at the start of every attempt,
so a retry can never stack on top of a half-finished load. The MERGE itself is a single
transaction: it either applies completely or not at all.
Requires Postgres 15+ (MERGE) and the staging table from fix_b.sql.
"""
from datetime import timedelta

import pendulum
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import DAG, Variable, get_current_context, task

BATCH_SIZE = 100

MERGE_SQL = """
MERGE INTO orders AS target
USING orders_stage AS stage
    ON target.order_id = stage.order_id
WHEN MATCHED THEN
    UPDATE SET customer_id = stage.customer_id,
               amount      = stage.amount,
               updated_at  = stage.updated_at,
               loaded_at   = now()
WHEN NOT MATCHED THEN
    INSERT (order_id, customer_id, amount, updated_at)
    VALUES (stage.order_id, stage.customer_id, stage.amount, stage.updated_at)
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
    def load_stage():
        fail_after = int(Variable.get("TUTORIAL_FAIL_AFTER_ROWS", default=0))
        attempt = get_current_context()["ti"].try_number
        print(f"attempt {attempt}; chaos switch TUTORIAL_FAIL_AFTER_ROWS={fail_after}")

        conn = PostgresHook(postgres_conn_id="warehouse_db").get_conn()
        cur = conn.cursor()

        cur.execute("TRUNCATE orders_stage")   # every attempt starts from a clean slate
        conn.commit()

        cur.execute("SELECT order_id, customer_id, amount, updated_at FROM raw_orders ORDER BY order_id")
        rows = cur.fetchall()

        loaded = 0
        for start in range(0, len(rows), BATCH_SIZE):
            batch = rows[start : start + BATCH_SIZE]
            cur.executemany(
                "INSERT INTO orders_stage (order_id, customer_id, amount, updated_at) VALUES (%s, %s, %s, %s)",
                batch,
            )
            conn.commit()
            loaded += len(batch)
            print(f"staged {loaded}/{len(rows)} rows")
            if fail_after and attempt == 1 and loaded >= fail_after:
                raise RuntimeError(
                    f"Simulated crash on attempt 1 after {loaded} rows "
                    f"(TUTORIAL_FAIL_AFTER_ROWS={fail_after}). Airflow will retry."
                )

        print(f"staging complete: {loaded} rows")

    @task
    def merge_orders():
        conn = PostgresHook(postgres_conn_id="warehouse_db").get_conn()
        cur = conn.cursor()
        cur.execute(MERGE_SQL)
        conn.commit()
        print(f"merge complete: {cur.rowcount} rows inserted or updated")

    load_stage() >> merge_orders()
