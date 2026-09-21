import asyncio
import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from aiogram import Bot
from aiogram.types import Update
from aiogram.fsm.storage.redis import RedisStorage

BOT_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "api-server"
sys.path.insert(0, str(BOT_DIR))

from sms_bot import BOT_TOKEN, create_dispatcher  # noqa: E402


def _write_json(handler: BaseHTTPRequestHandler, status: int, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


async def _process_update(payload: dict):
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")

    redis_url = os.environ.get("REDIS_URL") or os.environ.get("KV_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL or KV_URL is required for Vercel FSM storage.")

    storage = RedisStorage.from_url(redis_url)
    bot = Bot(token=BOT_TOKEN)
    try:
        dispatcher = create_dispatcher(storage)
        await dispatcher.feed_update(bot, Update.model_validate(payload))
    finally:
        await bot.session.close()
        await storage.close()


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        _write_json(self, 200, {"ok": True, "service": "telegram-webhook"})

    def do_POST(self):
        expected = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
        provided = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if expected and not hmac.compare_digest(provided, expected):
            _write_json(self, 403, {"ok": False, "error": "invalid webhook secret"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            asyncio.run(_process_update(payload))
            _write_json(self, 200, {"ok": True})
        except Exception as exc:
            print(f"Telegram webhook error: {exc}", file=sys.stderr)
            _write_json(self, 500, {"ok": False, "error": "webhook processing failed"})