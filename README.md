# Iceberg Practice Lab (under development)
--------------------------------------------

## 1. Start it

From bigdata-local/:
```

$ mkdir -p hdfs/namenode
$ mkdir -p hdfs/datanode
$chmod -R 777 hdfs

$ export AIRFLOW_UID=$(id -u)
$ docker compose up -d
```
Check containers:
```
docker compose ps
```
Open these:
```
HDFS NameNode UI:    http://localhost:9870
Spark Master UI:    http://localhost:8080
Spark Worker UI:    http://localhost:8081
Airflow UI:         http://localhost:8088
Hive Metastore:     thrift://localhost:9083
```
Airflow login:
```
username: airflow
password: airflow
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