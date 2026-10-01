import json
import re
from typing import AsyncGenerator
import google.auth
import google.auth.transport.requests
import httpx
import config

logger = config.get_logger("agent_client")

TOOL_DESCRIPTIONS = {
    "query_knowledge_base": "Searching BigQuery Vector Index for matching troubleshooting solutions...",
    "ingest_kb_record": "Admin Ingestion: Extracting structured fields and computing embeddings...",
}


def get_gcp_bearer_token() -> str:
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token


async def stream_agent_engine(
    user_id: str, session_id: str | None, message: str
) -> AsyncGenerator[dict, None]:
    payload = {
        "class_method": "async_stream_query",
        "input": {"user_id": user_id, "session_id": session_id, "message": message},
    }
    headers = {
        "Authorization": "Bearer " + str(get_gcp_bearer_token()),
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST", config.AGENT_ENGINE_STREAM_URL, json=payload, headers=headers
        ) as response:
            if response.status_code != 200:
                error_body = await response.aread()
                yield {
                    "type": "error",
                    "content": "API Error " + str(response.status_code) + ": " + error_body.decode("utf-8", errors="ignore"),
                }
                return

            async for line in response.aiter_lines():
                line = line.strip()
                if not line or line == "data: [DONE]":
                    continue

                data_str = line[5:].strip() if line.startswith("data:") else line
                try:
                    chunk = json.loads(data_str)
                    content = chunk.get("content", {})

                    if isinstance(content, str) and content.strip():
                        clean_text = re.sub(r"^Agent:.*?\n+", "", content)
                        yield {"type": "token", "content": clean_text}

                    parts = content.get("parts", []) if isinstance(content, dict) else []
                    for part in parts:
                        if "text" in part and part["text"].strip():
                            clean_text = re.sub(r"^Agent:.*?\n+", "", part["text"])
                            yield {"type": "token", "content": clean_text}

                        if "function_call" in part:
                            fn_name = part["function_call"].get("name", "")
                            desc = TOOL_DESCRIPTIONS.get(fn_name, "Running tool: `" + str(fn_name) + "`...")
                            yield {"type": "thought", "content": "⚙️ **" + desc + "**\n\n"}

                        if "thought" in part:
                            yield {"type": "thought", "content": str(part["thought"]) + "\n\n"}

                except json.JSONDecodeError:
                    continue
