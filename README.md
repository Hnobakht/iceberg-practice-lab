# Iceberg Practice Lab
--------------------------------------------

This repository provides a local infrastructure to develop and practice ETL on a Big Data stack including HDFS, Hive Metastore, Iceberg, Spark, and Airflow. It also includes a K3s Kubernetes cluster to simulate Spark-on-Kubernetes deployments.

## 1. Start it

1. Build the base airflow image
```bash
docker build --target base -t bigdata-airflow:3.2.2-spark ./docker/airflow/
```

2. From the project root:
```bash
docker compose up -d postgres redis
docker compose exec postgres psql -U airflow -d airflow -c "\l"
```
You should see: `airflow, metastore_db`

3. Start HDFS:
```bash
docker compose up -d hdfs-namenode hdfs-datanode hdfs-init
docker compose logs -f hdfs-init
```

4. Start Hive Metastore:
```bash
docker compose up -d postgres-driver-downloader hive-metastore
docker compose logs -f hive-metastore
```

5. Start Spark (Standalone Cluster):
```bash
docker compose up -d spark-master spark-worker
```

6. Start Kubernetes (K3s):
```bash
docker compose up -d k3s k3s-init
docker compose logs -f k3s-init
```

7. Start Airflow:
```bash
docker compose up -d airflow-init airflow-apiserver airflow-scheduler airflow-dag-processor airflow-worker airflow-triggerer
docker compose logs -f airflow-init
```
Airflow login:
username: `airflow`
password: `airflow`

8. Open these URLs:
- **Airflow UI:** http://localhost:8080
- **Spark Master UI:** http://localhost:8081
- **Spark Worker UI:** http://localhost:8082
- **HDFS NameNode UI:** http://localhost:9870

## 2. Basic health checks

Check HDFS:
```bash
docker compose exec hdfs-namenode hdfs dfs -ls /
```

Check Hive Metastore:
```bash
docker compose exec hive-metastore bash -c '</dev/tcp/localhost/9083' && echo OK
```

Check K3s Cluster (from Airflow container):
```bash
docker compose exec airflow-scheduler kubectl get nodes
```

## 3. Spark Standalone Smoke Test (Iceberg)

Run this from the Spark master container to verify Iceberg + Hive Metastore + HDFS:
```bash
docker compose exec spark-master /opt/spark/bin/spark-sql \
    --conf spark.sql.catalog.hms=org.apache.iceberg.spark.SparkCatalog \
    --conf spark.sql.catalog.hms.type=hive \
    --conf spark.sql.catalog.hms.uri=thrift://hive-metastore:9083 \
    --conf spark.sql.catalog.hms.warehouse=hdfs://hdfs-namenode:9000/warehouse/iceberg \
    --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
    -e "
        CREATE NAMESPACE IF NOT EXISTS hms.lab;
        CREATE TABLE IF NOT EXISTS hms.lab.test_orders (order_id BIGINT, customer_id BIGINT, amount DOUBLE, order_date DATE) USING iceberg;
        INSERT INTO hms.lab.test_orders VALUES (1, 101, 25.50, DATE '2026-05-30'), (2, 102, 99.90, DATE '2026-05-30');
        SELECT * FROM hms.lab.test_orders;
    "
```

## 4. Spark on Kubernetes (K3s) Guide

This lab includes a K3s cluster to simulate production Spark-on-K8s environments.

### Step 1: Verify Connectivity
The Airflow containers are pre-configured with a `KUBECONFIG` and `kubectl`. Verify that Airflow can see the K3s cluster:
```bash
docker compose exec airflow-scheduler kubectl get nodes
```

### Step 2: Prepare your Spark Job
Place your Python scripts in the `./jobs` directory. They will be automatically available to the Spark pods in Kubernetes at `/opt/airflow/jobs`.

An example `hello_world.py` is already provided.

### Step 3: Run the Example DAG
1. Access the Airflow UI at http://localhost:8080.
2. Unpause and trigger the `spark_submit_k8s_example` DAG.
3. This DAG uses the `SparkSubmitOperator` with a pre-configured connection `spark_k8s` to submit the job to the K3s cluster.

### Step 4: Monitor the Spark Job on K8s
You can watch the Spark pods being created in the K3s cluster:
```bash
docker compose exec airflow-scheduler kubectl get pods -w
```

### Step 5: Verify Integration
The example DAG is configured to use Iceberg and HDFS. You can verify that the Spark job on K8s successfully interacted with the stack by checking the logs or HDFS:
```bash
docker compose exec hdfs-namenode hdfs dfs -ls -R /warehouse/iceberg
```

### drafts

```bash
docker compose exec airflow-worker spark-submit \
  --master k8s://https://k3s:6443 \
  --deploy-mode cluster \
  --name test-pi \
  --packages org.bouncycastle:bcpkix-jdk15on:1.68 \
  --class org.apache.spark.examples.SparkPi \
  --conf spark.kubernetes.container.image=spark:3.5.8-scala2.12-java17-python3-ubuntu \
  --conf spark.kubernetes.authenticate.driver.serviceAccountName=spark \
  --conf spark.kubernetes.namespace=default \
  --conf spark.jars.ivy=/home/airflow/.ivy2 \
  --conf spark.jars=/opt/spark/examples/jars/spark-examples_2.12-3.5.8.jar \
  local:///opt/spark/examples/jars/spark-examples_2.12-3.5.8.jar
```

```bash
sudo docker build \
  --network=host \
  --build-arg HTTP_PROXY=http://127.0.0.1:2080 \
  --build-arg HTTPS_PROXY=http://127.0.0.1:2080 \
  --build-arg http_proxy=http://127.0.0.1:2080 \
  --build-arg https_proxy=http://127.0.0.1:2080 \
  --build-arg NO_PROXY=localhost,127.0.0.1,::1,k3s,hdfs-namenode,hive-metastore,postgres,redis \
  --build-arg no_proxy=localhost,127.0.0.1,::1,k3s,hdfs-namenode,hive-metastore,postgres,redis \
  --target base \
  -t bigdata-airflow:3.2.2-spark \
  ./docker/airflow/
```