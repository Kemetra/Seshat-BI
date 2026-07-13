# Research Notes (sources)

This layer was grounded in current (2025–2026) public documentation and practitioner
writing, then re-expressed in original words and re-cast into the fictional retail domain.
No source text is reproduced (see `references/copyright-and-sources.md`). This file is a
citation list for traceability only.

## Topics and representative sources

### Spark performance, shuffle, partition tuning, AQE
- Apache Spark — Performance Tuning (official docs): https://spark.apache.org/docs/latest/sql-performance-tuning.html
- Databricks — Adaptive Query Execution: https://www.databricks.com/blog/2020/05/29/adaptive-query-execution-speeding-up-spark-sql-at-runtime.html
- Spark partition tuning (luminousmen): https://luminousmen.com/post/spark-tips-partition-tuning/
- AWS Glue — Optimize shuffles: https://docs.aws.amazon.com/prescriptive-guidance/latest/tuning-aws-glue-for-apache-spark/optimize-shuffles.html

### Data skew, salting, broadcast vs shuffle joins
- Mitigating data skew in Spark (canadiandataguy): https://www.canadiandataguy.com/p/a-deep-dive-into-skewed-joins-groupby
- Spark joins / broadcast / skew (DataCamp): https://www.datacamp.com/tutorial/pyspark-joins
- Accelerating Spark joins (dev.to): https://dev.to/sandeepk27/day-8-accelerating-spark-joins-broadcast-shuffle-optimization-skew-handling-13gd

### Anti-patterns: collect()/driver memory, small files, coalesce(1), UDFs
- Bringing too much data back to the driver (Spark flowchart): https://holdenk.github.io/spark-flowchart/details/best-pratice-collect/
- Top Spark code mistakes (Databricks community): https://community.databricks.com/t5/technical-blog/top-10-code-mistakes-that-degrade-your-spark-performance/ba-p/118468
- Anti-patterns in a PySpark ETL pipeline (Medium): https://medium.com/@ChillData/breaking-the-bottlenecks-lessons-from-anti-patterns-in-our-pyspark-etl-pipeline-660fc297b25e

### Single-node engines vs Spark (Polars, DuckDB)
- DuckDB vs Polars on large Parquet (codecentric): https://www.codecentric.de/en/knowledge-hub/blog/duckdb-vs-polars-performance-and-memory-with-massive-parquet-data
- 650GB Delta Lake — Polars vs DuckDB vs Spark (data engineering central): https://dataengineeringcentral.substack.com/p/650gb-of-data-delta-lake-on-s3-polars
- DuckDB/Polars won't replace Spark (Medium / israeli-tech-radar): https://medium.com/israeli-tech-radar/will-duckdb-replace-spark-maybe-polars-will-9728f6d86c8d

### Data quality / reconciliation at scale
- Great Expectations — data quality volume: https://greatexpectations.io/blog/exploring-data-quality-volume/
- Data quality with PySpark + Great Expectations (Databricks community): https://community.databricks.com/t5/community-articles/data-quality-with-pyspark-and-great-expectations-on-databricks/td-p/128912
- Data quality & reconciliation concepts (Medium / Geeks Data): https://medium.com/geeks-data/data-quality-and-data-reconciliation-in-data-engineering-concepts-and-processes-5672c081d2fa

### File / table formats, incremental, idempotency (Parquet, Delta, Iceberg)
- Iceberg vs Delta Lake — schema & partition evolution (Flexera): https://www.flexera.com/blog/finops/iceberg-vs-delta-lake-schema-partition/
- Delta / Parquet / Iceberg update guide (Medium): https://medium.com/@shreerajgujar/delta-lake-parquet-or-iceberg-a-guide-to-efficient-data-updates-in-data-lakes-7a5ae8fc80d7
- Iceberg vs Delta Lake (DataCamp): https://www.datacamp.com/blog/iceberg-vs-delta-lake

> Note: URLs captured June 2026. They support the concepts; all wording here is original.
