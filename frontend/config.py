import logging
import os
import sys
from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "saas-poc-env")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
ENGINE_ID = os.getenv("ENGINE_ID", "")

VERTEX_AI_AGENT_ENGINE_URL = os.getenv("VERTEX_AI_AGENT_ENGINE_URL", "")

if VERTEX_AI_AGENT_ENGINE_URL:
    AGENT_ENGINE_QUERY_URL = str(VERTEX_AI_AGENT_ENGINE_URL) + ":query"
    AGENT_ENGINE_STREAM_URL = str(VERTEX_AI_AGENT_ENGINE_URL) + ":streamQuery?alt=sse"
else:
    BASE_URL = (
        "https://"
        + str(GCP_LOCATION)
        + "-aiplatform.googleapis.com/v1/projects/"
        + str(GCP_PROJECT_ID)
        + "/locations/"
        + str(GCP_LOCATION)
        + "/reasoningEngines/"
        + str(ENGINE_ID)
    )
    AGENT_ENGINE_QUERY_URL = os.getenv("AGENT_ENGINE_QUERY_URL", BASE_URL + ":query")
    AGENT_ENGINE_STREAM_URL = os.getenv("AGENT_ENGINE_STREAM_URL", BASE_URL + ":streamQuery?alt=sse")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(LOG_LEVEL.upper())
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
    return logger
