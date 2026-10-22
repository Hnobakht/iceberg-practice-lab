Use these exact files. This does **not** modify any existing DAG.

`dags/spark_job_debug_dag.py`

```python
from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

# -----------------------------------------------------------------------------
# Edit only this block when debugging another Spark job.
# -----------------------------------------------------------------------------
JOB_FILE = "iceberg_insert_random_records.py"
JOB_ARGS = [
    "--table",
    "hms.demo.random_records",
    "--rows",
    "10000",
]
SPARK_APP_NAME = "debug-iceberg-insert-random-records"

# Debug image must already exist inside K3s containerd.
SPARK_DEBUG_IMAGE = "spark-debug:3.5.8-scala2.12-java17-python3-ubuntu"

DEBUGPY_PORT = "5678"

DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
}

spark_k8s_debug_conf = {
    "spark.master": "k8s://https://k3s:6443",
    "spark.submit.deployMode": "cluster",
    "spark.kubernetes.container.image": SPARK_DEBUG_IMAGE,
    "spark.kubernetes.container.image.pullPolicy": "Never",
    "spark.kubernetes.authenticate.driver.serviceAccountName": "spark",
    "spark.kubernetes.namespace": "default",

    # jobs/ mounted into Spark driver and executor pods.
    "spark.kubernetes.driver.volumes.hostPath.jobs.mount.path": "/opt/airflow/jobs",
    "spark.kubernetes.driver.volumes.hostPath.jobs.options.path": "/opt/spark/jobs",
    "spark.kubernetes.driver.volumes.hostPath.jobs.mount.readOnly": "true",
    "spark.kubernetes.executor.volumes.hostPath.jobs.mount.path": "/opt/airflow/jobs",
    "spark.kubernetes.executor.volumes.hostPath.jobs.options.path": "/opt/spark/jobs",
    "spark.kubernetes.executor.volumes.hostPath.jobs.mount.readOnly": "true",

    # Iceberg runtime jar mounted into Spark driver and executor pods.
    "spark.kubernetes.driver.volumes.hostPath.jars.mount.path": "/opt/spark/extra-jars",
    "spark.kubernetes.driver.volumes.hostPath.jars.options.path": "/opt/spark/extra-jars",
    "spark.kubernetes.driver.volumes.hostPath.jars.mount.readOnly": "true",
    "spark.kubernetes.executor.volumes.hostPath.jars.mount.path": "/opt/spark/extra-jars",
    "spark.kubernetes.executor.volumes.hostPath.jars.options.path": "/opt/spark/extra-jars",
    "spark.kubernetes.executor.volumes.hostPath.jars.mount.readOnly": "true",

    # HDFS + Hive Metastore + Iceberg catalog.
    "spark.hadoop.fs.defaultFS": "hdfs://hdfs-namenode:9000",
    "spark.sql.catalog.hms": "org.apache.iceberg.spark.SparkCatalog",
    "spark.sql.catalog.hms.type": "hive",
    "spark.sql.catalog.hms.uri": "thrift://hive-metastore:9083",
    "spark.hadoop.hive.metastore.uris": "thrift://hive-metastore:9083",
    "spark.sql.catalog.hms.warehouse": "hdfs://hdfs-namenode:9000/warehouse/iceberg",
    "spark.sql.extensions": "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
    "spark.jars": "local:///opt/spark/extra-jars/iceberg-spark-runtime-3.5_2.12-1.6.1.jar",

    # Keep local debug runs light.
    "spark.sql.shuffle.partitions": "4",
    "spark.default.parallelism": "4",
    "spark.driver.memory": "1g",
    "spark.executor.memory": "1g",
    "spark.executor.cores": "1",

    # debugpy. Your job file must call wait_for_debugger_if_enabled() early.
    "spark.kubernetes.driverEnv.DEBUGPY_ENABLE": "1",
    "spark.kubernetes.driverEnv.DEBUGPY_WAIT_FOR_CLIENT": "1",
    "spark.kubernetes.driverEnv.DEBUGPY_LISTEN_HOST": "0.0.0.0",
    "spark.kubernetes.driverEnv.DEBUGPY_LISTEN_PORT": DEBUGPY_PORT,

    # Used by VS Code tasks.json to find the Spark driver pod.
    "spark.kubernetes.driver.label.spark-debugger": "true",
    "spark.kubernetes.driver.label.spark-debug-dag": "spark-job-debug-launcher",
}

with DAG(
    dag_id="spark_job_debug_launcher",
    default_args=DEFAULT_ARGS,
    description="One-task DAG for debugging Spark-on-Kubernetes Python jobs from VS Code",
    schedule=None,
    catchup=False,
    tags=["spark", "k8s", "debug", "vscode"],
) as dag:
    debug_spark_job = SparkSubmitOperator(
        task_id="debug_spark_job",
        application=f"local:///opt/airflow/jobs/{JOB_FILE}",
        name=SPARK_APP_NAME,
        conn_id="spark_k8s",
        conf=spark_k8s_debug_conf,
        application_args=JOB_ARGS,
        verbose=True,
    )

if __name__ == "__main__":
    dag.test()
```

`.vscode/launch.json`

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run debug launcher DAG via dag.test()",
      "type": "debugpy",
      "request": "launch",
      "program": "/opt/airflow/dags/spark_job_debug_dag.py",
      "cwd": "/opt/airflow",
      "console": "integratedTerminal",
      "env": {
        "AIRFLOW_HOME": "/opt/airflow",
        "AIRFLOW_CONFIG": "/opt/airflow/config/airflow.cfg",
        "KUBECONFIG": "/opt/labs/conf/kubeconfig/k3s.yaml"
      },
      "justMyCode": false
    },
    {
      "name": "Attach to Spark driver debugpy",
      "type": "debugpy",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "/opt/airflow/jobs",
          "remoteRoot": "/opt/airflow/jobs"
        }
      ],
      "preLaunchTask": "wait for Spark debug driver and port-forward debugpy",
      "postDebugTask": "stop Spark debugpy port-forward",
      "justMyCode": false
    }
  ],
  "compounds": [
    {
      "name": "Debug Spark job through Airflow + K8s",
      "configurations": [
        "Run debug launcher DAG via dag.test()",
        "Attach to Spark driver debugpy"
      ],
      "stopAll": true
    }
  ]
}
```

`.vscode/tasks.json`

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "wait for Spark debug driver and port-forward debugpy",
      "type": "shell",
      "command": "bash",
      "args": [
        "-lc",
        "set -euo pipefail\nPID_FILE=/tmp/spark-debugpy-port-forward.pid\nLOG_FILE=/tmp/spark-debugpy-port-forward.log\nPORT=5678\n\nif [ -f \"$PID_FILE\" ]; then\n  kill \"$(cat \"$PID_FILE\")\" >/dev/null 2>&1 || true\n  rm -f \"$PID_FILE\"\nfi\nrm -f \"$LOG_FILE\"\n\necho '[vscode] Waiting for Spark debug driver pod...'\nPOD=''\nPHASE=''\n\nfor _ in $(seq 1 240); do\n  POD=$(kubectl get pods -l spark-debugger=true --sort-by=.metadata.creationTimestamp --no-headers 2>/dev/null | awk '{print $1}' | tail -n 1 || true)\n\n  if [ -n \"$POD\" ]; then\n    PHASE=$(kubectl get pod \"$POD\" -o jsonpath='{.status.phase}' 2>/dev/null || true)\n    echo \"[vscode] Found pod/$POD phase=$PHASE\"\n\n    if [ \"$PHASE\" = 'Running' ]; then\n      break\n    fi\n  fi\n\n  sleep 2\ndone\n\nif [ -z \"$POD\" ] || [ \"$PHASE\" != 'Running' ]; then\n  echo '[vscode] ERROR: no running Spark debug driver pod found.' >&2\n  exit 1\nfi\n\necho \"[vscode] Starting kubectl port-forward pod/$POD ${PORT}:${PORT}\"\nkubectl port-forward \"pod/$POD\" \"${PORT}:${PORT}\" >\"$LOG_FILE\" 2>&1 &\nPF_PID=$!\necho \"$PF_PID\" > \"$PID_FILE\"\n\nfor _ in $(seq 1 60); do\n  if ! kill -0 \"$PF_PID\" >/dev/null 2>&1; then\n    echo '[vscode] ERROR: kubectl port-forward exited early:' >&2\n    cat \"$LOG_FILE\" >&2 || true\n    exit 1\n  fi\n\n  if python3 - <<'PY'\nimport socket\n\nsock = socket.socket()\nsock.settimeout(0.5)\ntry:\n    sock.connect(('127.0.0.1', 5678))\nexcept OSError:\n    raise SystemExit(1)\nfinally:\n    sock.close()\nPY\n  then\n    echo '[vscode] Spark debugpy port-forward is ready'\n    wait \"$PF_PID\"\n    exit $?\n  fi\n\n  sleep 1\ndone\n\necho '[vscode] ERROR: port-forward did not become ready.' >&2\ncat \"$LOG_FILE\" >&2 || true\nexit 1"
      ],
      "isBackground": true,
      "problemMatcher": {
        "owner": "spark-debugpy",
        "pattern": [
          {
            "regexp": "^(.*)$",
            "message": 1
          }
        ],
        "background": {
          "activeOnStart": true,
          "beginsPattern": "\\[vscode\\] Waiting for Spark debug driver pod\\.\\.\\.",
          "endsPattern": "\\[vscode\\] Spark debugpy port-forward is ready"
        }
      },
      "presentation": {
        "reveal": "always",
        "panel": "dedicated",
        "clear": true
      }
    },
    {
      "label": "stop Spark debugpy port-forward",
      "type": "shell",
      "command": "bash",
      "args": [
        "-lc",
        "PID_FILE=/tmp/spark-debugpy-port-forward.pid\nif [ -f \"$PID_FILE\" ]; then\n  kill \"$(cat \"$PID_FILE\")\" >/dev/null 2>&1 || true\n  rm -f \"$PID_FILE\"\nfi\necho '[vscode] Stopped Spark debugpy port-forward.'"
      ],
      "problemMatcher": []
    }
  ]
}
```
