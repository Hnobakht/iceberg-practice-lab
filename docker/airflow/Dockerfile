FROM apache/airflow:3.2.2-python3.11 AS base

ARG AIRFLOW_VERSION=3.2.2
ARG PYTHON_VERSION=3.11

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        openjdk-17-jre-headless \
        procps \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

USER airflow

# use airflow_constraints.txt file if githubusercontent.com is not accessible
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt" \
    apache-airflow-providers-apache-spark \
    pyspark==3.5.8

ENV SPARK_HOME=/home/airflow/.local/lib/python3.11/site-packages/pyspark
ENV PATH="${SPARK_HOME}/bin:/home/airflow/.local/bin:${PATH}"

ENV HADOOP_CONF_DIR=/opt/airflow/conf/hadoop
ENV SPARK_CONF_DIR=/opt/airflow/conf/spark

# ============================================================
# First build the base image manually:
# docker build --target base -t bigdata-airflow:3.2.2-spark .
# ============================================================
FROM bigdata-airflow:3.2.2-spark AS final

USER root

# kubectl installation
RUN apt-get update \
    && arch=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/') \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/${arch}/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow