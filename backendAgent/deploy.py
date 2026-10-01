import vertexai
from vertexai.preview import reasoning_engines  # Agent Engine SDK

# 1. Initialize Vertex AI
PROJECT_ID = "saas-poc-env"
LOCATION = "us-central1"
STAGING_BUCKET = f"gs://{PROJECT_ID}-agent-engine-staging"
SERVICE_ACCOUNT = f"agent-engine-sa@{PROJECT_ID}.iam.gserviceaccount.com"

vertexai.init(
    project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET
)

# 2. Wrap ADK troubleshooting_agent for Agent Engine runtime
from troubleshooting_agent.agent import root_agent


class TroubleshootingAgentApp:

  def __init__(self):
    pass

  def set_up(self):
    # Any warm-up logic if needed
    pass

  def query(self, prompt: str) -> str:
    response = root_agent.run(prompt)
    return response.text


# 3. Deploy the application
if __name__ == "__main__":
  print("Deploying troubleshooting_agent to Vertex AI Agent Engine...")

  remote_app = reasoning_engines.ReasoningEngine.create(
      TroubleshootingAgentApp(),
      requirements=[
          "google-adk>=0.1.0",
          "google-cloud-bigquery>=3.25.0",
          "google-genai>=0.1.1",
          "python-dotenv>=1.0.0",
      ],
      extra_packages=["./troubleshooting_agent"],
      display_name="troubleshooting-agent-service",
      description="Troubleshooting agent using BigQuery Vector Search RAG",
  )

  print(f"Deployment complete! Resource Name: {remote_app.resource_name}")