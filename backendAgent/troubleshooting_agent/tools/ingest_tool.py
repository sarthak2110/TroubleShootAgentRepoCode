import json
from google.genai import Client
from troubleshooting_agent import config
from troubleshooting_agent.services.bigquery_service import (
    get_table_columns,
    insert_dynamic_record,
)

logger = config.get_logger("ingest_tool")
genai_client = Client()


def ingest_kb_record(raw_kb_text: str) -> str:
    """Extracts unstructured text into the exact columns configured in BigQuery
    and inserts the record with auto-computed embeddings.
    """
    logger.info("Tool invoked: ingest_kb_record")
    try:
        current_columns = get_table_columns()

        prompt = f"""
        Extract the information from the raw troubleshooting text below into a valid JSON object.
        
        The JSON object must ONLY contain keys from this list of columns:
        {current_columns}

        Raw Text:
        \"\"\"{raw_kb_text}\"\"\"
        """

        response = genai_client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )

        extracted_data = json.loads(response.text)
        logger.info(f"Parsed keys from raw text: {list(extracted_data.keys())}")

        search_content = "\n".join(
            [f"{k}: {v}" for k, v in extracted_data.items() if v]
        )

        insert_dynamic_record(extracted_data, search_content)

        return json.dumps(
            {
                "status": "SUCCESS",
                "message": "Record parsed and saved successfully to BigQuery.",
                "ingested_fields": extracted_data,
            },
            indent=2,
        )

    except Exception as exc:
        logger.error(f"Ingestion failed: {exc}", exc_info=True)
        return json.dumps({"status": "FAILED", "error": str(exc)})