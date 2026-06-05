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
    && arch=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/') \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/${arch}/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

USER airflow

# Install Spark provider + PySpark once at image build time.
# The constraints file keeps provider/dependency versions compatible with Airflow.
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt" \
    apache-airflow-providers-apache-spark \
    pyspark==3.5.3

# PySpark installed by pip contains spark-submit under this package path.
ENV SPARK_HOME=/home/airflow/.local/lib/python3.11/site-packages/pyspark
ENV PATH="${SPARK_HOME}/bin:/home/airflow/.local/bin:${PATH}"

# These are mounted by docker-compose.
ENV HADOOP_CONF_DIR=/opt/airflow/conf/hadoop
ENV SPARK_CONF_DIR=/opt/airflow/conf/spark