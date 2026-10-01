import json
from typing import Any, Dict, List
from google.cloud import bigquery
from troubleshooting_agent import config

logger = config.get_logger("bigquery_service")
_client = None


def get_bq_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=config.GOOGLE_CLOUD_PROJECT)
    return _client


def get_table_columns() -> List[str]:
    client = get_bq_client()
    table = client.get_table(config.FULL_TABLE_PATH)
    excluded = {"embedding", "search_content"}
    columns = [col.name for col in table.schema if col.name not in excluded]
    logger.info(f"Discovered dynamic BigQuery columns: {columns}")
    return columns


def search_knowledge_base_vectors(
    query_text: str, top_k: int = config.TOP_K_RESULTS
) -> List[Dict[str, Any]]:
    client = get_bq_client()
    logger.info(f"Executing Vector Search for: '{query_text}' with top_k={top_k}")

    sql = f"""
    SELECT 
        base.*,
        distance
    FROM VECTOR_SEARCH(
        TABLE `{config.FULL_TABLE_PATH}`,
        'embedding',
        (
            SELECT ml_generate_embedding_result AS embedding
            FROM ML.GENERATE_EMBEDDING(
                MODEL `{config.FULL_MODEL_PATH}`,
                (SELECT @query_text AS content)
            )
        ),
        top_k => @top_k,
        distance_type => 'COSINE'
    )
    ORDER BY distance ASC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("query_text", "STRING", query_text),
            bigquery.ScalarQueryParameter("top_k", "INT64", top_k),
        ]
    )

    query_job = client.query(sql, job_config=job_config)
    results = []
    for row in query_job.result():
        row_dict = dict(row)
        row_dict.pop("embedding", None)
        results.append(row_dict)

    logger.info(f"Retrieved {len(results)} matching entries.")
    return results


def insert_dynamic_record(data: Dict[str, Any], search_content: str) -> None:
    client = get_bq_client()
    columns = list(data.keys())

    col_names_sql = ", ".join(columns) + ", search_content, embedding"
    param_names_sql = (
        ", ".join([f"@{col}" for col in columns])
        + ", @search_content, ml_generate_embedding_result"
    )

    insert_sql = f"""
    INSERT INTO `{config.FULL_TABLE_PATH}` ({col_names_sql})
    SELECT 
        {param_names_sql}
    FROM ML.GENERATE_EMBEDDING(
        MODEL `{config.FULL_MODEL_PATH}`,
        (SELECT @search_content AS content)
    )
    """

    query_params = [
        bigquery.ScalarQueryParameter(col, "STRING", str(val))
        for col, val in data.items()
    ]
    query_params.append(
        bigquery.ScalarQueryParameter("search_content", "STRING", search_content)
    )

    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    logger.info(f"Executing dynamic INSERT for columns: {columns}")
    job = client.query(insert_sql, job_config=job_config)
    job.result()
    logger.info("Record inserted and embedded successfully into BigQuery.")