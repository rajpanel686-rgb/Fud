import asyncio
import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from aiogram import Bot

BOT_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "api-server"
sys.path.insert(0, str(BOT_DIR))

from sms_bot import BOT_TOKEN, load, poll_inbox_once  # noqa: E402


def _write_json(handler: BaseHTTPRequestHandler, status: int, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


async def _poll_all_users() -> int:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
    bot = Bot(token=BOT_TOKEN)
    try:
        users = load().get("users", {})
        count = 0
        for uid, user in users.items():
            if user.get("monitoring"):
                await poll_inbox_once(bot, int(uid))
                count += 1
        return count
    finally:
        await bot.session.close()


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        expected = os.environ.get("CRON_SECRET", "")
        provided = self.headers.get("Authorization", "")
        if expected and not hmac.compare_digest(provided, f"Bearer {expected}"):
            _write_json(self, 401, {"ok": False, "error": "unauthorized"})
            return
        try:
            count = asyncio.run(_poll_all_users())
            _write_json(self, 200, {"ok": True, "users_checked": count})
        except Exception as exc:
            print(f"Cron error: {exc}", file=sys.stderr)
            _write_json(self, 500, {"ok": False, "error": "cron failed"})