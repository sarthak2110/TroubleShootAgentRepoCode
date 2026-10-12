1. Secure Login (Frontend UI)
Instead of typing passwords into the chat box (which leaves them in chat histories), the user clicks the "Switch to ADMIN MODE" button.
Chainlit securely prompts the user for their email and password using UI popups.
The frontend sends these credentials to GCP Identity Platform, which verifies them and returns a signed JSON Web Token (JWT / id_token).
This id_token is saved locally in the user's Chainlit session.


2. Context Injection (The Bridge)
When the Admin types a message (e.g., "Add this error to the KB"), agent_client.py intercepts it before sending it to the Agent Engine.
It checks if the user has an id_token. If they do, it secretly prepends a hidden string to the user's message:
[[SYSTEM_AUTH_CONTEXT: id_token=eyJhbG...]]\n\nUser Input: Add this error...
The user never sees this happen.


3. LLM Parsing (Agent Engine)
The LLM receives the modified prompt.
The system instructions (AGENT_INSTRUCTION in agent.py) specifically train the LLM to look for the [[SYSTEM_AUTH_CONTEXT]] tag.
When the LLM decides to use the ingest_kb_record tool, it extracts the token from the hidden text and passes it into the tool as the admin_id_token argument.


4. Cryptographic Verification (The Tool)
This is the ultimate security layer. The Python function ingest_kb_record receives the token from the LLM.
Before running any BigQuery code, the tool uses Google's official id_token.verify_firebase_token() library.
It mathematically verifies the token's signature against Google's public keys to ensure the token is real, not expired, and belongs to your GCP project.


5. Execution or Rejection
If the token is valid: The tool processes the text, saves it to BigQuery, and tells the LLM it succeeded.
If the token is missing or fake: The tool blocks the database action and returns {"status": "UNAUTHORIZED"} to the LLM. The LLM then apologizes to the user and asks them to log in.
