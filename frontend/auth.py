import httpx
import google.auth
import google.auth.transport.requests
import config

logger = config.get_logger("auth")

def get_service_account_token() -> str:
    """Retrieves an access token using GCP Service Account / ADC."""
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token


async def verify_idp_credentials(email: str, password: str) -> dict | None:
    """Authenticates the administrator directly using Identity Platform via Service Account token."""
    try:
        token = get_service_account_token()
        sign_in_url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"

        headers = {
            "Authorization": "Bearer " + str(token),
            "Content-Type": "application/json",
            "x-goog-user-project": config.GCP_PROJECT_ID,
        }

        payload = {
            "email": email.strip(),
            "password": password,
            "returnSecureToken": True,
            "targetProjectId": config.GCP_PROJECT_ID,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(sign_in_url, json=payload, headers=headers)
            data = resp.json()

            if resp.status_code == 200:
                user_email = data.get("email", email).lower()
                logger.info("Admin verified by Identity Platform: " + str(user_email))
                return {
                    "email": user_email,
                    "is_admin": True,
                    "local_id": data.get("localId"),
                    "id_token": data.get("idToken"),
                }
            else:
                error_msg = data.get("error", {}).get("message", "INVALID_CREDENTIALS")
                logger.warning("Identity Platform rejected login for " + str(email) + ": " + str(error_msg))
                return None

    except Exception as exc:
        logger.error("Error during Identity Platform authentication: " + str(exc), exc_info=True)
        return None
