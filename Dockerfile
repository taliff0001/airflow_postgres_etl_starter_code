# Use the official Apache Airflow image as the base
FROM apache/airflow:2.7.1

# Set the working directory in the container
WORKDIR /opt/airflow

# Install additional dependencies
USER root
RUN apt-get update && apt-get install -y \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Switch back to the airflow user
USER airflow

# Install Python dependencies
RUN pip install --no-cache-dir \
    pandas \
    sqlalchemy \
    psycopg2-binary \
    pendulum

# Copy the DAG file into the container
COPY --chown=airflow:root etl_pipeline.py /opt/airflow/dags/

# Set environment variables for PostgreSQL connection
ENV AIRFLOW__CORE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres:5432/airflow
ENV AIRFLOW__CORE__EXECUTOR=LocalExecutor

# Initialize the Airflow database
RUN airflow db init

# Create an admin user
RUN airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin

# Expose the webserver port
EXPOSE 8080

# Start the webserver
CMD ["airflow", "webserver"]