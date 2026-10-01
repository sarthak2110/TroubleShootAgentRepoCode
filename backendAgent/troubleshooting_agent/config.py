import logging
import os
import sys

# GCP & BigQuery Settings
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "saas-poc-env")
GOOGLE_CLOUD_REGION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")

BQ_DATASET_ID = os.getenv("BQ_DATASET_ID", "support_rag")
BQ_TABLE_ID = os.getenv("BQ_TABLE_ID", "knowledge_base")
BQ_EMBEDDING_MODEL_ID = os.getenv("BQ_EMBEDDING_MODEL_ID", "embedding_model")

FULL_TABLE_PATH = f"{GOOGLE_CLOUD_PROJECT}.{BQ_DATASET_ID}.{BQ_TABLE_ID}"
FULL_MODEL_PATH = f"{GOOGLE_CLOUD_PROJECT}.{BQ_DATASET_ID}.{BQ_EMBEDDING_MODEL_ID}"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "3"))

# Logging Configuration
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