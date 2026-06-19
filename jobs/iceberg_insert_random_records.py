import argparse
import uuid

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    concat,
    current_date,
    current_timestamp,
    expr,
    from_unixtime,
    lit,
    rand,
    round as spark_round,
    unix_timestamp,
)


def build_random_records(spark: SparkSession, rows: int, batch_id: str):
    random_seconds = (rand(seed=66) * lit(30 * 24 * 60 * 60)).cast("int")

    return (
        spark.range(0, rows, 1, numPartitions=4)
        .withColumn("customer_id", (rand(seed=11) * lit(1_000_000)).cast("int"))
        .withColumn("customer_name", concat(lit("customer_"), col("customer_id").cast("string")))
        .withColumn("email", concat(lit("customer_"), col("customer_id").cast("string"), lit("@example.com")))
        .withColumn(
            "country",
            expr("element_at(array('US','DE','FR','GB','IN','CA','BR','JP'), cast(rand(22) * 8 as int) + 1)"),
        )
        .withColumn(
            "event_type",
            expr("element_at(array('view','click','cart','purchase','refund'), cast(rand(33) * 5 as int) + 1)"),
        )
        .withColumn("amount", spark_round((rand(seed=44) * lit(5000)) + lit(5), 2).cast("double"))
        .withColumn("quantity", ((rand(seed=55) * lit(20)) + lit(1)).cast("int"))
        .withColumn(
            "event_ts",
            from_unixtime((unix_timestamp(current_timestamp()) - random_seconds).cast("bigint")).cast("timestamp"),
        )
        .withColumn("created_date", expr("date_sub(current_date(), cast(rand(77) * 30 as int))"))
        .withColumn("is_active", (rand(seed=88) > lit(0.15)).cast("boolean"))
        .withColumn("batch_id", lit(batch_id))
        .select(
            "id",
            "customer_id",
            "customer_name",
            "email",
            "country",
            "event_type",
            "amount",
            "quantity",
            "event_ts",
            "created_date",
            "is_active",
            "batch_id",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True, help="Fully qualified table, for example hms.demo.random_records")
    parser.add_argument("--rows", type=int, default=10_000, help="Number of random rows to append")
    args = parser.parse_args()

    if args.rows <= 0:
        raise ValueError("--rows must be greater than 0")

    batch_id = str(uuid.uuid4())
    spark = SparkSession.builder.appName("IcebergInsertRandomRecords").getOrCreate()
    try:
        df = build_random_records(spark, args.rows, batch_id)

        print(f"Appending {args.rows} records to {args.table} with batch_id={batch_id}")
        df.writeTo(args.table).append()

        print("Inserted batch summary:")
        spark.sql(
            f"""
            SELECT
                batch_id,
                COUNT(*) AS inserted_rows,
                MIN(amount) AS min_amount,
                MAX(amount) AS max_amount,
                ROUND(AVG(amount), 2) AS avg_amount
            FROM {args.table}
            WHERE batch_id = '{batch_id}'
            GROUP BY batch_id
            """
        ).show(truncate=False)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
