FROM apache/airflow:3.2.2-python3.11

ARG AIRFLOW_VERSION=3.2.2
ARG PYTHON_VERSION=3.11

USER root

# Java is required because spark-submit starts a JVM.
# procps is useful for Airflow/Celery process checks.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        openjdk-17-jre-headless \
        procps \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

USER airflow

# Install Spark provider + PySpark once at image build time.
# The constraints file keeps provider/dependency versions compatible with Airflow.
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt" \
    apache-airflow-providers-apache-spark \
    pyspark==3.5.8

# PySpark installed by pip contains spark-submit under this package path.
ENV SPARK_HOME=/home/airflow/.local/lib/python3.11/site-packages/pyspark
ENV PATH="${SPARK_HOME}/bin:/home/airflow/.local/bin:${PATH}"

# These are mounted by docker-compose.
ENV HADOOP_CONF_DIR=/opt/airflow/conf/hadoop
ENV SPARK_CONF_DIR=/opt/airflow/conf/spark