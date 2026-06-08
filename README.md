# TESLA1 VPN Bot

Monorepo для VPN-сервиса на базе [Bedolaga Bot](https://github.com/BEDOLAGA-DEV/remnawave-bedolaga-telegram-bot) и [Bedolaga Cabinet](https://github.com/BEDOLAGA-DEV/bedolaga-cabinet).

## Структура

| Папка | Описание |
|-------|----------|
| `bot/` | Telegram-бот, API, платежи, интеграция с Remnawave |
| `web/` | Веб-кабинет (React + Vite) |

## Быстрый старт

```bash
# Backend
cd bot
cp .env.example .env   # заполнить переменные
docker compose up -d --build

# Frontend (опционально)
cd ../web
cp .env.example .env
docker compose up -d --build
```

Документация: [docs.bedolagam.ru](https://docs.bedolagam.ru)
