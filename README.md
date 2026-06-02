# Iceberg Practice Lab (under development)
--------------------------------------------

## 1. Start it

1. From bigdata-local/:
```
docker compose up -d postgres redis
docker compose exec postgres psql -U airflow -d airflow -c "\l"
```
You should see: `airflow, metastore_db`

2. Start HDFS
```
docker compose up -d hdfs-namenode hdfs-datanode hdfs-init
docker compose logs -f hdfs-init
```

3. Start Hive Metastore:
```
docker compose up -d postgres-driver-downloader hive-metastore
docker compose logs -f hive-metastore
```

4. Start Spark:
```
docker compose up -d spark-master spark-worker
```

5. Start Airflow
```
docker compose up -d airflow-init
docker compose logs -f airflow-init

docker compose up -d airflow-apiserver airflow-scheduler airflow-dag-processor airflow-worker airflow-triggerer
```
Airflow login:
username: `airflow`
password: `airflow`

6. Open these URLS:
```
Airflow API/UI:    http://localhost:8080
Spark Master UI:   http://localhost:8081
Spark Worker UI:   http://localhost:8082
HDFS NameNode UI:  http://localhost:9870
Hive Metastore:    thrift://localhost:9083
Postgres:          localhost:5432
```

```
## 2. Basic health checks

Check HDFS:
```
$ docker compose exec hdfs-namenode hdfs dfs -ls /
```
You should see something like:
```
/warehouse
/tmp
/user
```
Check Hive Metastore port:
```
docker compose exec hive-metastore bash -c '</dev/tcp/localhost/9083' && echo OK
```
Check Spark master:
```
$ docker compose exec spark-master /opt/spark/bin/spark-submit --version
```
Check Spark can see HDFS config:
```
$ docker compose exec spark-master hdfs dfs -ls hdfs://hdfs-namenode:9000/
```
## 3. Very small Iceberg smoke test

Run this from the Spark master container:
```
$ docker compose exec spark-master /opt/spark/bin/spark-sql \
    --conf spark.sql.catalog.hms=org.apache.iceberg.spark.SparkCatalog \
    --conf spark.sql.catalog.hms.type=hive \
    --conf spark.sql.catalog.hms.uri=thrift://hive-metastore:9083 \
    --conf spark.sql.catalog.hms.warehouse=hdfs://hdfs-namenode:9000/warehouse/iceberg \
    --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
    -e "
        CREATE NAMESPACE IF NOT EXISTS hms.lab;

        CREATE TABLE IF NOT EXISTS hms.lab.test_orders (
        order_id BIGINT,
        customer_id BIGINT,
        amount DOUBLE,
        order_date DATE
        )
        USING iceberg;

        INSERT INTO hms.lab.test_orders VALUES
        (1, 101, 25.50, DATE '2026-05-30'),
        (2, 102, 99.90, DATE '2026-05-30');

        SELECT * FROM hms.lab.test_orders;
    "
```
Then check files in HDFS:
```
$ docker compose exec hdfs-namenode hdfs dfs -ls -R /warehouse/iceberg
```
You should see Iceberg metadata and data files under `/warehouse/iceberg.`