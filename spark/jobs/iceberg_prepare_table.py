import argparse
import traceback
from typing import Tuple

from pyspark.sql import SparkSession


TABLE_DDL = """
CREATE TABLE {table} (
    id BIGINT,
    customer_id INT,
    customer_name STRING,
    email STRING,
    country STRING,
    event_type STRING,
    amount DOUBLE,
    quantity INT,
    event_ts TIMESTAMP,
    created_date DATE,
    is_active BOOLEAN,
    batch_id STRING
)
USING iceberg
TBLPROPERTIES (
    'format-version' = '2',
    'write.format.default' = 'parquet'
)
"""


def split_table_identifier(table: str) -> Tuple[str, str, str]:
    parts = table.split(".")
    if len(parts) < 3:
        raise ValueError("Use a fully qualified Iceberg table name like hms.demo.random_records")
    catalog = parts[0]
    namespace = ".".join(parts[1:-1])
    table_name = parts[-1]
    return catalog, namespace, table_name


def table_exists(spark: SparkSession, table: str) -> bool:
    catalog, namespace, table_name = split_table_identifier(table)
    rows = spark.sql(f"SHOW TABLES IN {catalog}.{namespace} LIKE '{table_name}'").collect()
    return any(row.tableName == table_name and not row.isTemporary for row in rows)


def truncate_table(spark: SparkSession, table: str) -> None:
    """Clear all rows from the table while preserving the table object and schema.

    For Iceberg, DELETE FROM works with the Spark Iceberg extensions enabled.
    TRUNCATE TABLE is kept as a fallback for non-Iceberg Spark tables.
    """
    try:
        spark.sql(f"DELETE FROM {table} WHERE TRUE")
        print(f"Truncated table with DELETE FROM: {table}")
    except Exception as delete_error:
        print("DELETE FROM failed; trying Spark TRUNCATE TABLE fallback.")
        print("DELETE error:")
        traceback.print_exception(type(delete_error), delete_error, delete_error.__traceback__)
        spark.sql(f"TRUNCATE TABLE {table}")
        print(f"Truncated table with TRUNCATE TABLE: {table}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True, help="Fully qualified table, for example hms.demo.random_records")
    args = parser.parse_args()

    spark = SparkSession.builder.appName("IcebergPrepareTable").getOrCreate()
    try:
        catalog, namespace, _ = split_table_identifier(args.table)
        namespace_identifier = f"{catalog}.{namespace}"

        spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {namespace_identifier}")
        print(f"Ensured namespace exists: {namespace_identifier}")

        if table_exists(spark, args.table):
            print(f"Table exists, truncating: {args.table}")
            truncate_table(spark, args.table)
        else:
            print(f"Table does not exist, creating: {args.table}")
            spark.sql(TABLE_DDL.format(table=args.table))
            print(f"Created table: {args.table}")

        spark.sql(f"DESCRIBE TABLE {args.table}").show(100, truncate=False)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
