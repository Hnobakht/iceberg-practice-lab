FROM apache/airflow:3.2.2-python3.11 AS base

ARG AIRFLOW_VERSION=3.2.2
ARG PYTHON_VERSION=3.11
ARG SPARK_VERSION=4.1.3

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
    "apache-airflow==${AIRFLOW_VERSION}" \
    apache-airflow-providers-apache-spark

# Install the full Spark distribution after the constrained provider dependencies.
RUN pip install --no-cache-dir \
    "apache-airflow==${AIRFLOW_VERSION}" \
    "pyspark-client==${SPARK_VERSION}" \
    "pyspark==${SPARK_VERSION}"

ENV SPARK_HOME=/home/airflow/.local/lib/python3.11/site-packages/pyspark
ENV PATH="${SPARK_HOME}/bin:/home/airflow/.local/bin:${PATH}"

ENV HADOOP_CONF_DIR=/opt/labs/conf/hadoop
ENV SPARK_CONF_DIR=/opt/labs/conf/spark

# Reuse this build's Spark client so Compose cannot pick up a stale base image.
FROM bigdata-airflow:3.2.2-spark4.1.3-python11 AS final

ARG KUBECTL_VERSION=v1.32.13

USER root

# kubectl installation
RUN apt-get update \
    && arch=$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/') \
    && curl -fsSLO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${arch}/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

    
ARG BOUNCYCASTLE_VERSION=1.78.1
RUN set -eux; \
    for artifact in bcprov bcpkix bcutil; do \
      curl -fsSL \
        "https://repo1.maven.org/maven2/org/bouncycastle/${artifact}-jdk18on/${BOUNCYCASTLE_VERSION}/${artifact}-jdk18on-${BOUNCYCASTLE_VERSION}.jar" \
        -o "${SPARK_HOME}/jars/${artifact}-jdk18on-${BOUNCYCASTLE_VERSION}.jar"; \
    done; \
    chown airflow:0 "${SPARK_HOME}"/jars/bc*-jdk18on-${BOUNCYCASTLE_VERSION}.jar; \
    chmod 0644 "${SPARK_HOME}"/jars/bc*-jdk18on-${BOUNCYCASTLE_VERSION}.jar

USER airflow
