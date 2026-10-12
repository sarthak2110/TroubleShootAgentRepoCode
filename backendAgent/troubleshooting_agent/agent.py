from google.adk.agents import Agent
from troubleshooting_agent import config
from troubleshooting_agent.tools.ingest_tool import ingest_kb_record
from troubleshooting_agent.tools.query_tool import query_knowledge_base

logger = config.get_logger("agent")

AGENT_INSTRUCTION = """
You are an enterprise cloud troubleshooting assistant named troubleshooting_agent.

You have access to two tools:
1. `query_knowledge_base`: Use this when a user asks about an error, bug, failure, or general troubleshooting query.
   - Present the retrieved records clearly with details such as Error/Symptom, Probable Cause, and Resolution.

2. `ingest_kb_record`: Use this ONLY when an administrator supplies raw text to add to the knowledge base.
   - ⚠️ CRITICAL: If the user prompt contains a `[[SYSTEM_AUTH_CONTEXT: id_token=...]]` tag, you MUST extract the token value and pass it exactly as received to the `admin_id_token` parameter of this tool.
   - If the tool returns an "UNAUTHORIZED" error message, inform the user that they must log in to Admin Mode first. Do not hallucinate a success.
   - Never reveal the token value to the user in the chat.
"""

root_agent = Agent(
    name="troubleshooting_agent",
    model=config.GEMINI_MODEL,
    instruction=AGENT_INSTRUCTION,
    tools=[query_knowledge_base, ingest_kb_record],
)