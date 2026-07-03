import argparse

from pyspark.sql import SparkSession


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True, help="Fully qualified table, for example hms.demo.random_records")
    parser.add_argument("--limit", type=int, default=50, help="How many rows to print to Airflow logs")
    args = parser.parse_args()

    if args.limit <= 0:
        raise ValueError("--limit must be greater than 0")

    spark = SparkSession.builder.appName("IcebergSelectRecords").getOrCreate()
    try:
        print(f"Table summary for {args.table}")
        spark.sql(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                COUNT(DISTINCT batch_id) AS batches,
                MIN(created_date) AS min_created_date,
                MAX(created_date) AS max_created_date,
                ROUND(AVG(amount), 2) AS avg_amount,
                SUM(quantity) AS total_quantity
            FROM {args.table}
            """
        ).show(truncate=False)

        print("Rows by country and event_type:")
        spark.sql(
            f"""
            SELECT country, event_type, COUNT(*) AS records, ROUND(SUM(amount), 2) AS total_amount
            FROM {args.table}
            GROUP BY country, event_type
            ORDER BY country, event_type
            """
        ).show(200, truncate=False)

        print(f"Sample records, limited to {args.limit} rows to avoid huge Airflow logs:")
        spark.sql(
            f"""
            SELECT *
            FROM {args.table}
            ORDER BY id
            LIMIT {args.limit}
            """
        ).show(args.limit, truncate=False)

        print("Latest Iceberg snapshots:")
        spark.sql(
            f"""
            SELECT committed_at, snapshot_id, operation
            FROM {args.table}.snapshots
            ORDER BY committed_at DESC
            LIMIT 10
            """
        ).show(truncate=False)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
