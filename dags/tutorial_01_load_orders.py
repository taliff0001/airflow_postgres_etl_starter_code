"""
Tutorial 01: Idempotent loads  --  STARTING VERSION (the one with the bug)

Loads every row from raw_orders into orders, 100 rows per batch, committing after each batch.
That's how real large loads behave, and it's why a crash halfway leaves half the data behind.

The Airflow Variable TUTORIAL_FAIL_AFTER_ROWS is a chaos switch:
  0  -> load normally
  N  -> on the FIRST attempt only, raise an error once N rows have been committed.
        Airflow retries, the retry succeeds, and the run turns green.
"""
from datetime import timedelta

import pendulum
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import DAG, Variable, get_current_context, task

BATCH_SIZE = 100

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
            cur.executemany(
                "INSERT INTO orders (order_id, customer_id, amount, updated_at) VALUES (%s, %s, %s, %s)",
                batch,
            )
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
