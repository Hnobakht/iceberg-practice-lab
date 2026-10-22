"""Exercise the demo pipeline against a temporary local Iceberg catalog."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))

from pyspark.sql import SparkSession
from iceberg_check_table import table_exists as check_table_exists
from iceberg_insert_random_records import build_random_records
from iceberg_prepare_table import TABLE_DDL, table_exists, truncate_table


warehouse = TemporaryDirectory(prefix="iceberg-upgrade-smoke-")
spark = (
    SparkSession.builder.appName("SparkUpgradeSmokeTest")
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
    .config("spark.sql.catalog.hms", "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.hms.type", "hadoop")
    .config("spark.sql.catalog.hms.warehouse", Path(warehouse.name).as_uri())
    .config("spark.hadoop.fs.defaultFS", "file:///")
    .config("spark.sql.shuffle.partitions", "2")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")
try:
    assert spark.version == "4.1.3", spark.version
    assert spark.conf.get("spark.sql.ansi.enabled") == "true"
    assert spark.createDataFrame([(1, "foo"), (2, "bar")], ["id", "label"]).count() == 2
    table = "hms.demo.random_records"
    assert not check_table_exists(spark, table)
    assert not table_exists(spark, table)
    spark.sql("CREATE NAMESPACE hms.demo")
    assert not table_exists(spark, table)
    spark.sql(TABLE_DDL.format(table=table))
    assert table_exists(spark, table)
    assert check_table_exists(spark, table)
    build_random_records(spark, 10000, "upgrade-smoke").writeTo(table).append()
    result = spark.sql(f"SELECT COUNT(*) AS rows, COUNT(DISTINCT batch_id) AS batches FROM {table}").first()
    assert result.rows == 10000 and result.batches == 1, result
    assert spark.sql(f"SELECT * FROM {table} WHERE amount IS NULL OR event_ts IS NULL OR created_date IS NULL").count() == 0
    assert spark.sql(f"SELECT country, event_type, COUNT(*) FROM {table} GROUP BY country, event_type").count() == 40
    assert spark.sql(f"SELECT * FROM {table}.snapshots").count() == 1
    truncate_table(spark, table)
    assert spark.table(table).count() == 0
    build_random_records(spark, 10, "upgrade-smoke-rerun").writeTo(table).append()
    assert spark.table(table).count() == 10
    print("PASS: Spark 4.1.3 / Iceberg 1.12.0: Python workers, create, append 10000 rows, query, snapshots, delete, rerun; ANSI SQL enabled")
finally:
    spark.stop()
    warehouse.cleanup()
