from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
}

dag = DAG(
    'spark_submit_k8s_example',
    default_args=default_args,
    description='Spark submit on K8s example with Iceberg and HDFS',
    catchup=False,
)

# Configuration for Spark on Kubernetes
spark_k8s_conf = {
    'spark.master': 'k8s://https://k3s:6443',
    'spark.submit.deployMode': 'cluster',
    # 'spark.kubernetes.container.image': 'spark:3.5.8-scala2.12-java17-python3-ubuntu',
    'spark.kubernetes.container.image': 'spark:3.5.10-scala2.12-java17-python3-ubuntu',
    'spark.kubernetes.authenticate.driver.serviceAccountName': 'spark',
    'spark.kubernetes.namespace': 'default',

    # Expose local jobs/data to the Spark pods via hostPath (since they are mounted into the K3s node)
    'spark.kubernetes.driver.volumes.hostPath.jobs.mount.path': '/opt/airflow/jobs',
    'spark.kubernetes.driver.volumes.hostPath.jobs.options.path': '/opt/spark/jobs',
    'spark.kubernetes.driver.volumes.hostPath.jobs.mount.readOnly': 'true',
    'spark.kubernetes.executor.volumes.hostPath.jobs.mount.path': '/opt/airflow/jobs',
    'spark.kubernetes.executor.volumes.hostPath.jobs.options.path': '/opt/spark/jobs',
    'spark.kubernetes.executor.volumes.hostPath.jobs.mount.readOnly': 'true',

    # For bcprov configs
    # 'spark.driver.extraClassPath': '/opt/spark/extra-jars/bcprov-jdk15on-1.68.jar',
    # 'spark.executor.extraClassPath': '/opt/spark/extra-jars/bcprov-jdk15on-1.68.jar',

    # Mount extra-jars to Spark pods on K8s
    'spark.kubernetes.driver.volumes.hostPath.jars.mount.path': '/opt/spark/extra-jars',
    'spark.kubernetes.driver.volumes.hostPath.jars.options.path': '/opt/spark/extra-jars',
    'spark.kubernetes.driver.volumes.hostPath.jars.mount.readOnly': 'true',
    'spark.kubernetes.executor.volumes.hostPath.jars.mount.path': '/opt/spark/extra-jars',
    'spark.kubernetes.executor.volumes.hostPath.jars.options.path': '/opt/spark/extra-jars',
    'spark.kubernetes.executor.volumes.hostPath.jars.mount.readOnly': 'true',

    # Networking and Big Data stack integration
    'spark.hadoop.fs.defaultFS': 'hdfs://hdfs-namenode:9000',
    'spark.sql.catalog.hms': 'org.apache.iceberg.spark.SparkCatalog',
    'spark.sql.catalog.hms.type': 'hive',
    'spark.sql.catalog.hms.uri': 'thrift://hive-metastore:9083',
    'spark.sql.catalog.hms.warehouse': 'hdfs://hdfs-namenode:9000/warehouse/iceberg',
    'spark.sql.extensions': 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions',
    'spark.jars': '/opt/spark/extra-jars/iceberg-spark-runtime-3.5_2.12-1.6.1.jar',
}

submit_job = SparkSubmitOperator(
    task_id='submit_hello_world',
    application='/opt/airflow/jobs/hello_world.py',
    name='spark-on-k8s-hello-world',
    conn_id='spark_k8s',
    conf=spark_k8s_conf,
    # env_vars={
    #     'SPARK_SUBMIT_OPTS': '--driver-class-path /opt/spark/extra-jars/bcprov-jdk15on-1.68.jar'
    # },
    dag=dag,
)
