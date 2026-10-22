# Iceberg Practice Lab ![Version](https://img.shields.io/github/v/tag/Hnobakht/iceberg-practice-lab?label=version)

This repository provides a local infrastructure to develop and practice ETL on a Big Data stack including HDFS, Hive Metastore, Iceberg, Spark, Trino, and Airflow. It also includes a K3s Kubernetes cluster to simulate Spark-on-Kubernetes deployments.

This is a teaching and practice lab designed to give you hands-on experience with modern data engineering tools.

The Spark stack uses these matching versions for standalone and Kubernetes jobs:

| Component | Version |
| --- | --- |
| Spark / PySpark / PySpark client | 4.1.3 |
| Scala | 2.13 |
| Java | 17 |
| Iceberg Spark runtime | 1.12.0 (`iceberg-spark-runtime-4.1_2.13`) |
| K3s | v1.32.13+k3s1 |
| kubectl | v1.32.13 |

Spark 4.1.3 is the latest stable release supported by the published Iceberg runtimes as of October 22, 2026. Spark 4.2.0 is newer, but Iceberg 1.12.0 does not publish a Spark 4.2 runtime; see the [Iceberg engine support matrix](https://iceberg.apache.org/multi-engine-support/) and [Spark 4.2 support tracking](https://github.com/apache/iceberg/issues/17959).

Spark 4 enables ANSI SQL mode by default: invalid casts and arithmetic overflow can now raise errors. Review the [Spark SQL migration guide](https://spark.apache.org/docs/4.1.3/sql-migration-guide.html) when adding jobs. The containers supply Java 17 and Python 3.10 or newer; Airflow uses Python 3.11.

Spark 4.1 requires [Kubernetes 1.32 or newer](https://spark.apache.org/docs/4.1.3/running-on-kubernetes.html#prerequisites). The lab upgrades K3s from 1.31 to 1.32 and pins Airflow's `kubectl` to the same Kubernetes version.

## 1. Config it

Before starting, you need to configure your environment. We provide two sample files based on your machine's RAM capacity:

- `.env_sample_8gb`: For machines with limited resources (~8GB RAM).
- `.env_sample_32gb`: For more powerful machines (~32GB RAM).

These files define memory limits for each service (e.g., `SPARK_WORKER_MEM_LIMIT`, `HIVE_METASTORE_MEM_LIMIT`) to ensure the lab runs smoothly without crashing your host system.

**To configure:**
Choose the appropriate file and rename it to `.env`:

```bash
# For 8GB RAM machines
cp .env_sample_8gb .env

# OR for 32GB+ RAM machines
cp .env_sample_32gb .env
```

## 2. Start it

Follow these steps in order to bring up the stack step by step.

### Step A: Build the Airflow Image
First, build the custom Airflow image that includes the necessary Spark and Kubernetes dependencies.
```bash
docker compose build airflow-scheduler
```
All Airflow services share this image. The final Docker stage builds its Spark base automatically, so no separate base-image build is needed.

When upgrading an existing checkout, rebuild this image and pull the matching Spark images before recreating the services:

```bash
docker compose pull spark-master spark-worker k3s k3s-init
docker compose up -d --force-recreate k3s k3s-init
docker compose up -d --force-recreate spark-master spark-worker \
    airflow-apiserver airflow-scheduler airflow-dag-processor airflow-worker airflow-triggerer
```

The matching Iceberg runtime JAR is bundled in `etc/jars` and mounted into both standalone containers and Kubernetes pods. Use the Spark 4.1 / Scala 2.13 runtime for these jobs.

### Step B: Core Services (Postgres & Redis)
Start the database and message broker.
```bash
docker compose up -d postgres redis
# Verify postgres is ready
docker compose exec postgres psql -U airflow -d airflow -c "\l"
```
*Expected output: `airflow, metastore_db`*

### Step C: Storage & Metastore (HDFS & Hive)
Start the HDFS cluster and the Hive Metastore.
```bash
# HDFS
docker compose up -d hdfs-namenode hdfs-datanode hdfs-init
docker compose logs -f hdfs-init # Wait for initialization to complete

# Hive Metastore
docker compose up -d postgres-driver-downloader hive-metastore
docker compose logs -f hive-metastore
```

### Step D: Query Engine & Processing (Trino & Spark)
Start Trino for SQL queries and Spark for distributed processing.
```bash
# Trino
docker compose up -d trino

# Spark Standalone
docker compose up -d spark-master spark-worker
```

### Step E: Kubernetes Cluster (K3s)
Start the local K3s cluster for Spark-on-K8s simulation.
```bash
docker compose up -d k3s k3s-init
```
note: `k3s-init` service runs every 30 seconds to keep k3s ip addresses sync with the docker-compose network.

### Step F: Orchestration (Airflow)
Finally, start the Airflow components.
```bash
docker compose up -d airflow-init
docker compose logs -f airflow-init # Wait for DB migrations

docker compose up -d airflow-apiserver airflow-scheduler airflow-dag-processor airflow-worker airflow-triggerer
```

### All in one step: 
Alternatively, you can start all services at the same time.
```bash
docker compose up -d
watch docker compose ps # watch and wait for all services to turn healthy
```

## 3. Access the UIs

Once everything is up, you can access the following interfaces:

- **Airflow UI:** [http://localhost:8080](http://localhost:8080) (User/Pass: `airflow` / `airflow`)
- **Spark Master UI:** [http://localhost:8081](http://localhost:8081)
- **Spark Worker UI:** [http://localhost:8082](http://localhost:8082)
- **HDFS NameNode UI:** [http://localhost:9870](http://localhost:9870)

---

## 4. Basic health checks

Verify that the main components are communicating correctly:

**Check HDFS:**
```bash
docker compose exec hdfs-namenode hdfs dfs -ls /
```

**Check Hive Metastore:**
```bash
docker compose exec hive-metastore bash -c '</dev/tcp/localhost/9083' && echo OK
```

**Check Trino connectivity to Hive Metastore:**
```bash
docker compose exec trino trino --execute "SHOW SCHEMAS FROM hms"
```

**Check K3s Cluster (from Airflow):**
```bash
docker compose exec airflow-scheduler kubectl get nodes
```

---

## 5. Spark Smoke Test (Iceberg)

To check the upgraded Spark runtime and demo pipeline without starting HDFS, Hive, Airflow, or Kubernetes, run the isolated smoke test. It uses a temporary local Iceberg catalog and checks first-run table detection, Python workers, inserting 10,000 records, queries, snapshots, deletion, and reinsertion:

```bash
docker run --rm --network none --hostname localhost \
    -e SPARK_LOCAL_IP=127.0.0.1 \
    --mount "type=bind,src=$PWD,dst=/lab,readonly" \
    spark:4.1.3-scala2.13-java17-python3-ubuntu \
    /opt/spark/bin/spark-submit --master 'local[2]' --driver-memory 512m \
    --conf spark.driver.host=127.0.0.1 \
    --jars /lab/etc/jars/iceberg-spark-runtime-4.1_2.13-1.12.0.jar \
    /lab/spark/tests/smoke_iceberg.py
```

Verify the integration of Spark, Iceberg, Hive Metastore, and HDFS.

Run this from the Spark master container to create an Iceberg table and insert data:
```bash
docker compose exec spark-master /opt/spark/bin/spark-sql \
    --conf spark.sql.catalog.hms=org.apache.iceberg.spark.SparkCatalog \
    --conf spark.sql.catalog.hms.type=hive \
    --conf spark.sql.catalog.hms.uri=thrift://hive-metastore:9083 \
    --conf spark.sql.catalog.hms.warehouse=hdfs://hdfs-namenode:9000/warehouse/iceberg \
    --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
    -e "
        CREATE NAMESPACE IF NOT EXISTS hms.demo;
        CREATE TABLE IF NOT EXISTS hms.demo.test_orders (order_id BIGINT, customer_id BIGINT, amount DOUBLE, order_date DATE) USING iceberg;
        INSERT INTO hms.demo.test_orders VALUES (1, 101, 25.50, DATE '2026-05-30'), (2, 102, 99.90, DATE '2026-05-30');
        SELECT * FROM hms.demo.test_orders;
    "
```

**Query the same Iceberg table from Trino:**
```bash
docker compose exec trino trino --execute "SELECT * from hms.demo.test_orders;"
```

---

## 6. Spark on Kubernetes (K3s) Guide

This lab includes a K3s cluster to simulate production Spark-on-K8s environments.

### Step 1: Verify Connectivity
The Airflow containers are pre-configured with `KUBECONFIG` and `kubectl`.
```bash
docker compose exec airflow-scheduler kubectl get nodes
```

### Step 2: Prepare your Spark Job
Place your Python scripts in the `./spark/jobs` directory. They will be automatically available to the Spark pods in Kubernetes at `/opt/spark/jobs`.

### Step 3: Run the Example DAG
1. Access the [Airflow UI](http://localhost:8080).
2. Unpause and trigger the `spark_submit_k8s_example` DAG.
3. This DAG uses the `SparkSubmitOperator` to submit the job to the K3s cluster.

### Step 4: Monitor the Spark Job on K8s
Watch the Spark pods being created:
```bash
docker compose exec airflow-scheduler kubectl get pods -w
```

### Step 5: Verify Integration
Check if the Spark job successfully wrote data to HDFS:
```bash
docker compose exec hdfs-namenode hdfs dfs -ls -R /warehouse/iceberg
```
