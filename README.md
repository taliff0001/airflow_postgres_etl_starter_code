# Airflow Pipeline Starter Code

This is the starter code for my data engineering project from Fall of 2024 (See the finished project [here](https://github.com/taliff0001/cs_440_airflow_etl_pipeline_project)).
It demonstrates an ETL (Extract, Transform, Load) pipeline using Apache Airflow,
Docker, and PostgreSQL. The pipeline ingests two CSV files, performs data cleaning,
merges the data, and stores the result in a PostgreSQL database

**Follow the instructions to clone the repository and start your own Apache Airflow project!**

## **Table of Contents**

- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Install Docker Desktop](#2-install-docker-desktop)
  - [3. Generate a Fernet Key](#3-generate-a-fernet-key)
  - [4. Create a `.env` File](#4-create-a-env-file)
  - [5. Initialize Airflow](#5-initialize-airflow)
  - [6. Start the Services](#6-start-the-services)
- [Running the ETL Pipeline](#running-the-etl-pipeline)
  - [1. Access the Airflow Web UI](#1-access-the-airflow-web-ui)
  - [2. Enable and Trigger the DAG](#2-enable-and-trigger-the-dag)
- [Verifying the Results](#verifying-the-results)
- [Stopping the Services](#stopping-the-services)
- [Notes](#notes)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## **Prerequisites**

- **Docker Desktop**: Install Docker Desktop for your operating system:
  - [Docker Desktop for Windows](https://docs.docker.com/desktop/windows/install/)
  - [Docker Desktop for Mac](https://docs.docker.com/desktop/mac/install/)
  - [Docker Engine for Linux](https://docs.docker.com/engine/install/)

- **Command Line Interface**: Use a terminal application (Command Prompt, PowerShell, Terminal, etc.)

- **Python 3.x**: Required for generating the Fernet key (if not using the one provided).

---

## **Project Structure**

```
airflow_etl_project/
├── dags/
│   └── etl_pipeline.py
├── data/
│   ├── csv1.csv
│   └── csv2.csv
├── .env
├── .gitignore
├── docker-compose.yml
├── README.md
```

- **dags/**: Contains the Airflow DAG (`etl_pipeline.py`).
- **data/**: Contains the sample CSV files (`csv1.csv` and `csv2.csv`).
- **.env**: Environment variables file containing the Fernet key.
- **docker-compose.yml**: Docker Compose configuration file.
- **README.md**: Project documentation (this file).

---

## **Setup Instructions**

### **1. Clone the Repository**

Open your terminal and run:

```bash
git clone https://github.com/taliff0001/airflow_postgres_etl_starter_code.git
cd airflow_etl_project
```

### **2. Install Docker Desktop**

- **Windows and Mac**: Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop).
- **Linux**: Follow the [Docker Engine installation guide](https://docs.docker.com/engine/install/).

Ensure Docker is running before proceeding.

### **3. Generate a Fernet Key**

Airflow requires a Fernet key for encrypting sensitive data.

#### **Option 1: Use the Provided Key**

A sample Fernet key is included in the `.env` file. You can use it as is.

#### **Option 2: Generate Your Own Key**

If you prefer to generate a new Fernet key:

1. Run the following command:

   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. Copy the generated key.

### **4. Create a `.env` File**

Create a `.env` file in the project root directory (if not already present):

```bash
touch .env
```

Add the following content to the `.env` file:

```dotenv
AIRFLOW__CORE__FERNET_KEY=YOUR_GENERATED_FERNET_KEY
```

- Replace `YOUR_GENERATED_FERNET_KEY` with the key you generated or the one provided.

### **5. Initialize Airflow**

Run the following commands to set up Airflow:

```bash
# Set the Airflow home directory
export AIRFLOW_HOME=$(pwd)

# Initialize the Airflow database
docker-compose run airflow airflow db init

# Create an admin user
docker-compose run airflow airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin
```

### **6. Start the Services**

Start the Airflow and PostgreSQL services using Docker Compose:

```bash
docker-compose up -d
```

---

## **Running the ETL Pipeline**

### **1. Access the Airflow Web UI**

Open your web browser and navigate to:

```
http://localhost:8080
```

- **Username**: `admin`
- **Password**: `admin`

### **2. Enable and Trigger the DAG**

1. In the Airflow web UI, locate the DAG named `csv_to_postgres_etl`.
2. Toggle the DAG to **On** (the switch should turn blue).
3. Click the **Trigger DAG** button (a play icon) to manually start the pipeline.

---

## **Verifying the Results**

To confirm that the data has been successfully processed and stored:

1. **Access the PostgreSQL Container**:

   ```bash
   docker exec -it $(docker ps -qf "name=postgres") psql -U airflow -d airflow
   ```

2. **Query the `merged_data` Table**:

   ```sql
   SELECT * FROM merged_data;
   ```

3. **Exit the PostgreSQL Shell**:

   ```sql
   \q
   ```

---

## **Stopping the Services**

When you're done, you can stop the Docker containers:

```bash
docker-compose down
```

---

## **Notes**

- **Data Directory**: The `data` directory contains the sample CSV files. These are mounted into the Airflow containers.

- **Environment Variables**: The `.env` file stores sensitive information like the Fernet key. Do not commit this file to version control if it contains sensitive data.

- **Docker Volumes**: Docker volumes are used to persist data for PostgreSQL and Airflow.

---

## **Troubleshooting**

- **Docker Permission Issues (Linux)**:

  If you encounter permission issues on Linux, you may need to manage Docker as a non-root user. Follow the [post-installation steps for Linux](https://docs.docker.com/engine/install/linux-postinstall/).

- **Port Conflicts**:

  Ensure that ports `5432` (PostgreSQL) and `8080` (Airflow web UI) are not in use by other applications.

- **Environment Variables Not Loaded**:

  If the Fernet key is not being recognized, make sure that the `.env` file is correctly formatted and that Docker Compose is loading it.

- **Airflow UI Not Accessible**:

  - Check if the containers are running:

    ```bash
    docker-compose ps
    ```

  - View logs for any errors:

    ```bash
    docker-compose logs airflow
    docker-compose logs airflow_scheduler
    ```

---

## **License**

This project is licensed under the MIT License.

---

**Enjoy using the Airflow ETL Pipeline Project! If you have any questions or issues, feel free to reach out.**
