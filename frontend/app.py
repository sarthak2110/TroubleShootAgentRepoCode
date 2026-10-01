import uuid
import chainlit as cl
from auth import verify_idp_credentials
from agent_client import stream_agent_engine
from session_service import create_agent_session


def is_admin_ingest_intent(text: str) -> bool:
    t = text.lower()
    keywords = ["add to knowledge base", "ingest", "add this kb", "insert to bq"]
    return any(k in t for k in keywords) or "kb-alm-" in t or ("error / symptom" in t and "probable cause" in t)


def build_hero_ui(is_admin: bool, user_id: str) -> str:
    if is_admin:
        top_bar = (
            '<div class="mode-topbar">\n'
            '<div class="mode-indicator" style="color: #81c995;">\n'
            '<span>⚡ <strong>ADMIN MODE</strong> (Active)</span>\n'
            '<span style="color: #80868b; font-size: 0.8rem;">(' + str(user_id) + ')</span>\n'
            '</div>\n'
            '<span style="color: #81c995; font-size: 0.85rem; font-weight: 500;">✓ Ingestion Unlocked</span>\n'
            '</div>'
        )
        subhead = "Admin mode active. Query solutions or paste unstructured KB notes to ingest directly into BigQuery."
    else:
        top_bar = (
            '<div class="mode-topbar">\n'
            '<div class="mode-indicator" style="color: #8ab4f8;">\n'
            '<span>🛡️ <strong>Standard Mode</strong> (Public)</span>\n'
            '</div>\n'
            '<button type="button" class="mode-btn-login">⚡ Switch to ADMIN MODE</button>\n'
            '</div>'
        )
        subhead = "Diagnose cloud pipeline, quota, and IAM errors using BigQuery Vector Search."

    chips = (
        '<div class="gemini-chip-grid">\n'
        '<div class="gemini-chip" data-prompt="Our deployment failed with 403 PERMISSION_DENIED: Caller lacks required IAM permissions during provisioning. How do I fix it?">\n'
        '<span class="gemini-chip-title">Fix 403 IAM Permission Failure</span>\n'
        '<span class="gemini-chip-icon">🔐</span>\n'
        '</div>\n'
        '<div class="gemini-chip" data-prompt="We hit RESOURCE_EXHAUSTED QuotaExceededError during scale-out. What are the resolution steps?">\n'
        '<span class="gemini-chip-title">Diagnose Quota & Resource Limits</span>\n'
        '<span class="gemini-chip-icon">📈</span>\n'
        '</div>\n'
        '<div class="gemini-chip" data-prompt="Circuit breaker triggered and initiated rollback during rolling upgrade.">\n'
        '<span class="gemini-chip-title">Rollback & Canary Failure Analysis</span>\n'
        '<span class="gemini-chip-icon">🔄</span>\n'
        '</div>\n'
        '<div class="gemini-chip" data-prompt="Please add this new data to the knowledge base:\nKB-ALM-009\nNETWORK_PEERING_FAILED: Subnet collision\nOverlapping CIDRs\nNetwork Setup\n1. Reallocate block\n2. Re-peer.">\n'
        '<span class="gemini-chip-title">Ingest New KB Document</span>\n'
        '<span class="gemini-chip-icon">✍️</span>\n'
        '</div>\n'
        '</div>'
    )

    hero = (
        top_bar + '\n'
        '<div class="gemini-hero">\n'
        '<h1>Hello, <span class="gemini-gradient-text">Cloud Engineer</span></h1>\n'
        '<p>' + subhead + '</p>\n'
        + chips + '\n'
        '</div>'
    )
    return hero


@cl.on_chat_start
async def on_start():
    user_id = "guest_" + str(uuid.uuid4().hex[:8])
    cl.user_session.set("user_id", user_id)
    cl.user_session.set("is_admin", False)

    session_id = await create_agent_session(user_id)
    cl.user_session.set("session_id", session_id)

    await cl.Message(content=build_hero_ui(is_admin=False, user_id=user_id)).send()


@cl.on_message
async def on_message(message: cl.Message):
    user_text = message.content.strip()
    user_id = cl.user_session.get("user_id")
    session_id = cl.user_session.get("session_id")
    is_admin = cl.user_session.get("is_admin", False)

    if user_text.startswith("__AUTH_ADMIN__:"):
        parts = user_text.split(":")
        if len(parts) >= 3:
            email, password = parts[1], parts[2]
            auth_result = await verify_idp_credentials(email, password)

            if auth_result and auth_result.get("is_admin"):
                cl.user_session.set("is_admin", True)
                cl.user_session.set("user_id", email)

                success_msg = (
                    "### ⚡ ADMIN MODE ACTIVATED\n\n"
                    "Authenticated as **" + str(email) + "** via Identity Platform.\n\n"
                    "- ✅ **RAG Diagnostic Queries:** Active\n"
                    "- ✅ **BigQuery Data Ingestion:** Active\n\n"
                    "You can now submit new KB documents to persist into BigQuery."
                )
                await cl.Message(content=success_msg).send()
            else:
                fail_msg = (
                    "❌ **Authentication Failed:** Invalid credentials or account not found in Identity Platform.<br><br>"
                    '<button type="button" class="mode-btn-login">🔑 Retry Admin Login</button>'
                )
                await cl.Message(content=fail_msg).send()
        return

    if is_admin_ingest_intent(user_text) and not is_admin:
        guard_msg = (
            "⛔ **ADMIN MODE Required to Ingest Data:**<br><br>"
            "Standard users can query solutions freely, but adding documents to the BigQuery knowledge base requires Administrator privileges.<br><br>"
            '<button type="button" class="mode-btn-login">⚡ Authenticate as Admin</button>'
        )
        await cl.Message(content=guard_msg).send()
        return

    msg = cl.Message(content="")
    message_started = False

    thought_step = cl.Step(name="✨ Thinking & Diagnostics", type="run")
    await thought_step.send()

    try:
        async for event in stream_agent_engine(user_id, session_id, user_text):
            event_type = event.get("type")

            if event_type == "thought":
                await thought_step.stream_token(event["content"])

            elif event_type == "token":
                if not message_started:
                    await msg.send()
                    message_started = True
                await msg.stream_token(event["content"])

            elif event_type == "error":
                if not message_started:
                    msg.content = "❌ " + str(event["content"])
                    await msg.send()
                else:
                    msg.content += "\n\n❌ " + str(event["content"])

    except Exception as exc:
        err_msg = "❌ **Error streaming response:** " + str(exc)
        if not message_started:
            msg.content = err_msg
            await msg.send()
        else:
            msg.content += "\n\n" + err_msg

    finally:
        await thought_step.update()
        if message_started:
            await msg.update()
        else:
            await cl.Message(content="✅ *Task completed.*").send()
