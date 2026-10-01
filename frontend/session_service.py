import uuid
import httpx
import config
from agent_client import get_gcp_bearer_token

logger = config.get_logger("session_service")

async def create_agent_session(user_id: str) -> str | None:
    """Provisions a conversation session on Vertex AI Agent Engine."""
    if not config.ENGINE_ID or config.ENGINE_ID == "YOUR_REASONING_ENGINE_ID":
        fallback_id = "local_session_" + str(uuid.uuid4().hex[:8])
        logger.warning("ENGINE_ID is not configured. Using fallback local session: " + fallback_id)
        return fallback_id

    payload = {
        "class_method": "async_create_session",
        "input": {"user_id": user_id},
    }
    headers = {
        "Authorization": "Bearer " + str(get_gcp_bearer_token()),
        "Content-Type": "application/json",
    }

    try:
        logger.info("Creating session on Agent Engine for user: " + str(user_id))
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                config.AGENT_ENGINE_QUERY_URL, json=payload, headers=headers
            )
            data = resp.json()

            if resp.status_code == 200:
                session_id = data.get("output", {}).get("id")
                logger.info("Session created successfully: " + str(session_id))
                return session_id
            else:
                logger.error("Failed to create session on Agent Engine. HTTP " + str(resp.status_code) + ": " + resp.text)
                return "fallback_session_" + str(uuid.uuid4().hex[:8])

    except Exception as exc:
        logger.error("Session initialization error: " + str(exc), exc_info=True)
        return "fallback_session_" + str(uuid.uuid4().hex[:8])
