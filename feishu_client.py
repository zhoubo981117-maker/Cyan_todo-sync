from __future__ import annotations

import json
import logging
import os
from typing import Any

import server


LOG = logging.getLogger("todo-sync.feishu")
RECEIVED_REPLY_TEXT = os.environ.get("TODO_FEISHU_RECEIVED_REPLY", "✅ 收到").strip() or "✅ 收到"


def _event_to_dict(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        return data
    try:
        import lark_oapi as lark  # type: ignore

        marshalled = lark.JSON.marshal(data)
        if isinstance(marshalled, str):
            parsed = json.loads(marshalled)
            return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass
    if hasattr(data, "to_dict"):
        try:
            parsed = data.to_dict()
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            pass
    try:
        parsed = json.loads(json.dumps(data, default=lambda obj: getattr(obj, "__dict__", str(obj))))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def handle_feishu_event_payload(payload: dict[str, Any]) -> dict[str, Any]:
    text = server._extract_feishu_message_text(payload)
    if not text.strip():
        return {"handled": False, "reason": "empty message"}

    if server.AI_API_KEY:
        todos = server.create_feishu_ai_todos(server.DB, server.FEISHU_DEFAULT_EMAIL, text)
        return {"handled": bool(todos), "todos": todos}

    title = server.parse_feishu_todo_command(text)
    if not title:
        return {"handled": False, "reason": "unsupported command"}
    todo = server.create_feishu_todo(server.DB, server.FEISHU_DEFAULT_EMAIL, title)
    return {"handled": True, "todo": todo}


def extract_message_id(payload: dict[str, Any]) -> str:
    event = payload.get("event")
    if not isinstance(event, dict):
        return ""
    message = event.get("message")
    if not isinstance(message, dict):
        return ""
    return str(message.get("message_id") or "").strip()


def reply_to_feishu_message(api_client: Any, message_id: str, text: str = RECEIVED_REPLY_TEXT) -> bool:
    if not message_id:
        return False
    try:
        from lark_oapi.api.im.v1 import ReplyMessageRequest, ReplyMessageRequestBody  # type: ignore

        request = (
            ReplyMessageRequest.builder()
            .message_id(message_id)
            .request_body(
                ReplyMessageRequestBody.builder()
                .msg_type("text")
                .content(json.dumps({"text": text}, ensure_ascii=False))
                .build()
            )
            .build()
        )
        response = api_client.im.v1.message.reply(request)
        success = response.success() if hasattr(response, "success") else True
        if not success:
            LOG.warning("failed to reply Feishu message: code=%s msg=%s", getattr(response, "code", ""), getattr(response, "msg", ""))
        return bool(success)
    except Exception:
        LOG.exception("failed to reply Feishu message")
        return False


def _load_lark_sdk():
    try:
        import lark_oapi as lark  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: lark-oapi. Install it with: python3 -m pip install -r requirements.txt"
        ) from exc
    return lark


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("TODO_FEISHU_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    app_id = os.environ.get("TODO_FEISHU_APP_ID", "").strip()
    app_secret = os.environ.get("TODO_FEISHU_APP_SECRET", "").strip()
    default_email = server.FEISHU_DEFAULT_EMAIL
    if not app_id or not app_secret:
        LOG.error("TODO_FEISHU_APP_ID and TODO_FEISHU_APP_SECRET are required")
        return 2
    if not default_email:
        LOG.error("TODO_FEISHU_DEFAULT_EMAIL is required")
        return 2

    lark = _load_lark_sdk()
    api_client = lark.Client.builder().app_id(app_id).app_secret(app_secret).build()

    def on_message(data: Any) -> None:
        payload = _event_to_dict(data)
        reply_to_feishu_message(api_client, extract_message_id(payload))
        try:
            result = handle_feishu_event_payload(payload)
            LOG.info("processed Feishu message: %s", json.dumps(result, ensure_ascii=False, default=str))
        except Exception:
            LOG.exception("failed to process Feishu message")

    event_handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(on_message)
        .build()
    )
    log_level = getattr(lark.LogLevel, os.environ.get("TODO_FEISHU_SDK_LOG_LEVEL", "INFO").upper(), lark.LogLevel.INFO)
    if hasattr(lark, "ws") and hasattr(lark.ws, "Client"):
        client = lark.ws.Client(app_id, app_secret, event_handler=event_handler, log_level=log_level)
    else:
        from lark_oapi.ws.client import LarkWSClient  # type: ignore

        client = LarkWSClient(
            api_client,
            event_handler=event_handler,
            log_level=log_level,
        )
    LOG.info("starting Feishu long connection client for %s", default_email)
    client.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
