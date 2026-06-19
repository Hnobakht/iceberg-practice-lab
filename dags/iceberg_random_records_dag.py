from datetime import datetime

from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

TABLE_NAME = "hms.demo.random_records"
RECORD_COUNT = "10000"
SELECT_LIMIT = "50"

DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
}

# Same Spark-on-K8s configuration pattern as the working hello_world DAG.
spark_k8s_conf = {
    "spark.master": "k8s://https://k3s:6443",
    "spark.submit.deployMode": "cluster",
    "spark.kubernetes.container.image": "spark:3.5.8-scala2.12-java17-python3-ubuntu",
    "spark.kubernetes.authenticate.driver.serviceAccountName": "spark",
    "spark.kubernetes.namespace": "default",

    # The Airflow container submits local:///opt/airflow/jobs/*.py.
    # Inside the K3s node, /opt/spark/jobs is host-mounted to /opt/airflow/jobs in the driver/executor pods.
    "spark.kubernetes.driver.volumes.hostPath.jobs.mount.path": "/opt/airflow/jobs",
    "spark.kubernetes.driver.volumes.hostPath.jobs.options.path": "/opt/spark/jobs",
    "spark.kubernetes.driver.volumes.hostPath.jobs.mount.readOnly": "true",
    "spark.kubernetes.executor.volumes.hostPath.jobs.mount.path": "/opt/airflow/jobs",
    "spark.kubernetes.executor.volumes.hostPath.jobs.options.path": "/opt/spark/jobs",
    "spark.kubernetes.executor.volumes.hostPath.jobs.mount.readOnly": "true",

    # Iceberg runtime jar mounted into the driver/executor pods.
    "spark.kubernetes.driver.volumes.hostPath.jars.mount.path": "/opt/spark/extra-jars",
    "spark.kubernetes.driver.volumes.hostPath.jars.options.path": "/opt/spark/extra-jars",
    "spark.kubernetes.driver.volumes.hostPath.jars.mount.readOnly": "true",
    "spark.kubernetes.executor.volumes.hostPath.jars.mount.path": "/opt/spark/extra-jars",
    "spark.kubernetes.executor.volumes.hostPath.jars.options.path": "/opt/spark/extra-jars",
    "spark.kubernetes.executor.volumes.hostPath.jars.mount.readOnly": "true",

    # HDFS + Hive Metastore + Iceberg catalog.
    "spark.hadoop.fs.defaultFS": "hdfs://hdfs-namenode.default.svc.cluster.local:9000",
    "spark.sql.catalog.hms": "org.apache.iceberg.spark.SparkCatalog",
    "spark.sql.catalog.hms.type": "hive",
    "spark.sql.catalog.hms.uri": "thrift://hive-metastore.default.svc.cluster.local:9083",
    "spark.hadoop.hive.metastore.uris": "thrift://hive-metastore.default.svc.cluster.local:9083",
    "spark.sql.catalog.hms.warehouse": "hdfs://hdfs-namenode.default.svc.cluster.local:9000/warehouse/iceberg",
    "spark.sql.extensions": "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
    "spark.jars": "local:///opt/spark/extra-jars/iceberg-spark-runtime-3.5_2.12-1.6.1.jar",

    # Keep the demo small enough for your local stack.
    "spark.sql.shuffle.partitions": "4",
    "spark.default.parallelism": "4",
    "spark.driver.memory": "1g",
    "spark.executor.memory": "1g",
    "spark.executor.cores": "1",
}

with DAG(
    dag_id="iceberg_random_records_pipeline",
    default_args=DEFAULT_ARGS,
    description="Check/create/truncate an Iceberg table, insert 10k random records, then query them with Spark on Kubernetes",
    schedule=None,
    catchup=False,
    tags=["spark", "k8s", "iceberg", "demo"],
) as dag:
    check_table_exists = SparkSubmitOperator(
        task_id="check_table_exists",
        application="local:///opt/airflow/jobs/iceberg_check_table.py",
        name="iceberg-check-table",
        conn_id="spark_k8s",
        conf=spark_k8s_conf,
        application_args=["--table", TABLE_NAME],
    )

    create_or_truncate_table = SparkSubmitOperator(
        task_id="create_or_truncate_table",
        application="local:///opt/airflow/jobs/iceberg_prepare_table.py",
        name="iceberg-create-or-truncate-table",
        conn_id="spark_k8s",
        conf=spark_k8s_conf,
        application_args=["--table", TABLE_NAME],
    )

    insert_random_records = SparkSubmitOperator(
        task_id="insert_random_records",
        application="local:///opt/airflow/jobs/iceberg_insert_random_records.py",
        name="iceberg-insert-random-records",
        conn_id="spark_k8s",
        conf=spark_k8s_conf,
        application_args=["--table", TABLE_NAME, "--rows", RECORD_COUNT],
    )

    select_records = SparkSubmitOperator(
        task_id="select_records",
        application="local:///opt/airflow/jobs/iceberg_select_records.py",
        name="iceberg-select-records",
        conn_id="spark_k8s",
        conf=spark_k8s_conf,
        application_args=["--table", TABLE_NAME, "--limit", SELECT_LIMIT],
    )

    check_table_exists >> create_or_truncate_table >> insert_random_records >> select_records