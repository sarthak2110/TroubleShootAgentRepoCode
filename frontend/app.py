import uuid
import chainlit as cl
from auth import verify_idp_credentials
from agent_client import stream_agent_engine
from session_service import create_agent_session


def build_hero_ui(is_admin: bool, user_id: str) -> str:
    if is_admin:
        top_bar = (
            '<div class="mode-topbar">\n'
            '<div class="mode-indicator" style="color: #81c995;">\n'
            '<span>🛡️ <strong>ADMIN MODE</strong> (Active)</span>\n'
            '<span style="color: #80868b; font-size: 0.8rem;">(' + str(user_id) + ')</span>\n'
            '</div>\n'
            '<button type="button" class="mode-btn-public" style="background: none; border: none; color: #8ab4f8; cursor: pointer; font-size: 0.85rem; font-weight: 500; padding: 0;">🛡️ Switch to Public Mode</button>\n'
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
        '<div class="gemini-chip" data-prompt="Please add this new data to the knowledge base:\nKB-ALM-009\nNETWORK_PEERING_FAILED: Subnet collision\nOverlapping CIDRs\nNetwork Setup\nReallocate block\nRe-peer.">\n'
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
    cl.user_session.set("id_token", None)

    session_id = await create_agent_session(user_id)
    cl.user_session.set("session_id", session_id)

    hero_msg = await cl.Message(content=build_hero_ui(is_admin=False, user_id=user_id)).send()
    cl.user_session.set("hero_msg", hero_msg)


@cl.on_message
async def on_message(message: cl.Message):
    user_text = message.content.strip()
    
    # ---------------------------------------------------------
    # 1. INTERCEPT PUBLIC MODE SWITCHING
    # ---------------------------------------------------------
    if user_text == "__SWITCH_PUBLIC__":
        await message.remove()
        cl.user_session.set("is_admin", False)
        cl.user_session.set("id_token", None)
        
        guest_user_id = "guest_" + str(uuid.uuid4().hex[:8])
        cl.user_session.set("user_id", guest_user_id)
        
        new_session_id = await create_agent_session(guest_user_id)
        cl.user_session.set("session_id", new_session_id)

        hero_msg = cl.user_session.get("hero_msg")
        if hero_msg:
            hero_msg.content = build_hero_ui(is_admin=False, user_id=guest_user_id)
            await hero_msg.update()

        await cl.Message(content="### 🛡️ Switched to Standard Mode\nYou are now in public mode. Data ingestion is locked.").send()
        return

    # ---------------------------------------------------------
    # 2. INTERCEPT CUSTOM JS LOGIN POP-UP
    # ---------------------------------------------------------
    if user_text.startswith("__AUTH_ADMIN__:"):
        await message.remove()
        
        parts = user_text.split(":", 2) 
        if len(parts) >= 3:
            email, password = parts[1], parts[2]
            
            print(f"Attempting login for: {email}") 
            auth_result = await verify_idp_credentials(email, password)
            print(f"Auth Result: {auth_result}") 

            if auth_result: 
                cl.user_session.set("is_admin", True)
                cl.user_session.set("user_id", email)
                
                token = auth_result.get("id_token") if isinstance(auth_result, dict) else auth_result
                cl.user_session.set("id_token", token) 

                new_session_id = await create_agent_session(email)
                cl.user_session.set("session_id", new_session_id)

                hero_msg = cl.user_session.get("hero_msg")
                if hero_msg:
                    hero_msg.content = build_hero_ui(is_admin=True, user_id=email)
                    await hero_msg.update()

                success_msg = (
                    "### ⚡ ADMIN MODE ACTIVATED\n\n"
                    f"Authenticated as **{email}** via Identity Platform.\n\n"
                    "- ✅ **RAG Diagnostic Queries:** Active\n"
                    "- ✅ **BigQuery Data Ingestion:** Active\n\n"
                    "You can now submit new KB documents."
                )
                await cl.Message(content=success_msg).send()
            else:
                fail_msg = (
                    "❌ **Authentication Failed:** Invalid credentials or missing token.<br><br>"
                    '<button type="button" class="mode-btn-login">🔑 Retry Admin Login</button>'
                )
                await cl.Message(content=fail_msg).send()
        return

    # ---------------------------------------------------------
    # 3. NORMAL CHAT STREAMING WITH AUTH CONTEXT INJECTION
    # ---------------------------------------------------------
    user_id = cl.user_session.get("user_id")
    session_id = cl.user_session.get("session_id")
    is_admin = cl.user_session.get("is_admin", False)
    id_token = cl.user_session.get("id_token")

    agent_message = user_text
    if is_admin and id_token:
        agent_message = f"{user_text}\n\n[[SYSTEM_AUTH_CONTEXT: id_token={id_token}]]"

    msg = cl.Message(content="")
    message_started = False

    try:
        async for event in stream_agent_engine(
            user_id=user_id, 
            session_id=session_id, 
            message=agent_message,
            is_admin=is_admin,
            id_token=id_token
        ):
            event_type = event.get("type")

            if event_type == "token":
                if not message_started:
                    await msg.send()
                    message_started = True
                
                await msg.stream_token(event["content"])

            elif event_type == "error":
                if "UNAUTHORIZED" in str(event["content"]).upper():
                    err = "⛔ **ADMIN MODE Required to Ingest Data:** Please authenticate using the button above."
                else:
                    err = "❌ " + str(event["content"])
                    
                if not message_started:
                    msg.content = err
                    await msg.send()
                else:
                    msg.content += "\n\n" + err
                    await msg.update()

    except Exception as exc:
        err_msg = "❌ **Error streaming response:** " + str(exc)
        if not message_started:
            msg.content = err_msg
            await msg.send()
        else:
            msg.content += "\n\n" + err_msg
            await msg.update()

    finally:
        if message_started:
            await msg.update()
        else:
            await cl.Message(content="✅ *Task completed.*").send()