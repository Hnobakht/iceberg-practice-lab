from pyspark.sql import SparkSession

if __name__ == "__main__":
    spark = SparkSession.builder.appName("HelloWorld").getOrCreate()
    print("Hello from Spark on K8s!")
    df = spark.createDataFrame([(1, "foo"), (2, "bar")], ["id", "label"])
    df.show()
    spark.stop()
