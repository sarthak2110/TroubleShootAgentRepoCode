import json
from troubleshooting_agent import config
from troubleshooting_agent.services.bigquery_service import search_knowledge_base_vectors

logger = config.get_logger("query_tool")


def query_knowledge_base(query: str) -> str:
    """Searches the BigQuery Knowledge Base vector store for solutions, root causes,
    and troubleshooting steps matching the user's issue.
    """
    logger.info(f"Tool invoked: query_knowledge_base with query='{query}'")
    try:
        results = search_knowledge_base_vectors(query)
        if not results:
            return "No matching troubleshooting records were found in the knowledge base."

        return json.dumps(results, indent=2, default=str)
    except Exception as exc:
        logger.error(f"Error querying knowledge base: {exc}", exc_info=True)
        return f"Error occurred while querying knowledge base: {str(exc)}"