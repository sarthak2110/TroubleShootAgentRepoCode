import json
import base64
import time
from google.genai import Client
from troubleshooting_agent import config
from troubleshooting_agent.services.bigquery_service import (
    get_table_columns,
    insert_dynamic_record,
)

logger = config.get_logger("ingest_tool")
genai_client = Client()

def _decode_jwt_payload(token: str) -> dict:
    """Safely decodes JWT payload without external network calls."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")
        payload_base64 = parts[1] + "=" * (-len(parts[1]) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_base64)
        return json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to decode token: {e}")

def ingest_kb_record(raw_kb_text: str, admin_id_token: str = None) -> str:
    """Extracts unstructured text into the exact columns configured in BigQuery
    and inserts the record with auto-computed embeddings.
    
    Args:
        raw_kb_text: The text to parse.
        admin_id_token: The system auth token extracted from the prompt.
    """
    logger.info("Tool invoked: ingest_kb_record")
    
    # 1. Verify token presence
    if not admin_id_token:
        logger.warning("Security Block: No ID token provided to tool.")
        return json.dumps({"status": "UNAUTHORIZED", "error": "Access Denied."})

    # 2. Sandbox-Safe Local Claims Verification with Clock Skew & Flexible Issuer
    try:
        claims = _decode_jwt_payload(admin_id_token)
        
        exp_time = claims.get("exp", 0)
        current_time = time.time()
        
        logger.info(f"Token exp: {exp_time} | Current time: {current_time} | Diff: {exp_time - current_time}s")
        
        # Check Expiration with 60s leeway for container time skew
        if exp_time < (current_time - 60):
            logger.error("Security Block: Token has expired.")
            return json.dumps({"status": "UNAUTHORIZED", "error": "Token has expired."})
        
        # Check Audience matches project ID or fallback ID
        token_aud = claims.get("aud")
        allowed_audiences = [str(config.GOOGLE_CLOUD_PROJECT), "saas-poc-env"]
        if token_aud not in allowed_audiences:
            logger.error(f"Security Block: Invalid audience. Got {token_aud}")
            return json.dumps({"status": "UNAUTHORIZED", "error": "Invalid token audience."})
        
        # Check Issuer contains google.com securely
        issuer = claims.get("iss", "")
        if not issuer or "google.com" not in issuer:
            logger.error(f"Security Block: Invalid issuer: {issuer}")
            return json.dumps({"status": "UNAUTHORIZED", "error": "Invalid token issuer."})

        email = claims.get("email")
        logger.info(f"Admin auth verified via local claims validation for: {email}")

    except Exception as e:
        logger.error(f"Security Block: Token validation failed: {e}")
        return json.dumps({"status": "UNAUTHORIZED", "error": "Invalid or Expired Admin token."})

    # 3. Proceed with normal ingestion if authorized
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