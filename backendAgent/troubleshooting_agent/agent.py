from google.adk.agents import Agent
from troubleshooting_agent import config
from troubleshooting_agent.tools.ingest_tool import ingest_kb_record
from troubleshooting_agent.tools.query_tool import query_knowledge_base

logger = config.get_logger("agent")

AGENT_INSTRUCTION = """
You are an enterprise cloud troubleshooting assistant named troubleshooting_agent.

You have access to two tools:
1. `query_knowledge_base`: Use this when a user asks about an error, bug, failure, or general troubleshooting query.
   - Present the retrieved records clearly with details such as Error/Symptom, Probable Cause, Impacted Phase, and Step-by-Step Resolution.
   - If nothing is found, state that no existing solution was found in BigQuery.

2. `ingest_kb_record`: Use this when an administrator supplies raw text to add to the knowledge base.
   - Confirm to the admin once the record has been parsed and saved into BigQuery.
"""

# ADK web UI and CLI server require `root_agent`
root_agent = Agent(
    name="troubleshooting_agent",
    model=config.GEMINI_MODEL,
    instruction=AGENT_INSTRUCTION,
    tools=[query_knowledge_base, ingest_kb_record],
)