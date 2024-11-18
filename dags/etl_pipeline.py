from airflow import DAG
from airflow.operators.python import PythonOperator
import pendulum
import pandas as pd
import os
from sqlalchemy import create_engine

# Define default arguments for the DAG
default_args = {
    'owner': 'airflow',
}

# Initialize the DAG
with DAG(
    'csv_to_postgres_etl',
    default_args=default_args,
    schedule_interval=None,
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
) as dag:

    def ingest_csv1(**kwargs):
        df1 = pd.read_csv('/opt/airflow/data/csv1.csv')
        df1.to_csv('/opt/airflow/data/clean_csv1.csv', index=False)
        print("CSV 1 ingested.")

    def ingest_csv2(**kwargs):
        df2 = pd.read_csv('/opt/airflow/data/csv2.csv')
        df2.to_csv('/opt/airflow/data/clean_csv2.csv', index=False)
        print("CSV 2 ingested.")

    def clean_csv1(**kwargs):
        df1 = pd.read_csv('/opt/airflow/data/clean_csv1.csv')
        # Perform cleaning operations on df1
        df1['name'] = df1['name'].str.title()
        df1.to_csv('/opt/airflow/data/clean_csv1.csv', index=False)
        print("CSV 1 cleaned.")

    def clean_csv2(**kwargs):
        df2 = pd.read_csv('/opt/airflow/data/clean_csv2.csv')
        # Perform cleaning operations on df2
        df2['city'] = df2['city'].str.title()
        df2.to_csv('/opt/airflow/data/clean_csv2.csv', index=False)
        print("CSV 2 cleaned.")

    def merge_and_store(**kwargs):
        df1 = pd.read_csv('/opt/airflow/data/clean_csv1.csv')
        df2 = pd.read_csv('/opt/airflow/data/clean_csv2.csv')
        merged_df = pd.merge(df1, df2, on='id')
        # Store the merged data into PostgreSQL
        engine = create_engine('postgresql+psycopg2://airflow:airflow@postgres:5432/airflow')
        merged_df.to_sql('merged_data', engine, if_exists='replace', index=False)
        print("Data merged and stored in PostgreSQL.")

    # Define tasks
    task_ingest_csv1 = PythonOperator(
        task_id='ingest_csv1',
        python_callable=ingest_csv1,
    )

    task_ingest_csv2 = PythonOperator(
        task_id='ingest_csv2',
        python_callable=ingest_csv2,
    )

    task_clean_csv1 = PythonOperator(
        task_id='clean_csv1',
        python_callable=clean_csv1,
    )

    task_clean_csv2 = PythonOperator(
        task_id='clean_csv2',
        python_callable=clean_csv2,
    )

    task_merge_and_store = PythonOperator(
        task_id='merge_and_store',
        python_callable=merge_and_store,
    )

    # Set task dependencies
    task_ingest_csv1 >> task_clean_csv1
    task_ingest_csv2 >> task_clean_csv2
    [task_clean_csv1, task_clean_csv2] >> task_merge_and_store