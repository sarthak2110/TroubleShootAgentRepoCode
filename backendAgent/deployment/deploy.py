import os

# 1. Force google.genai to use Vertex AI locally DURING IMPORT
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
os.environ["GOOGLE_CLOUD_PROJECT"] = "saas-poc-env"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

import vertexai
from vertexai import agent_engines

# 2. NOW import the agent code (it will successfully use Vertex now)
from troubleshooting_agent.agent import root_agent

# 3. Project Configuration
PROJECT_ID = "saas-poc-env"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://sarthak-test"

# 4. Initialize Vertex AI
vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET,
)

print(f"Current Directory: {os.getcwd()}")
print("Deploying troubleshooting_agent to Vertex AI Agent Engine...")

# 5. Environment variables for remote container
ENV_VARS = {
    "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
    "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "TRUE",
    "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "TRUE",
    "PROJECT_ID": PROJECT_ID,
    "LOCATION": LOCATION,
    "BQ_DATASET_ID": "support_rag",
    "BQ_TABLE_ID": "knowledge_base",
    "BQ_CONNECTION_ID": "vertex_conn",
    "BQ_EMBEDDING_MODEL_ID": "embedding_model",
    "GEMINI_MODEL": "gemini-2.5-flash",
    "EMBEDDING_ENDPOINT": "text-embedding-005",
    "TOP_K_RESULTS": "3",
    "LOG_LEVEL": "INFO",
}

# 6. Deploy using AgentEngine
try:
    remote_agent = agent_engines.AgentEngine.create(
        agent_engine=root_agent,
        requirements="./requirements.txt",
        extra_packages=["./troubleshooting_agent"],
        display_name="troubleshooting-agent-service",
        description="Troubleshooting agent using BigQuery Vector Search RAG",
        env_vars=ENV_VARS,
    )
    print("✅ Deployment successful!")
    print(f"Agent Resource Name: {remote_agent.resource_name}")

except Exception as e:
    print(f"❌ Deployment failed: {e}")