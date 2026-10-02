# Tutorial 01: The retry that duplicated everything

A pipeline fails near the end. Airflow retries it. The retry succeeds, the run turns green, and
nobody notices that half the table is now in there twice.

This tutorial reproduces that failure on your machine, then fixes it two ways. The property you're
building toward is **idempotency**: a load that produces the same result no matter how many times it
runs. Retries are normal; a pipeline has to know how to run again safely.

It was prompted by [a LinkedIn post from Madhuri P.](https://www.linkedin.com/posts/madhuri91_dataengineering-datapipelines-etl-share-7510773223597318144-sRcm/) (Sr. Big Data Engineer): a pipeline that
processed a million records, failed near the end, was retried, and created duplicates.

**Time:** about 45 minutes. **You need:** this repo's stack running (`./setup.sh` from the repo root)
and the Airflow UI open at http://localhost:8080 (admin / admin).

All commands below run from the **repo root**.

---

## Step 0: Starting state

```bash
./setup.sh --reset
./tutorials/01-idempotent-loads/check.sh
```

`--reset` creates two tables in the `warehouse` database: `raw_orders` (1,000 rows, the source) and
`orders` (empty, the target). `check.sh` prints three numbers you'll use at every checkpoint.

**Checkpoint:** `total_rows 0, distinct_order_ids 0, duplicate_rows 0`.

Note what `orders` is missing: it has no primary key. Keep that in mind.

## Step 1: Read the DAG

Open `dags/tutorial_01_load_orders.py`. It's one task, `load`, with `retries=1`. It reads every row
from `raw_orders` and inserts into `orders` **100 rows at a time, committing after each batch**.
That's how real loads of large tables work: you don't hold a million rows in one transaction.

There's also a chaos switch. The task reads an Airflow Variable, `TUTORIAL_FAIL_AFTER_ROWS`. If it's
greater than 0, the task raises an error once that many rows are committed, but **only on the first
attempt**. The retry runs clean. This simulates a transient failure: a dropped connection, a timeout,
a node restart.

In the Airflow UI, confirm `load_orders` is listed on the Dags page. (If it isn't yet, give it ten
seconds; the DAG processor rescans the folder on that interval.)

## Step 2: Break it

Turn the chaos switch on. In the UI: **Admin → Variables**, set `TUTORIAL_FAIL_AFTER_ROWS` to `500`.
Or from the terminal:

```bash
docker compose exec airflow-scheduler airflow variables set TUTORIAL_FAIL_AFTER_ROWS 500
```

Trigger the DAG (the play button on `load_orders`, or
`docker compose exec airflow-scheduler airflow dags trigger load_orders`). Within about 20 seconds
the run finishes **green**.

```bash
./tutorials/01-idempotent-loads/check.sh
```

**Checkpoint:** `total_rows 1500, distinct_order_ids 1000, duplicate_rows 500`.

What happened: attempt 1 committed 500 rows and crashed. Airflow retried. Attempt 2 started from the
top and loaded all 1,000. Rows 1 through 500 are in the table twice, and the only evidence is the
first attempt's log. Open the run in the UI, click the `load` task, and switch the log view between
try 1 and try 2.

This is the bug. The pipeline "worked." The data is wrong.

## Step 3: Fix A, a key plus ON CONFLICT

The table accepted duplicates because nothing told it not to. Fix the table first, then the insert.

```bash
./setup.sh --reset
docker compose exec -T postgres psql -U airflow -d warehouse < tutorials/01-idempotent-loads/solutions/fix_a.sql
```

`fix_a.sql` is one line: `ALTER TABLE orders ADD PRIMARY KEY (order_id);`

Now edit `dags/tutorial_01_load_orders.py`. Replace the INSERT statement with an *upsert*:

```sql
INSERT INTO orders (order_id, customer_id, amount, updated_at)
VALUES (%s, %s, %s, %s)
ON CONFLICT (order_id) DO UPDATE SET
    customer_id = EXCLUDED.customer_id,
    amount      = EXCLUDED.amount,
    updated_at  = EXCLUDED.updated_at,
    loaded_at   = now()
```

`EXCLUDED` is Postgres's name for "the row I was trying to insert." When the key already exists, the
existing row is updated with it instead. (Stuck? The finished file is
`solutions/fix_a_on_conflict.py`; copy it over the DAG file.)

Leave the chaos switch at 500 and trigger the DAG again.

**Checkpoint:** `total_rows 1000, distinct_order_ids 1000, duplicate_rows 0`.

Trigger it a third time, chaos still on. **Checkpoint:** still 1,000. That's idempotency: run it as
often as you like, the result is the same.

## Step 4: Fix B, a staging table plus MERGE

Fix A puts the responsibility on every INSERT. Fix B puts it on the structure of the pipeline, which
scales better when a load has many steps or many sources.

```bash
./setup.sh --reset
docker compose exec -T postgres psql -U airflow -d warehouse < tutorials/01-idempotent-loads/solutions/fix_a.sql
docker compose exec -T postgres psql -U airflow -d warehouse < tutorials/01-idempotent-loads/solutions/fix_b.sql
```

`fix_b.sql` creates `orders_stage`, a scratch table shaped like `orders`.

Restructure the DAG into two tasks:

1. **`load_stage`**: `TRUNCATE orders_stage`, then the same batched, crash-prone load, but into
   `orders_stage`. Because every attempt starts by truncating, a retry can never stack on a
   half-finished load.
2. **`merge_orders`**: one statement moves everything into the target.

```sql
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
```

Wire them up with `load_stage() >> merge_orders()`. (Finished version:
`solutions/fix_b_staging_merge.py`.) `MERGE` needs Postgres 15 or newer; this stack runs 17.

Trigger the DAG with the chaos switch still on. In the UI you'll see `load_stage` fail once, retry,
succeed, and then `merge_orders` run.

**Checkpoint:** `total_rows 1000, distinct_order_ids 1000, duplicate_rows 0`.

## Step 5: What you just learned

Both fixes make the load *idempotent*; they do it at different layers.

| | Fix A: key + ON CONFLICT | Fix B: staging + MERGE |
|---|---|---|
| Where the guarantee lives | the target table and each INSERT | the pipeline's shape |
| Good for | simple loads, one source, row-at-a-time or batched | multi-step loads, transformations before landing, auditing what each run brought in |
| Cost | every write checks the key | an extra table and an extra step |
| Without a key on the target | doesn't work | still works, but add the key anyway |

Both depend on one decision made in Step 3: **the target table has a key.** Everything else follows.

Madhuri's post ended with a checklist; this tutorial is the hands-on version of three items on it:
*find duplicate business keys* (Step 2), *use MERGE / UPSERT where appropriate* (Steps 3 and 4), and
*design retries to be idempotent* (Steps 3 and 4). Her last line was the whole lesson:
a production pipeline should not only know how to run. It should know how to safely run again.

---

## Reference

| Want to | Command |
|---|---|
| Start the stack | `./setup.sh` |
| Reset tutorial tables, chaos off | `./setup.sh --reset` |
| Check the target table | `./tutorials/01-idempotent-loads/check.sh` |
| Set the chaos switch | `docker compose exec airflow-scheduler airflow variables set TUTORIAL_FAIL_AFTER_ROWS 500` |
| Trigger the DAG | `docker compose exec airflow-scheduler airflow dags trigger load_orders` |
| Open psql on the warehouse | `docker compose exec postgres psql -U airflow -d warehouse` |
| Wipe everything and start over | `./setup.sh --clean` |

**Troubleshooting**

- *The DAG isn't in the UI.* Wait ten seconds. If it's still missing:
  `docker compose exec airflow-dag-processor airflow dags list-import-errors`
- *`ALTER TABLE ... ADD PRIMARY KEY` fails.* The table still has duplicates. Run `./setup.sh --reset` first.
- *The UI shows your variable, but the terminal doesn't see it (or `check.sh` stays at 0 after a run).* You may
  be looking at a different Airflow. In Codespaces, open the UI from the **Ports** tab (port 8080, globe icon);
  `localhost:8080` in your browser could be a stack running on your own machine. (The CLI prints "created"
  even when it updates an existing variable, so that message alone doesn't mean anything is wrong.)
- *`MERGE` is a syntax error.* You're on Postgres older than 15. This stack pins 17; run `./setup.sh --clean`.
