# Vercel hosting

This version receives Telegram updates through a webhook. It does not use long polling.

## Required Vercel environment variables

Set these in the Vercel project for **Production**:

- `TELEGRAM_BOT_TOKEN` — a fresh token from BotFather
- `TELEGRAM_WEBHOOK_SECRET` — a random secret used by Telegram webhook requests
- `REDIS_URL` or `KV_URL` — a Redis-compatible connection URL for aiogram FSM state
- `KV_REST_API_URL` — Vercel KV REST endpoint
- `KV_REST_API_TOKEN` — Vercel KV REST token
- `CRON_SECRET` — a random secret for the scheduled inbox poll

Vercel KV supplies the `KV_URL`, `KV_REST_API_URL`, and `KV_REST_API_TOKEN` values when the KV integration is attached.

## Deploy

1. Import this repository into Vercel.
2. Set the environment variables above.
3. Deploy the project.
4. Set Telegram's webhook, replacing the domain and placeholder values:

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
  -d "url=https://<your-project>.vercel.app/api/telegram" \
  -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>" \
  -d 'allowed_updates=["message","edited_message","channel_post","callback_query","chat_join_request"]'
```

The cron function checks Firebase inboxes once per minute for users whose monitor is enabled. Vercel cannot keep the original four-second background polling loop alive.