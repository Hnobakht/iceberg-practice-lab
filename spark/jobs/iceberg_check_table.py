import argparse
from typing import Tuple

from pyspark.sql import SparkSession


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
    # Unlike SHOW TABLES, this also returns False for a missing Iceberg namespace.
    return spark.catalog.tableExists(f"{catalog}.{namespace}.{table_name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True, help="Fully qualified table, for example hms.demo.random_records")
    args = parser.parse_args()

    spark = SparkSession.builder.appName("IcebergCheckTable").getOrCreate()
    try:
        exists = table_exists(spark, args.table)
        print("=" * 80)
        print(f"TABLE_CHECK table={args.table} exists={str(exists).lower()}")
        print("=" * 80)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
