#!/bin/sh
set -eu

SYNC_INTERVAL_SECONDS="${SYNC_INTERVAL_SECONDS:-30}"
MANIFEST_PATH="/tmp/docker-compose-endpoints.yaml"

log() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

resolve_ip() {
  name="$1"
  max_attempts="${2:-90}"
  attempt=1

  while [ "$attempt" -le "$max_attempts" ]; do
    ip=""

    if command -v getent >/dev/null 2>&1; then
      ip="$(getent hosts "$name" 2>/dev/null | awk '{print $1}' | grep -E '^[0-9]+\.' | head -n 1 || true)"
    fi

    if [ -z "$ip" ] && command -v nslookup >/dev/null 2>&1; then
      ip="$(nslookup "$name" 2>/dev/null | awk '/^Address[ 0-9]*: / {print $NF}' | grep -E '^[0-9]+\.' | tail -n 1 || true)"
    fi

    if [ -z "$ip" ] && command -v ping >/dev/null 2>&1; then
      ip="$(ping -c 1 "$name" 2>/dev/null | sed -n 's/^PING [^(]*(\([^)]*\)).*/\1/p' | grep -E '^[0-9]+\.' | head -n 1 || true)"
    fi

    if [ -n "$ip" ]; then
      printf '%s\n' "$ip"
      return 0
    fi

    log "Waiting for Docker DNS name $name to resolve... attempt $attempt/$max_attempts"
    attempt=$((attempt + 1))
    sleep 2
  done

  log "ERROR: could not resolve $name from the Docker network."
  return 1
}

write_manifest() {
  hive_ip="$1"
  nn_ip="$2"
  dn_ip="$3"
  postgres_ip="$4"

  cat > "$MANIFEST_PATH" <<EOF_MANIFEST
apiVersion: v1
kind: Service
metadata:
  name: hive-metastore
  namespace: default
spec:
  ports:
    - name: thrift
      port: 9083
      targetPort: 9083
---
apiVersion: v1
kind: Endpoints
metadata:
  name: hive-metastore
  namespace: default
subsets:
  - addresses:
      - ip: ${hive_ip}
    ports:
      - name: thrift
        port: 9083
---
apiVersion: v1
kind: Service
metadata:
  name: hdfs-namenode
  namespace: default
spec:
  ports:
    - name: rpc
      port: 9000
      targetPort: 9000
    - name: web
      port: 9870
      targetPort: 9870
---
apiVersion: v1
kind: Endpoints
metadata:
  name: hdfs-namenode
  namespace: default
subsets:
  - addresses:
      - ip: ${nn_ip}
    ports:
      - name: rpc
        port: 9000
      - name: web
        port: 9870
---
apiVersion: v1
kind: Service
metadata:
  name: hdfs-datanode
  namespace: default
spec:
  ports:
    - name: web
      port: 9864
      targetPort: 9864
    - name: data
      port: 9866
      targetPort: 9866
    - name: ipc
      port: 9867
      targetPort: 9867
---
apiVersion: v1
kind: Endpoints
metadata:
  name: hdfs-datanode
  namespace: default
subsets:
  - addresses:
      - ip: ${dn_ip}
    ports:
      - name: web
        port: 9864
      - name: data
        port: 9866
      - name: ipc
        port: 9867
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: default
spec:
  ports:
    - name: postgres
      port: 5432
      targetPort: 5432
---
apiVersion: v1
kind: Endpoints
metadata:
  name: postgres
  namespace: default
subsets:
  - addresses:
      - ip: ${postgres_ip}
    ports:
      - name: postgres
        port: 5432
EOF_MANIFEST
}

remove_old_externalname_services() {
  for service_name in hive-metastore hdfs-namenode hdfs-datanode postgres; do
    service_type="$(kubectl get svc "$service_name" -n default -o jsonpath='{.spec.type}' 2>/dev/null || true)"
    if [ "$service_type" = "ExternalName" ]; then
      log "Deleting old ExternalName service $service_name so it can be recreated as a normal ClusterIP service."
      kubectl delete svc "$service_name" -n default
    fi
  done
}

apply_manifest_once() {
  hive_ip="$(resolve_ip hive-metastore)"
  nn_ip="$(resolve_ip hdfs-namenode)"
  dn_ip="$(resolve_ip hdfs-datanode)"
  postgres_ip="$(resolve_ip postgres)"

  log "Resolved Docker endpoints: hive-metastore=${hive_ip}, hdfs-namenode=${nn_ip}, hdfs-datanode=${dn_ip}, postgres=${postgres_ip}"
  write_manifest "$hive_ip" "$nn_ip" "$dn_ip" "$postgres_ip"
  remove_old_externalname_services
  kubectl apply -f "$MANIFEST_PATH"
  kubectl get svc,endpoints hive-metastore hdfs-namenode hdfs-datanode postgres
}

log "Preparing kubeconfig..."
until [ -f /etc/rancher/k3s/k3s.yaml ]; do sleep 2; done
sed -i 's/127.0.0.1/k3s/g' /etc/rancher/k3s/k3s.yaml

log "Waiting for K3s to be ready..."
until kubectl get nodes >/dev/null 2>&1; do sleep 2; done

log "Applying Spark RBAC..."
kubectl apply -f /k8s/spark-rbac.yaml

log "Starting Docker-to-Kubernetes service endpoint sync."
while true; do
  apply_manifest_once

  if [ "${SYNC_ONCE:-false}" = "true" ]; then
    log "SYNC_ONCE=true, exiting after one successful sync."
    exit 0
  fi

  sleep "$SYNC_INTERVAL_SECONDS"
done
